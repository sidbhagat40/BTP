"""
Build frozen language probes from data/splits/probe_pool.jsonl.

Never uses train/val texts. Writes:
  data/probes/cloze.jsonl
  data/probes/mcq.jsonl
  data/probes/tf.jsonl
  data/probes/probes_manifest.json

Usage:
  python scripts/generate_probes.py
"""

from __future__ import annotations

import argparse
import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_POOL = REPO_ROOT / "data" / "splits" / "probe_pool.jsonl"
OUT_DIR = REPO_ROOT / "data" / "probes"

# Distinctive single-token (or short) cloze targets common in RHEA prose
CLOZE_TARGETS = [
    ("Hall-Petch", ["Hall-Petch", "Hall–Petch", "Hall‑Petch"]),
    ("sintering", ["sintering", "sintered"]),
    ("hardness", ["hardness"]),
    ("ductility", ["ductility"]),
    ("porosity", ["porosity", "pores"]),
    ("annealing", ["annealing", "annealed", "homogenization"]),
    ("dislocation", ["dislocation", "dislocations"]),
    ("precipitation", ["precipitation", "precipitates", "precipitate"]),
    ("elongation", ["elongation"]),
    ("yield", ["yield"]),
]

ROUTE_SHORT = {
    "powder metallurgy and spark plasma sintering": "spark plasma sintering",
    "laser additive manufacturing (directed energy deposition)": "directed energy deposition",
    "mechanical alloying followed by hot pressing": "mechanical alloying and hot pressing",
    "suction casting under an inert argon atmosphere": "suction casting",
    "arc melting followed by drop casting": "arc melting and drop casting",
    "vacuum induction melting": "vacuum induction melting",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    return s


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def find_span(text: str, variants: list[str]) -> tuple[str, int, int] | None:
    t = norm(text)
    for v in variants:
        m = re.search(re.escape(norm(v)), t, flags=re.IGNORECASE)
        if m:
            return t[m.start() : m.end()], m.start(), m.end()
    return None


def make_cloze(rows: list[dict], rng: random.Random) -> list[dict]:
    probes = []
    used_ids: set[str] = set()
    # Prefer one cloze per record when a target exists
    shuffled = list(rows)
    rng.shuffle(shuffled)
    target_order = list(CLOZE_TARGETS)
    rng.shuffle(target_order)

    for row in shuffled:
        text = norm(row["text"])
        hit = None
        gold_key = None
        for key, variants in target_order:
            span = find_span(text, variants)
            if span:
                hit = span
                gold_key = key
                break
        if not hit:
            continue
        surface, start, end = hit
        # single [MASK] — tokenizer may use more tokens; eval will use candidate ranking
        cloze_text = text[:start] + "[MASK]" + text[end:]
        # keep probes reasonably short for speed: window around mask
        left = max(0, start - 180)
        right = min(len(cloze_text), start + len("[MASK]") + 180)
        window = cloze_text[left:right].strip()
        if left > 0:
            window = "..." + window
        if right < len(cloze_text):
            window = window + "..."
        probes.append(
            {
                "id": f"cloze_{row['id']}_{gold_key}",
                "source_id": row["id"],
                "type": "cloze",
                "text": window,
                "gold": gold_key,
                "gold_surface": surface,
                "aliases": [a.lower() for a in next(v for k, v in CLOZE_TARGETS if k == gold_key)],
                "composition": row["composition"],
                "subtopic": row["subtopic"],
            }
        )
        used_ids.add(row["id"])
        if len(probes) >= 120:
            break

    # Composition cloze via short template (candidate ranking, not single-token fill)
    comps = []
    for row in shuffled:
        if row["kind"] != "single":
            continue
        if " vs " in row["composition"]:
            continue
        comps.append(row)
    rng.shuffle(comps)
    for row in comps[:80]:
        route = ROUTE_SHORT.get(row["processing_route"], row["processing_route"])
        probes.append(
            {
                "id": f"cloze_comp_{row['id']}",
                "source_id": row["id"],
                "type": "cloze_composition",
                "text": (
                    f"The refractory high-entropy alloy [MASK] was consolidated "
                    f"via {route}."
                ),
                "gold": row["composition"],
                "candidates": None,  # filled later with distractors
                "composition": row["composition"],
                "subtopic": row["subtopic"],
            }
        )
    return probes


def fill_composition_candidates(probes: list[dict], all_rows: list[dict], rng: random.Random) -> None:
    pool = sorted(
        {
            r["composition"]
            for r in all_rows
            if r["kind"] == "single" and " vs " not in r["composition"]
        }
    )
    for p in probes:
        if p["type"] != "cloze_composition":
            continue
        gold = p["gold"]
        distractors = [c for c in pool if c != gold]
        rng.shuffle(distractors)
        p["candidates"] = [gold] + distractors[:3]
        rng.shuffle(p["candidates"])


def strip_route_mentions(text: str, route: str) -> str:
    """Remove gold route phrases so MCQ is not a trivial string match."""
    t = norm(text)
    phrases = {route, ROUTE_SHORT.get(route, route)}
    # also strip common fragments
    phrases.update(
        [
            "spark-plasma sintering",
            "spark plasma sintering",
            "directed energy deposition",
            "mechanical alloying",
            "hot pressing",
            "suction casting",
            "arc melting",
            "drop casting",
            "vacuum induction melting",
            "powder metallurgy",
        ]
    )
    for p in sorted(phrases, key=len, reverse=True):
        t = re.sub(re.escape(norm(p)), "[PROCESS]", t, flags=re.IGNORECASE)
    return t


def make_mcq(rows: list[dict], rng: random.Random) -> list[dict]:
    routes = sorted({r["processing_route"] for r in rows})
    probes = []
    shuffled = list(rows)
    rng.shuffle(shuffled)

    # Processing-route MCQ (context with route phrases redacted)
    for row in shuffled:
        gold = row["processing_route"]
        others = [r for r in routes if r != gold]
        rng.shuffle(others)
        options = [gold] + others[:3]
        rng.shuffle(options)
        letter = ["A", "B", "C", "D"]
        labeled = {letter[i]: options[i] for i in range(4)}
        gold_letter = next(k for k, v in labeled.items() if v == gold)
        probes.append(
            {
                "id": f"mcq_route_{row['id']}",
                "source_id": row["id"],
                "type": "mcq_route",
                "question": (
                    f"According to the passage about {row['composition']}, "
                    f"which processing route was used?"
                ),
                "context": strip_route_mentions(row["text"], gold)[:700],
                "options": labeled,
                "gold": gold_letter,
                "gold_text": gold,
            }
        )
        if len([p for p in probes if p["type"] == "mcq_route"]) >= 60:
            break

    # Hall-Petch / grain-size conceptual MCQ
    grain_rows = [
        r
        for r in shuffled
        if "grain size" in r["subtopic"].lower()
        or "hall-petch" in norm(r["subtopic"]).lower()
    ]
    for row in grain_rows[:40]:
        options = {
            "A": "Finer grains typically increase strength and hardness (Hall-Petch-type).",
            "B": "Finer grains typically decrease yield strength and hardness.",
            "C": "Grain size has no systematic effect on hardness in BCC RHEAs.",
            "D": "Coarser grains always maximize both strength and ductility together.",
        }
        probes.append(
            {
                "id": f"mcq_hp_{row['id']}",
                "source_id": row["id"],
                "type": "mcq_concept",
                "question": (
                    f"For {row['composition']}, which statement best matches "
                    f"Hall-Petch-type grain-size strengthening?"
                ),
                "context": norm(row["text"])[:700],
                "options": options,
                "gold": "A",
                "gold_text": options["A"],
            }
        )

    trade_rows = [
        r
        for r in shuffled
        if "ductility-strength" in r["subtopic"].lower()
        or "trade-off" in r["subtopic"].lower()
        or "trade off" in r["subtopic"].lower()
    ]
    for row in trade_rows[:40]:
        options = {
            "A": "Gains in strength typically reduce elongation / ductility.",
            "B": "Higher strength always increases elongation simultaneously.",
            "C": "Ductility is independent of strength in all RHEAs.",
            "D": "Trade-offs only appear in pure metals, never in HEAs.",
        }
        probes.append(
            {
                "id": f"mcq_trade_{row['id']}",
                "source_id": row["id"],
                "type": "mcq_concept",
                "question": (
                    f"Regarding strength–ductility behavior discussed for "
                    f"{row['composition']}, which claim is most consistent?"
                ),
                "context": norm(row["text"])[:700],
                "options": options,
                "gold": "A",
                "gold_text": options["A"],
            }
        )
    return probes


def make_tf(rows: list[dict], rng: random.Random) -> list[dict]:
    probes = []
    shuffled = list(rows)
    rng.shuffle(shuffled)

    for row in shuffled[:100]:
        route = ROUTE_SHORT.get(row["processing_route"], row["processing_route"])
        true_stmt = (
            f"The alloy system {row['composition']} is discussed in the context of "
            f"processing by {route}."
        )
        # false: wrong route
        other_routes = [ROUTE_SHORT[r] for r in ROUTE_SHORT if r != row["processing_route"]]
        wrong = rng.choice(other_routes)
        false_stmt = (
            f"The alloy system {row['composition']} is discussed in the context of "
            f"processing by {wrong}."
        )
        probes.append(
            {
                "id": f"tf_route_{row['id']}",
                "source_id": row["id"],
                "type": "tf",
                "statement": true_stmt,
                "negation": false_stmt,
                "gold": "true",
            }
        )

    # Conceptual T/F
    concepts = [
        (
            "Finer grains typically raise yield strength and hardness via Hall-Petch-type strengthening.",
            "Finer grains typically lower yield strength and hardness in Hall-Petch-type reasoning.",
            "true",
        ),
        (
            "In many alloy designs, increasing strength comes at the expense of ductility.",
            "In all refractory HEAs, increasing strength always increases ductility as well.",
            "true",
        ),
        (
            "Residual porosity can act as crack nucleation sites and harm toughness or fatigue life.",
            "Residual porosity never affects fracture toughness in sintered refractory HEAs.",
            "true",
        ),
        (
            "Spark plasma sintering is a powder-metallurgy consolidation route used for some RHEAs.",
            "Spark plasma sintering is only used for polymer matrix composites, never metals.",
            "true",
        ),
    ]
    for i, (stmt, neg, gold) in enumerate(concepts):
        # duplicate with slight id variants for stability (still small set)
        probes.append(
            {
                "id": f"tf_concept_{i}",
                "source_id": None,
                "type": "tf_concept",
                "statement": stmt,
                "negation": neg,
                "gold": gold,
            }
        )
    return probes


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--probe-pool", type=Path, default=PROBE_POOL)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    rows = load_jsonl(args.probe_pool)
    print(f"Loaded probe_pool: {len(rows)} from {args.probe_pool}")

    cloze = make_cloze(rows, rng)
    fill_composition_candidates(cloze, rows, rng)
    mcq = make_mcq(rows, rng)
    tf = make_tf(rows, rng)

    out = args.out_dir
    write_jsonl(out / "cloze.jsonl", cloze)
    write_jsonl(out / "mcq.jsonl", mcq)
    write_jsonl(out / "tf.jsonl", tf)

    by_type: dict[str, int] = defaultdict(int)
    for p in cloze + mcq + tf:
        by_type[p["type"]] += 1

    manifest = {
        "seed": args.seed,
        "source": str(args.probe_pool.as_posix()),
        "counts": {
            "cloze_file": len(cloze),
            "mcq_file": len(mcq),
            "tf_file": len(tf),
            "by_type": dict(by_type),
        },
        "notes": [
            "Generated only from probe_pool.jsonl (no train/val leakage).",
            "Evaluate vanilla ModernBERT-large vs artifacts/hea-bert-synth/best_or_final.",
        ],
    }
    (out / "probes_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["counts"], indent=2))
    print(f"Wrote probes under {out}")


if __name__ == "__main__":
    main()
