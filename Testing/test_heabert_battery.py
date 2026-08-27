"""
Systematic test battery for HEABERT checkpoints.

Purpose
-------
An upgrade over eyeballing a handful of fill-mask sentences: this scores a
larger, categorized probe battery with pre-defined correct answers (so you
get hit@1, hit@5, and mean reciprocal rank -- real numbers, not vibes), and
runs the full held-out perplexity comparison (not capped at 50 passages).
It compares as many models as you like in one run -- base ModernBERT plus
however many of your HEABERT checkpoints (v1/v2/v3/...) you want lined up
side by side, so you can actually track whether checkpoint N+1 improved on
checkpoint N, rather than re-reading separate logs and eyeballing numbers.

Still no labels, no regression head -- this is purely testing what the
continued pretraining taught the encoder about domain language.

Requirements
------------
    pip install "transformers>=4.48" torch --break-system-packages

Usage
-----
    python test_heabert_battery.py \\
        --models base=answerdotai/ModernBERT-base \\
                 v1=./heabert-base-pretrained/final \\
                 v2=./heabert-base-pretrained_2/final \\
                 v3=./heabert-base-pretrained_3/final \\
        --corpus hea_corpus_groq_combined_2.jsonl \\
        --eval_sample_size all
"""

import argparse
import json
import math
import random

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer, DataCollatorForLanguageModeling, pipeline

# Each probe: a cloze sentence, the category it belongs to (matching the
# corpus's own subtopic groupings where possible), and the set of answers
# that count as correct. Some probes accept a short list of synonyms/close
# variants since more than one word can be a legitimate domain-correct fill.
PROBE_BATTERY = [
    # phase stability
    {"category": "phase_stability", "sentence": "NbMoTaW is a refractory high entropy alloy with a body-centered [MASK] crystal structure.", "gold": ["cubic"]},
    {"category": "phase_stability", "sentence": "A low valence electron concentration generally favors a body-centered [MASK] solid solution in refractory HEAs.", "gold": ["cubic"]},
    {"category": "phase_stability", "sentence": "High configurational entropy tends to stabilize a single-phase [MASK] solution over ordered intermetallic compounds.", "gold": ["solid"]},
    # lattice distortion
    {"category": "lattice_distortion", "sentence": "The alloy exhibits pronounced lattice [MASK] due to the large atomic size mismatch among its constituent elements.", "gold": ["distortion", "distortions"]},
    {"category": "lattice_distortion", "sentence": "Severe lattice distortion arises from the mismatch in atomic [MASK] among the constituent elements.", "gold": ["size", "radius", "radii"]},
    {"category": "lattice_distortion", "sentence": "X-ray diffraction peak broadening is often used to quantify lattice [MASK] in multi-principal-element alloys.", "gold": ["distortion", "distortions", "strain"]},
    # hardness / indentation
    {"category": "hardness", "sentence": "Vickers indentation is commonly used to measure the [MASK] of refractory high entropy alloys.", "gold": ["hardness"]},
    {"category": "hardness", "sentence": "Increasing the volume fraction of secondary precipitates generally raises the material's [MASK].", "gold": ["hardness", "strength"]},
    {"category": "hardness", "sentence": "A finer, more uniformly distributed precipitate network impedes dislocation glide and raises [MASK].", "gold": ["hardness", "strength"]},
    # secondary phases / precipitation
    {"category": "secondary_phases", "sentence": "The addition of chromium tends to promote the formation of brittle [MASK] phases at grain boundaries.", "gold": ["secondary", "intermetallic", "ordered"]},
    {"category": "secondary_phases", "sentence": "Laves-type precipitates commonly form as a [MASK] phase in refractory high entropy alloys.", "gold": ["secondary"]},
    {"category": "secondary_phases", "sentence": "Excessive coarsening of secondary [MASK] can reduce their effectiveness as barriers to dislocation motion.", "gold": ["precipitates", "phases", "particles"]},
    # hall-petch / grain size
    {"category": "hall_petch", "sentence": "Finer grains impede dislocation motion, which is the basis of the Hall-Petch [MASK] mechanism.", "gold": ["strengthening", "slip", "hardening"]},
    {"category": "hall_petch", "sentence": "Reducing the grain size typically raises both the yield strength and the [MASK] according to Hall-Petch behavior.", "gold": ["hardness", "strength"]},
    {"category": "hall_petch", "sentence": "According to the Hall-Petch relationship, a smaller grain [MASK] corresponds to higher yield strength.", "gold": ["size"]},
    # oxidation
    {"category": "oxidation", "sentence": "At elevated temperature, the alloy's oxidation resistance is governed by the formation of a protective [MASK].", "gold": ["scale", "layer", "oxide"]},
    {"category": "oxidation", "sentence": "Chromium additions commonly promote the formation of a protective Cr2O3 [MASK] at high temperature.", "gold": ["scale", "layer"]},
    {"category": "oxidation", "sentence": "Molybdenum's volatile oxide can lead to porous, non-adherent oxide [MASK] formation at high temperature.", "gold": ["scale", "scales", "layer", "layers"]},
    # tensile / yield strength
    {"category": "tensile_yield", "sentence": "Solid-solution strengthening from the large atomic size mismatch tends to raise the alloy's yield [MASK].", "gold": ["strength"]},
    {"category": "tensile_yield", "sentence": "Work hardening during tensile deformation is reflected in a rising slope of the stress-strain [MASK].", "gold": ["curve"]},
    {"category": "tensile_yield", "sentence": "Ductility-strength trade-offs mean that gains in strength typically come at the cost of [MASK].", "gold": ["elongation", "ductility"]},
    # elastic modulus
    {"category": "modulus", "sentence": "Resonant ultrasound spectroscopy is a common technique for measuring a material's elastic [MASK].", "gold": ["modulus"]},
    {"category": "modulus", "sentence": "Stronger, more directional metallic bonding tends to raise a material's Young's [MASK].", "gold": ["modulus"]},
    # fracture toughness
    {"category": "fracture_toughness", "sentence": "Crack deflection and branching around secondary phase particles tends to raise a material's fracture [MASK].", "gold": ["toughness"]},
    {"category": "fracture_toughness", "sentence": "A sharper notch root radius generally increases notch [MASK] in brittle BCC alloys.", "gold": ["sensitivity"]},
    # fatigue
    {"category": "fatigue", "sentence": "Residual porosity commonly acts as a preferential site for fatigue crack [MASK].", "gold": ["initiation", "nucleation"]},
    {"category": "fatigue", "sentence": "Crack-tip blunting by ductile secondary phases can extend a material's fatigue [MASK].", "gold": ["life", "resistance", "endurance"]},
    # comparison with Ni superalloys
    {"category": "ni_superalloy_comparison", "sentence": "Unlike Ni-based superalloys, most refractory HEAs lack an ordered gamma-prime [MASK] phase.", "gold": ["precipitate", "precipitates", "strengthening"]},
    {"category": "ni_superalloy_comparison", "sentence": "Refractory HEAs generally offer a higher melting point than conventional Ni-based [MASK].", "gold": ["superalloys", "superalloy", "alloys"]},
]


