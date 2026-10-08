"""
Run the Path A vs Path B MPEA regression comparison from the project diagram.

  Path B: vanilla ModernBERT-large  -> MPEA fine-tune
  Path A: hea-bert-synth (synthetic MLM) -> MPEA fine-tune

Same CSV, same hyperparameters; only --model_name differs.

Usage (from repo root):
  python scripts/run_mpea_comparison.py
  python scripts/run_mpea_comparison.py --num-seeds 3
  python scripts/run_mpea_comparison.py --only vanilla
  python scripts/run_mpea_comparison.py --only hea
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "finetune_modernbert_regression.py"
CSV = REPO / "MPEA_dataset.csv"
VANILLA = REPO / "models" / "modernbert-large"
HEA = REPO / "artifacts" / "hea-bert-synth" / "best_or_final"
OUT_VANILLA = REPO / "artifacts" / "mpea-vanilla-large"
OUT_HEA = REPO / "artifacts" / "mpea-hea-synth"


def run(cmd: list[str]) -> None:
    print("\n>>>", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(REPO), check=True)


def build_cmd(model: Path, output: Path, args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--csv",
        str(CSV),
        "--model_name",
        str(model),
        "--output_dir",
        str(output),
        "--num_seeds",
        str(args.num_seeds),
        "--seed",
        str(args.seed),
        "--num_train_epochs",
        str(args.epochs),
        "--per_device_train_batch_size",
        str(args.batch_size),
        "--per_device_eval_batch_size",
        str(args.batch_size),
        "--gradient_accumulation_steps",
        str(args.grad_accum),
        "--learning_rate",
        str(args.lr),
        "--max_length",
        "256",
        "--gradient_checkpointing",
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["vanilla", "hea", "both"], default="both")
    p.add_argument("--num-seeds", type=int, default=1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=float, default=15.0)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-5)
    args = p.parse_args()

    if not SCRIPT.exists():
        raise SystemExit(f"missing {SCRIPT}")
    if not CSV.exists():
        raise SystemExit(f"missing {CSV}")
    if args.only in ("vanilla", "both") and not (VANILLA / "config.json").exists():
        raise SystemExit(f"missing vanilla model at {VANILLA}")
    if args.only in ("hea", "both") and not (HEA / "config.json").exists():
        raise SystemExit(f"missing HEA-BERT-synth at {HEA}")

    if args.only in ("vanilla", "both"):
        run(build_cmd(VANILLA, OUT_VANILLA, args))
    if args.only in ("hea", "both"):
        run(build_cmd(HEA, OUT_HEA, args))

    # Write a short comparison pointer if both summaries exist
    a = OUT_VANILLA / "seeds_summary.json"
    b = OUT_HEA / "seeds_summary.json"
    if a.exists() and b.exists():
        va = json.loads(a.read_text(encoding="utf-8"))
        vb = json.loads(b.read_text(encoding="utf-8"))
        key = "eval_mae_normalized_avg_well_supported"
        comp = {
            "metric": key,
            "vanilla_large": va.get("summary_mean_std", {}).get(key),
            "hea_bert_synth": vb.get("summary_mean_std", {}).get(key),
            "vanilla_dir": str(OUT_VANILLA),
            "hea_dir": str(OUT_HEA),
        }
        out = REPO / "artifacts" / "mpea_comparison_summary.json"
        out.write_text(json.dumps(comp, indent=2), encoding="utf-8")
        print(f"\nWrote {out}")
        print(json.dumps(comp, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
