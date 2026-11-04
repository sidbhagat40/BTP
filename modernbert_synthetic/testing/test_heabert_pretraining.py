"""
Sanity-test the continued-pretrained HEABERT checkpoint against the
original, un-adapted ModernBERT-base -- BEFORE building a regression or
classification head.

Purpose
-------
This answers "did the continued MLM pretraining actually teach the model
anything domain-relevant?" using two complementary checks that need no
labeled data at all:

1. FILL-MASK PROBING (qualitative): a handful of hand-written sentences
   with a key domain term masked out (crystal structure, hardness,
   lattice distortion, etc.). You read the top-5 predictions from both
   models side by side and judge for yourself whether HEABERT's guesses
   are more domain-appropriate than base ModernBERT's.

2. PERPLEXITY COMPARISON (quantitative): both models are evaluated on the
   SAME masked version of the same held-out text (same random mask
   positions, enforced via a fixed seed applied identically to both), so
   the comparison isn't confounded by different masks landing on
   different words. A lower perplexity for HEABERT than base ModernBERT
   on your domain text is direct evidence the continued pretraining
   helped; if they're close or HEABERT is worse, that's a real signal
   worth noticing, not something to explain away.

This script does NOT involve the regression head or any numeric labels --
it's purely testing the encoder's language understanding, which is all
continued pretraining was ever meant to produce.

Requirements
------------
    pip install "transformers>=4.48" torch --break-system-packages

Usage
-----
    python test_heabert_pretraining.py \\
        --heabert_dir ./heabert-base-pretrained/final \\
        --base_model_name answerdotai/ModernBERT-base \\
        --corpus hea_corpus.jsonl
"""

import argparse
import json
import math
import random

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer, DataCollatorForLanguageModeling, pipeline

# Hand-written cloze sentences probing domain vocabulary the corpus was
# specifically designed to cover. Feel free to add your own -- the more
# specific to your actual use case, the more informative this is.
PROBE_SENTENCES = [
    "NbMoTaW is a refractory high entropy alloy with a body-centered [MASK] crystal structure.",
    "Reducing the grain size typically raises both the yield strength and the [MASK] according to Hall-Petch behavior.",
    "The alloy exhibits pronounced lattice [MASK] due to the large atomic size mismatch among its constituent elements.",
    "Vickers indentation is commonly used to measure the [MASK] of refractory high entropy alloys.",
    "The addition of chromium tends to promote the formation of brittle [MASK] phases at grain boundaries.",
    "Increasing the volume fraction of secondary precipitates generally raises the material's [MASK].",
    "At elevated temperature, the alloy's oxidation resistance is governed by the formation of a protective [MASK].",
    "Finer grains impede dislocation motion, which is the basis of the Hall-Petch [MASK] mechanism.",
]


def run_fill_mask_probes(model_path: str, label: str):
    print(f"\n{'=' * 70}\nFILL-MASK PROBES -- {label} ({model_path})\n{'=' * 70}")
    fill_mask = pipeline("fill-mask", model=model_path, tokenizer=model_path, top_k=5)
    for sentence in PROBE_SENTENCES:
        print(f"\n  {sentence}")
        try:
            results = fill_mask(sentence)
        except Exception as e:  # noqa: BLE001 - keep probing the rest even if one sentence's tokenization trips something up
            print(f"    [error running this probe: {e}]")
            continue
        for r in results:
            print(f"    {r['token_str']!r:20} score={r['score']:.3f}")