def score_fill_mask(model_path: str, label: str, top_k: int = 10):
    print(f"\n{'=' * 70}\nPROBE BATTERY -- {label} ({model_path})\n{'=' * 70}")
    fill_mask = pipeline("fill-mask", model=model_path, tokenizer=model_path, top_k=top_k)

    category_stats = {}  # category -> {hit1: [...], hit5: [...], rr: [...]}
    for probe in PROBE_BATTERY:
        cat = probe["category"]
        gold = set(g.lower().strip() for g in probe["gold"])
        try:
            results = fill_mask(probe["sentence"])
        except Exception as e:  # noqa: BLE001 - keep scoring the rest even if one probe trips something up
            print(f"  [error scoring probe in category {cat}: {e}]")
            continue

        predicted_tokens = [r["token_str"].strip().lower() for r in results]
        hit1 = 1.0 if predicted_tokens and predicted_tokens[0] in gold else 0.0
        hit5 = 1.0 if any(t in gold for t in predicted_tokens[:5]) else 0.0
        rr = 0.0
        for rank, tok in enumerate(predicted_tokens, start=1):
            if tok in gold:
                rr = 1.0 / rank
                break

        stats = category_stats.setdefault(cat, {"hit1": [], "hit5": [], "rr": []})
        stats["hit1"].append(hit1)
        stats["hit5"].append(hit5)
        stats["rr"].append(rr)

    # Per-category breakdown
    print(f"\n  {'Category':<26} {'Hit@1':>8} {'Hit@5':>8} {'MRR':>8}  (n)")
    all_hit1, all_hit5, all_rr = [], [], []
    for cat, stats in sorted(category_stats.items()):
        n = len(stats["hit1"])
        h1 = sum(stats["hit1"]) / n
        h5 = sum(stats["hit5"]) / n
        mrr = sum(stats["rr"]) / n
        print(f"  {cat:<26} {h1:>8.2f} {h5:>8.2f} {mrr:>8.2f}  ({n})")
        all_hit1.extend(stats["hit1"])
        all_hit5.extend(stats["hit5"])
        all_rr.extend(stats["rr"])

    overall = {
        "hit1": sum(all_hit1) / len(all_hit1) if all_hit1 else 0.0,
        "hit5": sum(all_hit5) / len(all_hit5) if all_hit5 else 0.0,
        "mrr": sum(all_rr) / len(all_rr) if all_rr else 0.0,
    }
    print(f"\n  {'OVERALL':<26} {overall['hit1']:>8.2f} {overall['hit5']:>8.2f} {overall['mrr']:>8.2f}  ({len(all_hit1)})")
    return overall


