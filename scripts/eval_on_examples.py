"""
Evaluate both MPEA fine-tuned models on eval_examples.json.

  - property_based: regression head -> high/low vs dataset_median
  - other categories: fill-mask with fine-tuned encoder + init MLM head

Usage:
  python scripts/eval_on_examples.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer, pipeline

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from finetune_modernbert_regression import (  # noqa: E402
    COL_FORMULA,
    COL_MICROSTRUCTURE,
    COL_N_CONTENT,
    COL_O_CONTENT,
    COL_PHASE_CLASS,
    COL_PROCESSING,
    COL_TEST_TEMP,
    COL_TEST_TYPE,
    MultiTaskRegressionModel,
    _N_CONDITIONS,
    build_aux_features_for_row,
    build_text_for_row,
)

PROP_TO_KEY = {
    "hardness": "HV",
    "yield strength": "YS_MPa",
    "ultimate tensile strength": "UTS_MPa",
    "elongation": "elongation_pct",
}

MODELS = {
    "mpea_vanilla_large": REPO / "artifacts" / "mpea-vanilla-large" / "final",
    "mpea_hea_synth": REPO / "artifacts" / "mpea-hea-synth" / "final",
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_token(s: str) -> str:
    return s.strip().lower().replace("▁", "").replace("ġ", "").strip()


def answer_match(pred: str, gold: str) -> bool:
    p, g = normalize_token(pred), normalize_token(gold)
    if p == g:
        return True
    aliases = {
        "bcc": {"bcc", "body-centered", "body"},
        "fcc": {"fcc", "face-centered", "face"},
        "equal": {"equal", "near-equal", "equiatomic"},
        "higher": {"higher", "greater", "larger", "more"},
        "increase": {"increase", "increases", "increased"},
        "mismatch": {"mismatch", "difference", "misfit"},
        "stronger": {"stronger", "strong", "harder"},
        "tungsten": {"tungsten", "w"},
        "low": {"low", "lower"},
        "high": {"high", "higher"},
    }
    for canon, group in aliases.items():
        if g in group or g == canon:
            if p in group or p == canon or any(a in p for a in group):
                return True
    return g in p or p in g


class CachedRegressor:
    def __init__(self, model_dir: Path, device: str):
        self.model_dir = Path(model_dir)
        self.device = device
        self.scaling = json.loads(
            (self.model_dir / "target_scaling.json").read_text(encoding="utf-8")
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_dir), local_files_only=True
        )
        self.model = MultiTaskRegressionModel(
            self.scaling["base_model_name"],
            num_targets=len(self.scaling["target_names"]),
        )
        state = torch.load(self.model_dir / "model.pt", map_location="cpu", weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(device).eval()

    @torch.no_grad()
    def predict(self, formula: str) -> dict:
        fake_row = pd.Series(
            {
                COL_FORMULA: formula,
                COL_MICROSTRUCTURE: None,
                COL_PROCESSING: None,
                COL_PHASE_CLASS: None,
                COL_TEST_TYPE: None,
                COL_TEST_TEMP: None,
                COL_O_CONTENT: None,
                COL_N_CONTENT: None,
            }
        )
        text = build_text_for_row(fake_row, row_idx=0)
        aux_raw = np.array(build_aux_features_for_row(fake_row), dtype=np.float32)
        aux_mean = np.array(self.scaling["aux_mean"], dtype=np.float32)
        aux_std = np.array(self.scaling["aux_std"], dtype=np.float32)
        aux_norm = (aux_raw - aux_mean) / aux_std
        for k in range(_N_CONDITIONS):
            vidx, kidx = 2 * k, 2 * k + 1
            aux_norm[kidx] = aux_raw[kidx]
            if aux_raw[kidx] == 0:
                aux_norm[vidx] = 0.0

        enc = self.tokenizer(
            [text],
            truncation=True,
            max_length=256,
            padding="max_length",
            return_tensors="pt",
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}
        aux = torch.tensor(np.array([aux_norm]), dtype=torch.float32, device=self.device)
        out = self.model(
            input_ids=enc["input_ids"],
            attention_mask=enc["attention_mask"],
            aux_features=aux,
        )
        preds_std = out["logits"].float().cpu().numpy()[0]
        mean = np.array(self.scaling["mean"])
        std = np.array(self.scaling["std"])
        preds_real = preds_std * std + mean
        return dict(zip(self.scaling["target_names"], preds_real.tolist()))


def build_mlm_from_finetuned(model_dir: Path, device: str):
    scaling = json.loads((model_dir / "target_scaling.json").read_text(encoding="utf-8"))
    base = scaling["base_model_name"]
    local = {"local_files_only": True} if Path(base).is_dir() else {}

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    mlm = AutoModelForMaskedLM.from_pretrained(base, **local)

    state = torch.load(model_dir / "model.pt", map_location="cpu", weights_only=True)
    enc_state = {
        k[len("encoder.") :]: v for k, v in state.items() if k.startswith("encoder.")
    }
    missing, unexpected = mlm.model.load_state_dict(enc_state, strict=False)
    print(
        f"  Loaded fine-tuned encoder into MLM "
        f"(missing={len(missing)} unexpected={len(unexpected)})"
    )

    dtype = (
        torch.bfloat16
        if device == "cuda" and torch.cuda.is_bf16_supported()
        else (torch.float16 if device == "cuda" else torch.float32)
    )
    mlm = mlm.to(device)
    if dtype != torch.float32:
        mlm = mlm.to(dtype)
    mlm.eval()
    fill = pipeline(
        "fill-mask",
        model=mlm,
        tokenizer=tokenizer,
        device=0 if device == "cuda" else -1,
    )
    return fill


def score_property(reg: CachedRegressor, item: dict) -> dict:
    meta = item.get("meta") or {}
    prop = meta.get("property")
    value = meta.get("value")
    median = meta.get("dataset_median")
    formula = item.get("formula")
    gold = normalize_token(item["answer"])
    key = PROP_TO_KEY.get(prop or "")
    if key is None or formula is None or median is None:
        return {"correct": False, "error": "missing property meta", "pred": None}

    preds = reg.predict(formula)
    pred_val = float(preds[key])
    pred_label = "high" if pred_val >= float(median) else "low"
    return {
        "correct": pred_label == gold,
        "pred": pred_label,
        "pred_value": pred_val,
        "true_value": value,
        "median": median,
        "gold": gold,
        "property_key": key,
    }


def score_cloze(fill, item: dict, top_k: int = 5) -> dict:
    text = item["text_with_mask"]
    gold = item["answer"]
    try:
        hits = fill(text, top_k=top_k)
    except Exception as e:  # noqa: BLE001
        return {"correct": False, "pred": None, "error": str(e), "gold": gold}
    if hits and isinstance(hits[0], list):
        hits = hits[0]
    preds = [h.get("token_str", "") for h in hits]
    top1 = preds[0] if preds else ""
    return {
        "correct": answer_match(top1, gold),
        "topk_correct": any(answer_match(p, gold) for p in preds),
        "pred": normalize_token(top1),
        "preds": [normalize_token(p) for p in preds],
        "gold": normalize_token(gold),
    }


def eval_model(name: str, model_dir: Path, examples: list[dict], device: str) -> dict:
    print("=" * 60)
    print(f"Model: {name}")
    print(f"Path:  {model_dir}")

    reg = CachedRegressor(model_dir, device)
    fill = build_mlm_from_finetuned(model_dir, device)

    by_cat: dict[str, list[bool]] = defaultdict(list)
    by_cat_topk: dict[str, list[bool]] = defaultdict(list)
    details = []

    for i, item in enumerate(examples):
        cat = item.get("category", "unknown")
        if cat == "property_based":
            r = score_property(reg, item)
            by_cat[cat].append(bool(r["correct"]))
        else:
            r = score_cloze(fill, item)
            by_cat[cat].append(bool(r["correct"]))
            by_cat_topk[cat].append(bool(r.get("topk_correct", r["correct"])))
        details.append({"id": item.get("id", i), "category": cat, **r})
        if (i + 1) % 25 == 0:
            print(f"  scored {i + 1}/{len(examples)}")

    summary = {}
    for cat, vals in sorted(by_cat.items()):
        summary[cat] = {
            "n": len(vals),
            "accuracy": sum(vals) / len(vals) if vals else 0.0,
        }
        if cat in by_cat_topk and by_cat_topk[cat]:
            summary[cat]["topk5_accuracy"] = sum(by_cat_topk[cat]) / len(
                by_cat_topk[cat]
            )

    all_vals = [d["correct"] for d in details]
    summary["overall"] = {
        "n": len(all_vals),
        "accuracy": sum(all_vals) / len(all_vals) if all_vals else 0.0,
    }

    del reg, fill
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(json.dumps(summary, indent=2))
    return {
        "model": name,
        "path": str(model_dir),
        "summary": summary,
        "details": details,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", type=Path, default=REPO / "eval_examples.json")
    ap.add_argument(
        "--out", type=Path, default=REPO / "artifacts" / "eval_examples_results.json"
    )
    args = ap.parse_args()

    examples = load_jsonl(args.examples)
    print(f"Loaded {len(examples)} examples from {args.examples}")
    cats = defaultdict(int)
    for e in examples:
        cats[e.get("category", "?")] += 1
    print("Categories:", dict(cats))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    reports = []
    for name, path in MODELS.items():
        if not path.exists():
            raise SystemExit(f"missing checkpoint: {path}")
        reports.append(eval_model(name, path, examples, device))

    comparison = {}
    for k in sorted(reports[0]["summary"]):
        a = reports[0]["summary"][k].get("accuracy")
        b = reports[1]["summary"][k].get("accuracy")
        comparison[k] = {
            "vanilla": a,
            "hea_synth": b,
            "delta_hea_minus_vanilla": None if a is None or b is None else b - a,
        }

    payload = {
        "examples": str(args.examples),
        "models": reports,
        "comparison": comparison,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md = REPO / "artifacts" / "eval_examples_results.md"
    lines = [
        "# eval_examples.json results",
        "",
        "MPEA fine-tuned **vanilla ModernBERT-large** vs **HEA-BERT-synth**.",
        "",
        "- `property_based`: regression → high/low vs `dataset_median`",
        "- other categories: fill-mask (fine-tuned encoder + init MLM head)",
        "",
        "| Category | Vanilla | HEA-synth | Δ |",
        "|----------|--------:|----------:|--:|",
    ]
    for k, v in comparison.items():
        lines.append(
            f"| {k} | {v['vanilla']:.3f} | {v['hea_synth']:.3f} | "
            f"{v['delta_hea_minus_vanilla']:+.3f} |"
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("=" * 60)
    print("COMPARISON")
    print(json.dumps(comparison, indent=2))
    print(f"Wrote {args.out}")
    print(f"Wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