def compute_perplexity(model_path: str, texts: list, mlm_probability: float, seed: int, max_length: int, batch_size: int = 8):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForMaskedLM.from_pretrained(model_path)
    model.eval()

    encodings = [tokenizer(t, truncation=True, max_length=max_length) for t in texts]
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=True, mlm_probability=mlm_probability)

    total_loss = 0.0
    total_batches = 0
    skipped_batches = 0
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    with torch.no_grad():
        for i in range(0, len(encodings), batch_size):
            batch = encodings[i : i + batch_size]
            features = [{"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]} for b in batch]
            # Re-seed identically before every batch on every model call so the SAME
            # positions get masked regardless of which model (base or HEABERT) is
            # being evaluated -- otherwise a "lower perplexity" could just mean an
            # easier random mask landed on this model's batch, not real improvement.
            torch.manual_seed(seed + i)
            random.seed(seed + i)
            collated = collator(features)

            # DataCollatorForLanguageModeling never masks special tokens (including
            # [UNK]) -- on a batch where every token happens to end up special/unmasked
            # (degenerate short text, or a broken tokenizer), there are zero valid loss
            # targets and the model's internal mean-reduction silently divides by zero
            # into NaN. Skip such batches explicitly rather than let that NaN corrupt
            # the whole aggregate without any indication of why.
            if (collated["labels"] != -100).sum().item() == 0:
                skipped_batches += 1
                continue

            collated = {k: v.to(device) for k, v in collated.items()}
            outputs = model(**collated)
            if torch.isnan(outputs.loss):
                skipped_batches += 1
                continue
            total_loss += outputs.loss.item()
            total_batches += 1

    if skipped_batches:
        print(f"  [warn] skipped {skipped_batches} batch(es) with zero valid masked tokens (see note above on why this can happen)")
    if total_batches == 0:
        print("  [warn] every batch was skipped -- cannot compute a perplexity for this model on this data.")
        return float("nan"), float("nan")

    avg_loss = total_loss / total_batches
    try:
        perplexity = math.exp(avg_loss)
    except OverflowError:
        perplexity = float("inf")
    return avg_loss, perplexity


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--heabert_dir", type=str, default="./heabert-base-pretrained/final")
    ap.add_argument("--base_model_name", type=str, default="answerdotai/ModernBERT-base")
    ap.add_argument("--corpus", type=str, default=None, help="JSONL corpus (needs a 'text' field) for the perplexity comparison. If omitted, only fill-mask probing runs.")
    ap.add_argument("--eval_sample_size", type=int, default=50, help="How many passages from --corpus to use for the perplexity comparison.")
    ap.add_argument("--mlm_probability", type=float, default=0.15)
    ap.add_argument("--max_length", type=int, default=384)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip_fill_mask", action="store_true", help="Skip the qualitative probes and only run the perplexity comparison.")
    args = ap.parse_args()

    if not args.skip_fill_mask:
        run_fill_mask_probes(args.base_model_name, "BASE ModernBERT (before continued pretraining)")
        run_fill_mask_probes(args.heabert_dir, "HEABERT (after continued pretraining)")

    if args.corpus:
        print(f"\n{'=' * 70}\nPERPLEXITY COMPARISON on {args.eval_sample_size} held-out passages from {args.corpus}\n{'=' * 70}")
        texts = []
        with open(args.corpus, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    texts.append(json.loads(line)["text"])
                except (json.JSONDecodeError, KeyError):
                    continue
        rng = random.Random(args.seed)
        rng.shuffle(texts)
        texts = texts[: args.eval_sample_size]
        if not texts:
            print("[warn] no usable 'text' entries found in --corpus -- skipping perplexity comparison.")
            return
        print(f"Using {len(texts)} passages.")

        base_loss, base_ppl = compute_perplexity(args.base_model_name, texts, args.mlm_probability, args.seed, args.max_length)
        heabert_loss, heabert_ppl = compute_perplexity(args.heabert_dir, texts, args.mlm_probability, args.seed, args.max_length)

        print(f"\n  BASE ModernBERT : loss={base_loss:.4f}  perplexity={base_ppl:.2f}")
        print(f"  HEABERT         : loss={heabert_loss:.4f}  perplexity={heabert_ppl:.2f}")
        delta = base_ppl - heabert_ppl
        if delta > 0:
            print(f"\n  HEABERT's perplexity is {delta:.2f} points LOWER than base ModernBERT's on this domain text --")
            print("  consistent with the continued pretraining having helped, at least on this held-out sample.")
        else:
            print(f"\n  HEABERT's perplexity is {-delta:.2f} points HIGHER (or equal) -- worth investigating rather than")
            print("  assuming pretraining helped. Possible causes: too few epochs, too small a corpus, or overfitting")
            print("  to the pretraining split rather than generalizing to this held-out sample.")
    else:
        print("\n(No --corpus passed, so skipping the quantitative perplexity comparison -- fill-mask probes above are qualitative only.)")


if __name__ == "__main__":
    main()