def compute_perplexity(model_path: str, texts: list, mlm_probability: float, seed: int, max_length: int, batch_size: int = 8):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForMaskedLM.from_pretrained(model_path)
    model.eval()

    encodings = [tokenizer(t, truncation=True, max_length=max_length) for t in texts]
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=True, mlm_probability=mlm_probability)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    per_batch_losses = []
    skipped_batches = 0
    with torch.no_grad():
        for i in range(0, len(encodings), batch_size):
            batch = encodings[i : i + batch_size]
            features = [{"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]} for b in batch]
            # Same seed sequence applied identically to every model so all models
            # get the SAME masked positions on the SAME passages -- otherwise a
            # perplexity difference could just reflect an easier/harder random mask,
            # not real model quality.
            torch.manual_seed(seed + i)
            random.seed(seed + i)
            collated = collator(features)

            if (collated["labels"] != -100).sum().item() == 0:
                skipped_batches += 1
                continue

            collated = {k: v.to(device) for k, v in collated.items()}
            outputs = model(**collated)
            if torch.isnan(outputs.loss):
                skipped_batches += 1
                continue
            per_batch_losses.append(outputs.loss.item())

    if skipped_batches:
        print(f"  [warn] skipped {skipped_batches} batch(es) with zero valid masked tokens")
    if not per_batch_losses:
        return float("nan"), float("nan"), float("nan")

    mean_loss = sum(per_batch_losses) / len(per_batch_losses)
    variance = sum((l - mean_loss) ** 2 for l in per_batch_losses) / len(per_batch_losses)
    std_loss = math.sqrt(variance)
    try:
        perplexity = math.exp(mean_loss)
    except OverflowError:
        perplexity = float("inf")
    return mean_loss, std_loss, perplexity


def parse_model_arg(arg: str):
    if "=" not in arg:
        raise argparse.ArgumentTypeError(f"Expected name=path, got: {arg}")
    name, path = arg.split("=", 1)
    return name, path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--models",
        type=parse_model_arg,
        nargs="+",
        required=True,
        help="One or more name=path pairs, e.g. base=answerdotai/ModernBERT-base v3=./heabert-base-pretrained_3/final",
    )
    ap.add_argument("--corpus", type=str, default=None, help="JSONL corpus (needs a 'text' field) for the perplexity comparison.")
    ap.add_argument("--eval_sample_size", type=str, default="200", help="Number of held-out passages to use, or 'all' for the entire file.")
    ap.add_argument("--mlm_probability", type=float, default=0.15)
    ap.add_argument("--max_length", type=int, default=384)
    ap.add_argument("--top_k", type=int, default=10, help="Fill-mask depth for hit@5/MRR scoring -- needs to be >=5.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip_battery", action="store_true", help="Skip the probe battery and only run perplexity.")
    args = ap.parse_args()

    battery_results = {}
    if not args.skip_battery:
        for name, path in args.models:
            battery_results[name] = score_fill_mask(path, name, top_k=max(5, args.top_k))

    if args.corpus:
        print(f"\n{'=' * 70}\nPERPLEXITY COMPARISON on {args.corpus}\n{'=' * 70}")
        texts = []
        with open(args.corpus, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    texts.append(json.loads(line)["text"])
                except (json.JSONDecodeError, KeyError):
                    continue
        rng = random.Random(args.seed)
        rng.shuffle(texts)
        if args.eval_sample_size.lower() != "all":
            texts = texts[: int(args.eval_sample_size)]
        print(f"Using {len(texts)} passages.\n")

        ppl_results = {}
        for name, path in args.models:
            mean_loss, std_loss, ppl = compute_perplexity(path, texts, args.mlm_probability, args.seed, args.max_length)
            ppl_results[name] = (mean_loss, std_loss, ppl)
            print(f"  {name:<10} loss={mean_loss:.4f} (+/-{std_loss:.4f} across batches)  perplexity={ppl:.2f}")

        # Summary table combining battery + perplexity, if both were run
        if battery_results:
            print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}")
            print(f"  {'Model':<10} {'Hit@1':>8} {'Hit@5':>8} {'MRR':>8} {'Perplexity':>12}")
            for name, _ in args.models:
                b = battery_results.get(name, {"hit1": float("nan"), "hit5": float("nan"), "mrr": float("nan")})
                ppl = ppl_results.get(name, (None, None, float("nan")))[2]
                print(f"  {name:<10} {b['hit1']:>8.2f} {b['hit5']:>8.2f} {b['mrr']:>8.2f} {ppl:>12.2f}")


if __name__ == "__main__":
    main()
