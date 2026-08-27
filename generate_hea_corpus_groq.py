"""
Synthetic text corpus generator for refractory high entropy alloys (HEAs).

Purpose
-------
This is the FIRST stage of the AlloyBERT pipeline: it produces a large,
diverse, unlabeled text corpus (no property values needed) that will be
used for CONTINUED PRETRAINING (MLM) of ModernBERT. It is NOT the labeled
fine-tuning dataset -- that stage comes later once you have paper-derived
composition -> property pairs.

Target mechanical properties (see TARGET_PROPERTIES below): ultimate
tensile strength, yield strength, hardness, elastic (Young's) modulus,
fracture toughness, elongation at fracture, compressive yield strength,
and fatigue strength/life. Corpus content is weighted toward passages that
build vocabulary/reasoning relevant to all of these, not just a subset.

Design notes
------------
- Uses Groq's free-tier API (openai/gpt-oss-120b) to write short technical
  passages about randomly sampled refractory HEA compositions. This is the
  same model/provider used in the RoboShot project, so no new account is
  needed beyond a Groq API key (console.groq.com).
- Diversity is enforced structurally, not left to chance: each prompt
  varies (a) the element set (3-7 principal elements), (b) processing
  route, (c) which subtopic to focus on, (d) style, and (e) ~25% of
  prompts compare two alloys rather than describing one in isolation.
  This matters because if every generated passage has the same shape, the
  MLM stage just memorizes a template instead of learning domain
  vocabulary/structure.
- No numeric property labels are requested or fabricated. Continued
  pretraining is unsupervised -- injecting LLM-hallucinated numbers here
  would bias downstream fine-tuning even though this stage has no loss
  on those numbers directly (the model would still learn spurious
  co-occurrence patterns between alloys and specific values).
- Output is JSONL, one passage per line, ready to feed into a
  HuggingFace `datasets` MLM pretraining script.

Usage
-----
    pip install groq --break-system-packages
    export GROQ_API_KEY=...
    python generate_hea_corpus_groq.py --num-samples 2000 --out hea_corpus.jsonl

Cost/throughput
----------------
Groq's free tier for openai/gpt-oss-120b has TWO separate caps that both
matter here: a per-minute cap (8000 TPM) and a per-DAY cap (200,000 TPD).
The per-minute cap is what --tpm/--est-tokens pace against, but the daily
cap is the one that actually bottlenecks a 2000-sample run: at ~700
tokens/request, 200,000 tokens/day works out to roughly 285 requests/day.
That means 2000 samples realistically takes about a WEEK of wall-clock
time on this tier, spread across multiple daily quota windows -- there is
no pacing trick that gets around a hard daily cap, only real elapsed time.
The script detects daily-limit (TPD) errors specifically, parses Groq's
own suggested cooldown (which can be several minutes), and pauses ALL
worker threads together rather than each one retrying independently into
the same exhausted daily budget. Run it under nohup and just let it run
across days:
    nohup python generate_hea_corpus_groq.py --num-samples 2000 --out hea_corpus.jsonl --resume > run.log 2>&1 &
--resume is safe to pass from the start -- it's a no-op on an empty/missing
file and means you can kill and restart the process anytime (e.g. to pull
in script updates) without losing progress or re-paying for tokens already
spent on earlier passages.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import re
import sys
import threading
import time

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env in the current directory so GROQ_API_KEY doesn't need a manual export
except ImportError:
    pass  # fine if python-dotenv isn't installed -- just export the var manually instead

try:
    from groq import Groq
except ImportError:
    sys.exit("Run: pip install groq --break-system-packages")


class TokenBucketLimiter:
    """
    Paces calls by TOKENS consumed within a rolling 60-second window, not by
    a fixed request count -- this matches Groq's actual quota mechanism
    (8000 tokens/minute), which is more precise than a requests/minute
    approximation since request size (prompt + completion) varies per call.

    Since this runs unattended under nohup, the priority is avoiding 429s
    entirely rather than minimizing wall-clock time: every call reserves its
    estimated token cost against the window BEFORE sending, and blocks until
    there's genuinely enough headroom. Reservations age out of the window
    after 60s the same way Groq's own quota window does.
    """

    def __init__(self, tpm_limit: float, tokens_per_request_estimate: float, safety_margin: float = 0.85):
        self._budget = tpm_limit * safety_margin
        self._estimate = tokens_per_request_estimate
        self._lock = threading.Lock()
        self._window: list[tuple[float, float]] = []  # (timestamp, reserved_tokens)
        self._cooldown_until = 0.0  # monotonic timestamp; shared across all worker threads

    def note_daily_limit_hit(self, wait_seconds: float):
        """
        Call this when a response indicates the DAILY (not per-minute) quota
        is exhausted. Sets a shared cooldown so every worker thread -- not
        just the one that hit the error -- waits it out together, instead of
        each independently retrying into the same exhausted daily budget.
        """
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, time.monotonic() + wait_seconds)

    def wait(self):
        while True:
            with self._lock:
                now = time.monotonic()
                if now < self._cooldown_until:
                    sleep_for = self._cooldown_until - now
                else:
                    self._window = [(t, tok) for t, tok in self._window if now - t < 60]
                    used = sum(tok for _, tok in self._window)
                    if used + self._estimate <= self._budget:
                        self._window.append((now, self._estimate))
                        return
                    sleep_for = 60.0 - (now - self._window[0][0]) + 0.2
            time.sleep(max(0.2, sleep_for))


def parse_suggested_retry_seconds(error_text: str) -> float | None:
    """
    Both Gemini and Groq's 429 responses often include the server's own
    suggested wait time. Groq's per-minute (TPM) errors use plain seconds
    ('try again in 4.5s'), but its per-day (TPD) errors use minutes+seconds
    ('try again in 3m4.03s') -- the previous version of this parser only
    matched the plain-seconds form, so daily-limit errors silently fell
    through to the short exponential backoff and retried every few seconds
    into a wall that wouldn't clear for minutes. Both forms are handled here.
    """
    # Minutes+seconds form: "3m4.03s", "5m50.35s"
    match = re.search(r"(\d+)m(\d+(?:\.\d+)?)s", error_text)
    if match:
        return float(match.group(1)) * 60.0 + float(match.group(2))
    # Plain-seconds form: "retryDelay: 33s", "try again in 4.5s"
    match = re.search(
        r"(?:retry(?:Delay)?|try again)['\"]?\s*[:=]?\s*(?:in\s*)?['\"]?(\d+(?:\.\d+)?)\s*s",
        error_text,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1))
    return None

# ---------------------------------------------------------------------------
# Domain vocabulary used to construct varied, structurally-grounded prompts.
# Extend these lists as your literature review turns up more terms.
# ---------------------------------------------------------------------------

REFRACTORY_ELEMENTS = ["W", "Mo", "Nb", "Ta", "Hf", "Zr", "Ti", "V", "Cr", "Re"]

PROCESSING_ROUTES = [
    "arc melting followed by drop casting",
    "vacuum induction melting",
    "powder metallurgy and spark plasma sintering",
    "laser additive manufacturing (directed energy deposition)",
    "mechanical alloying followed by hot pressing",
    "suction casting under an inert argon atmosphere",
]

SUBTOPICS = [
    "phase stability and the formation of BCC solid solutions",
    "microstructural features such as dendritic segregation and grain size",
    "oxidation behavior at elevated temperature",
    "thermodynamic considerations (mixing enthalpy, valence electron concentration)",
    "the effect of annealing or homogenization heat treatment on microstructure",
    "comparison with conventional Ni-based superalloys in high-temperature contexts",
    "secondary phase precipitation (Laves phases, intermetallics)",
    "recrystallization behavior and grain growth kinetics",
    "lattice distortion effects from atomic size mismatch",
    "environmental embrittlement and hydrogen effects",
    "high-temperature coating or surface protection strategies",
]

# The properties the downstream regression head will ultimately predict.
# Started as tensile strength / yield strength / hardness (the examples given
# early on) but that was illustrative, not the full target set -- expanded
# here to the broader set of mechanical properties commonly reported
# alongside those three in HEA literature, so the pretraining corpus builds
# vocabulary/context for all of them rather than just the original three.
TARGET_PROPERTIES = [
    "ultimate tensile strength",
    "yield strength",
    "hardness",
    "elastic (Young's) modulus",
    "fracture toughness",
    "elongation at fracture (ductility)",
    "compressive yield strength",
    "fatigue strength / fatigue life",
]

# These subtopics are the ones that matter most for the downstream regression
# task, so they are sampled more heavily than the general microstructure/
# oxidation subtopics above -- see PROPERTY_SUBTOPIC_WEIGHT below. Kept
# qualitative/no-numbers for the same reason as everything else at this
# pretraining stage, but the vocabulary and reasoning patterns here
# (grain size -> strength, solid solution strengthening -> yield, phase
# content -> hardness, precipitate spacing -> fracture toughness, etc.) are
# exactly what the fine-tuned regression head will need the encoder to
# already represent well.
PROPERTY_SUBTOPICS = [
    "qualitative tensile strength trends relative to composition and grain size",
    "qualitative yield strength trends and their relation to solid solution strengthening",
    "qualitative hardness trends across compositions and their relation to secondary phase content",
    "the relationship between grain size and both strength and hardness (Hall-Petch-type reasoning)",
    "work hardening behavior during tensile deformation",
    "strain rate sensitivity of strength properties",
    "temperature dependence of tensile strength and yield strength",
    "the qualitative correlation between hardness and yield strength (Tabor-type reasoning)",
    "the effect of secondary phase or precipitate content on hardness",
    "ductility-strength trade-offs (how gains in strength typically come at the cost of elongation)",
    "anisotropy of tensile properties in additively manufactured or textured samples",
    "elastic (Young's) modulus trends and their relation to bonding character and composition",
    "fracture toughness trends and their relation to phase content, grain boundary character, and crack path",
    "elongation at fracture and the microstructural features that promote or limit ductility",
    "compressive yield behavior, including asymmetry between tensile and compressive yield response",
    "fatigue crack initiation and propagation behavior, and features that influence fatigue life",
    "the effect of porosity or processing defects on fracture toughness and fatigue performance",
    "notch sensitivity and its relation to fracture toughness in brittle BCC compositions",
]
PROPERTY_SUBTOPIC_WEIGHT = 0.65  # fraction of single-alloy prompts drawing from PROPERTY_SUBTOPICS

TEST_METHODS = [
    "standard tensile testing following ASTM E8 methodology",
    "Vickers microhardness testing across multiple indentation sites",
    "compression testing to capture yield behavior in more brittle compositions",
    "nanoindentation mapping of local hardness and modulus variation across phases",
    "Rockwell hardness testing",
    "high-temperature tensile testing in a controlled-atmosphere furnace",
    "resonant ultrasound spectroscopy to determine elastic modulus",
    "three-point bend fracture toughness testing following ASTM E399/E1820",
    "extensometer-based elongation measurement during tensile testing",
    "compact-tension fracture toughness testing",
    "cyclic (fatigue) loading testing to characterize fatigue life",
    "instrumented indentation to extract both hardness and elastic modulus",
]

STYLES = [
    "a materials science journal abstract",
    "a technical report summary",
    "a textbook passage explaining the concept to a graduate student",
    "an experimental methods and observations section",
]

SYSTEM_PROMPT = (
    "You are a materials science domain-text generator. You write technically "
    "grounded, plausible passages about refractory high entropy alloys (HEAs) "
    "for use as unlabeled pretraining text, in support of a downstream model "
    "that will predict mechanical properties including ultimate tensile "
    "strength, yield strength, hardness, elastic modulus, fracture toughness, "
    "elongation at fracture, compressive yield strength, and fatigue "
    "strength. Rules:\n"
    "1. Do NOT invent specific numeric property values (no exact MPa, GPa, HV, "
    "or % elongation figures) -- describe directional trends and qualitative "
    "behavior only (e.g. 'finer grain size is associated with higher hardness "
    "and yield strength in this system').\n"
    "2. When the prompt concerns mechanical properties, ground the discussion "
    "in the actual microstructural/compositional mechanisms that drive those "
    "properties (grain size, solid solution strengthening, secondary phases, "
    "lattice distortion, porosity, precipitate spacing) rather than generic "
    "statements.\n"
    "3. Use correct alloy nomenclature (e.g. NbMoTaW, HfNbTaTiZr) and correct "
    "element symbols exactly as given.\n"
    "4. Keep passages self-contained, 100-180 words, single paragraph, no "
    "headers or bullet points.\n"
    "5. Vary sentence structure and vocabulary across passages -- do not reuse "
    "the same opening phrase."
)


def sample_composition(rng: random.Random) -> str:
    n_elements = rng.randint(3, 7)
    elements = rng.sample(REFRACTORY_ELEMENTS, n_elements)
    return "".join(elements)


def build_user_prompt(rng: random.Random) -> dict:
    style = rng.choice(STYLES)

    # ~25% of prompts compare two compositions on a property trend, since
    # contrastive language ("X shows higher hardness than Y because...") is
    # exactly the kind of signal that helps an encoder later distinguish
    # alloys by property level, more so than isolated single-alloy passages.
    if rng.random() < 0.25:
        comp_a = sample_composition(rng)
        comp_b = sample_composition(rng)
        subtopic = rng.choice(PROPERTY_SUBTOPICS)
        route = rng.choice(PROCESSING_ROUTES)
        prompt = (
            f"Write a passage in the style of {style} comparing the refractory "
            f"high entropy alloys {comp_a} and {comp_b}, both processed via "
            f"{route}. Focus on {subtopic}, explaining which alloy would "
            f"plausibly trend higher or lower and why, without inventing exact "
            f"numeric values."
        )
        return {
            "prompt": prompt,
            "meta": {
                "composition": f"{comp_a} vs {comp_b}",
                "processing_route": route,
                "subtopic": subtopic,
                "style": style,
                "kind": "comparative",
            },
        }

    composition = sample_composition(rng)
    route = rng.choice(PROCESSING_ROUTES)
    use_property_subtopic = rng.random() < PROPERTY_SUBTOPIC_WEIGHT
    subtopic = rng.choice(PROPERTY_SUBTOPICS) if use_property_subtopic else rng.choice(SUBTOPICS)

    prompt = (
        f"Write a passage in the style of {style} about the refractory high "
        f"entropy alloy {composition}, processed via {route}. Focus primarily "
        f"on {subtopic}."
    )
    if use_property_subtopic and rng.random() < 0.5:
        test_method = rng.choice(TEST_METHODS)
        prompt += f" Frame the discussion around observations from {test_method}."

    return {
        "prompt": prompt,
        "meta": {
            "composition": composition,
            "processing_route": route,
            "subtopic": subtopic,
            "style": style,
            "kind": "single",
        },
    }


def generate_one(client: "Groq", limiter: TokenBucketLimiter, rng_seed: int, model: str, max_retries: int = 40) -> dict:
    rng = random.Random(rng_seed)
    spec = build_user_prompt(rng)

    attempt = 0
    daily_limit_hits = 0  # tracked separately -- these shouldn't burn through max_retries as fast as transient errors
    while attempt < max_retries:
        limiter.wait()  # pace every attempt, not just the first -- retries count against the quota too
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": spec["prompt"]},
                ],
                reasoning_effort="low",
            )
            text = (resp.choices[0].message.content or "").strip()
            if len(text) < 50:
                raise ValueError("Generated passage too short, likely a refusal/empty response")
            return {
                "text": text,
                "composition": spec["meta"]["composition"],
                "processing_route": spec["meta"]["processing_route"],
                "subtopic": spec["meta"]["subtopic"],
                "style": spec["meta"]["style"],
                "kind": spec["meta"]["kind"],
                "id": hashlib.sha1(text.encode("utf-8")).hexdigest()[:16],
            }
        except Exception as e:  # noqa: BLE001 - broad on purpose, this is a batch job
            error_text = str(e)
            suggested = parse_suggested_retry_seconds(error_text)
            is_daily_limit = "tokens per day" in error_text or "TPD" in error_text

            if is_daily_limit and suggested is not None:
                # The DAILY quota is exhausted, not the per-minute one -- no amount
                # of local pacing fixes this, only real elapsed time does. Register
                # a shared cooldown so every worker thread waits it out together
                # instead of each one independently retrying into the same wall.
                daily_limit_hits += 1
                limiter.note_daily_limit_hit(suggested + 2.0)
                print(f"[warn] seed={rng_seed} DAILY token quota hit, cooling down {suggested:.0f}s (shared across workers)", file=sys.stderr)
                # Daily-quota waits don't count against max_retries the same way transient
                # errors do -- only cap it to avoid a truly infinite loop on a stuck account.
                if daily_limit_hits > 200:
                    return None
                continue

            wait = suggested + 1.0 if suggested is not None else min(120, 3 * (2 ** attempt))
            print(f"[warn] seed={rng_seed} attempt={attempt} error={error_text} retrying in {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)
            attempt += 1
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--num-samples", type=int, default=2000)
    ap.add_argument("--out", type=str, default="hea_corpus.jsonl")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--tpm",
        type=float,
        default=8000.0,
        help="Groq's tokens-per-minute quota for this model (check console.groq.com/settings/"
        "billing for your account's actual limit -- 8000 is the current free-tier default for "
        "openai/gpt-oss-120b). An internal 85%% safety margin is applied on top of this.",
    )
    ap.add_argument(
        "--est-tokens",
        type=float,
        default=750.0,
        help="Estimated tokens (prompt + system + completion) per request, used to reserve "
        "budget against --tpm before sending. Observed requests run ~550-700; 750 leaves margin.",
    )
    ap.add_argument("--model", type=str, default="openai/gpt-oss-120b")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Append to --out instead of overwriting, and skip content hashes already present in it.",
    )
    args = ap.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        sys.exit("Set GROQ_API_KEY in your environment first.")

    client = Groq()
    limiter = TokenBucketLimiter(tpm_limit=args.tpm, tokens_per_request_estimate=args.est_tokens)
    seeds = list(range(args.seed, args.seed + args.num_samples))

    written = 0
    seen_hashes = set()
    t0 = time.time()

    if args.resume and os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8") as f_in:
            for line in f_in:
                try:
                    seen_hashes.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"[resume] found {len(seen_hashes)} existing passages in {args.out}")

    file_mode = "a" if args.resume else "w"
    with open(args.out, file_mode, encoding="utf-8") as f_out:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(generate_one, client, limiter, s, args.model): s for s in seeds
            }
            for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                record = future.result()
                if record is None:
                    continue
                if record["id"] in seen_hashes:
                    continue  # drop near-duplicate/duplicate passage
                seen_hashes.add(record["id"])
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
                if i % 50 == 0:
                    elapsed = time.time() - t0
                    print(f"[progress] {i}/{args.num_samples} requested, {written} written, {elapsed:.0f}s elapsed")

    print(f"Done. Wrote {written} unique passages to {args.out}")


if __name__ == "__main__":
    main()