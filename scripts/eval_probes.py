"""
Evaluate language probes for vanilla ModernBERT-large vs HEA-BERT-synth.

Metrics:
  - cloze (token): top-1 / top-5 fill-mask accuracy
  - cloze_composition: candidate ranking accuracy (lowest NLL wins)
  - mcq: option ranking accuracy (context + option NLL)
  - tf: prefer statement vs negation by NLL

Usage:
  python scripts/eval_probes.py
  python scripts/eval_probes.py --max-per-type 20   # quick
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer, pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
VANILLA = REPO_ROOT / "models" / "modernbert-large"
ADAPTED = REPO_ROOT / "artifacts" / "hea-bert-synth" / "best_or_final"
PROBES = REPO_ROOT / "data" / "probes"
OUT = REPO_ROOT / "artifacts" / "hea-bert-synth" / "probe_eval.json"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def pick_dtype() -> torch.dtype:
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


class ProbeScorer:
    def __init__(self, model_path: Path) -> None:
        self.model_path = Path(model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = pick_dtype()
        print(f"Loading {self.model_path} on {self.device} ({self.dtype})")
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path), local_files_only=True
        )
        self.model = AutoModelForMaskedLM.from_pretrained(
            str(self.model_path),
            dtype=self.dtype,
            local_files_only=True,
        ).to(self.device)
        self.model.eval()
        self.fill = pipeline(
            "fill-mask",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1,
            dtype=self.dtype,
        )

    def close(self) -> None:
        del self.fill
        del self.model
        del self.tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @torch.no_grad()
    def sequence_nll(self, text: str, max_length: int = 256) -> float:
        """Batched MLM pseudo-likelihood (mean NLL over content tokens)."""
        enc = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
        input_ids = enc["input_ids"].to(self.device)
        attn = enc["attention_mask"].to(self.device)
        ids = input_ids[0]
        special = set(self.tokenizer.all_special_ids)
        positions = [
            i
            for i, tok in enumerate(ids.tolist())
            if tok not in special and attn[0, i] == 1
        ]
        if not positions:
            return float("inf")
        # subsample long sequences for speed
        if len(positions) > 48:
            step = math.ceil(len(positions) / 48)
            positions = positions[::step]
        b = len(positions)
        masked = input_ids.repeat(b, 1)
        attn_b = attn.repeat(b, 1)
        for row, pos in enumerate(positions):
            masked[row, pos] = self.tokenizer.mask_token_id
        logits = self.model(input_ids=masked, attention_mask=attn_b).logits
        losses = []
        for row, pos in enumerate(positions):
            logp = torch.log_softmax(logits[row, pos].float(), dim=-1)
            losses.append(-logp[ids[pos]].item())
        return sum(losses) / len(losses)

    def cloze_topk(self, text: str, gold: str, aliases: list[str], top_k: int = 5) -> dict:
        if "[MASK]" not in text:
            text = text.replace("[mask]", "[MASK]")
        try:
            hits = self.fill(text, top_k=top_k)
        except Exception as e:  # noqa: BLE001
            return {"top1": False, "top5": False, "error": str(e)}
        if hits and isinstance(hits[0], list):
            hits = hits[0]
        preds = [h["token_str"].strip().lower() for h in hits]
        aliases_l = {a.lower() for a in aliases} | {gold.lower()}
        # also accept without leading space issues
        def match(pred: str) -> bool:
            p = pred.strip().lower()
            if p in aliases_l:
                return True
            for a in aliases_l:
                if a in p or p in a:
                    return True
            return False

        top1 = match(preds[0]) if preds else False
        top5 = any(match(p) for p in preds)
        return {"top1": top1, "top5": top5, "preds": preds[:5]}

    def rank_candidates(self, template: str, candidates: list[str], gold: str) -> dict:
        scored = []
        for c in candidates:
            sent = template.replace("[MASK]", c)
            nll = self.sequence_nll(sent, max_length=128)
            scored.append((nll, c))
        scored.sort(key=lambda x: x[0])
        pred = scored[0][1]
        return {
            "correct": pred == gold,
            "pred": pred,
            "ranked": [{"nll": n, "text": t} for n, t in scored],
        }

    def mcq(self, context: str, question: str, options: dict[str, str], gold: str) -> dict:
        scored = []
        # keep context short for speed
        ctx = context[:400]
        for letter, opt in options.items():
            sent = f"{ctx} Question: {question} Answer: {opt}"
            nll = self.sequence_nll(sent, max_length=320)
            scored.append((nll, letter))
        scored.sort(key=lambda x: x[0])
        pred = scored[0][1]
        return {
            "correct": pred == gold,
            "pred": pred,
            "ranked": [{"nll": n, "letter": L} for n, L in scored],
        }

    def true_false(self, statement: str, negation: str, gold: str) -> dict:
        nll_t = self.sequence_nll(statement, max_length=128)
        nll_f = self.sequence_nll(negation, max_length=128)
        pred = "true" if nll_t < nll_f else "false"
        return {
            "correct": pred == gold,
            "pred": pred,
            "nll_statement": nll_t,
            "nll_negation": nll_f,
        }


def summarize(results: list[dict]) -> dict:
    by: dict[str, list[bool]] = defaultdict(list)
    cloze_top1, cloze_top5 = [], []
    for r in results:
        t = r["type"]
        if t == "cloze":
            cloze_top1.append(r["top1"])
            cloze_top5.append(r["top5"])
            by["cloze_top1"].append(r["top1"])
            by["cloze_top5"].append(r["top5"])
        else:
            by[t].append(r["correct"])
    out = {}
    for k, vals in by.items():
        out[k] = {
            "n": len(vals),
            "accuracy": sum(vals) / len(vals) if vals else 0.0,
        }
    return out


def eval_model(name: str, path: Path, cloze, mcq, tf, max_per_type: int | None) -> dict:
    scorer = ProbeScorer(path)
    results = []

    cloze_items = cloze if max_per_type is None else cloze[:max_per_type]
    # split types roughly
    if max_per_type is not None:
        token_cloze = [c for c in cloze if c["type"] == "cloze"][:max_per_type]
        comp_cloze = [c for c in cloze if c["type"] == "cloze_composition"][:max_per_type]
        cloze_items = token_cloze + comp_cloze

    print(f"  cloze items: {len(cloze_items)}")
    for i, item in enumerate(cloze_items, 1):
        if item["type"] == "cloze":
            r = scorer.cloze_topk(
                item["text"],
                item["gold"],
                item.get("aliases", [item["gold"]]),
            )
            results.append({"id": item["id"], "type": "cloze", **r})
        else:
            r = scorer.rank_candidates(
                item["text"], item["candidates"], item["gold"]
            )
            results.append({"id": item["id"], "type": "cloze_composition", **r})
        if i % 20 == 0:
            print(f"    cloze {i}/{len(cloze_items)}")

    mcq_items = mcq
    if max_per_type is not None:
        by = defaultdict(list)
        for m in mcq:
            by[m["type"]].append(m)
        mcq_items = []
        for items in by.values():
            mcq_items.extend(items[:max_per_type])
    print(f"  mcq items: {len(mcq_items)}")
    for i, item in enumerate(mcq_items, 1):
        r = scorer.mcq(item["context"], item["question"], item["options"], item["gold"])
        results.append({"id": item["id"], "type": item["type"], **r})
        if i % 20 == 0:
            print(f"    mcq {i}/{len(mcq_items)}")

    tf_items = tf if max_per_type is None else tf[:max_per_type]
    print(f"  tf items: {len(tf_items)}")
    for i, item in enumerate(tf_items, 1):
        r = scorer.true_false(item["statement"], item["negation"], item["gold"])
        results.append({"id": item["id"], "type": item.get("type", "tf"), **r})
        if i % 20 == 0:
            print(f"    tf {i}/{len(tf_items)}")

    summary = summarize(results)
    scorer.close()
    return {"model": name, "path": str(path), "summary": summary, "n_scored": len(results)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--max-per-type", type=int, default=None)
    p.add_argument("--out", type=Path, default=OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cloze = load_jsonl(PROBES / "cloze.jsonl")
    mcq = load_jsonl(PROBES / "mcq.jsonl")
    tf = load_jsonl(PROBES / "tf.jsonl")
    print(f"Probes: cloze={len(cloze)} mcq={len(mcq)} tf={len(tf)}")

    if not VANILLA.exists():
        raise FileNotFoundError(VANILLA)
    if not ADAPTED.exists():
        raise FileNotFoundError(ADAPTED)

    reports = []
    for name, path in [
        ("vanilla_modernbert_large", VANILLA),
        ("hea_bert_synth", ADAPTED),
    ]:
        print("=" * 60)
        print(name)
        reports.append(eval_model(name, path, cloze, mcq, tf, args.max_per_type))
        print(json.dumps(reports[-1]["summary"], indent=2))

    # comparison table
    comparison = {}
    keys = sorted(set(reports[0]["summary"]) | set(reports[1]["summary"]))
    for k in keys:
        a = reports[0]["summary"].get(k, {}).get("accuracy")
        b = reports[1]["summary"].get(k, {}).get("accuracy")
        comparison[k] = {
            "vanilla": a,
            "hea_bert_synth": b,
            "delta": (None if a is None or b is None else b - a),
        }

    payload = {
        "baseline_mlm": {
            "note": "from training run",
            "vanilla_val_loss": 1.1979,
            "adapted_val_loss": 0.6287,
        },
        "models": reports,
        "comparison": comparison,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("=" * 60)
    print("COMPARISON")
    print(json.dumps(comparison, indent=2))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
