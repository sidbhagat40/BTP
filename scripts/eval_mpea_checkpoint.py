"""
Re-evaluate a saved MPEA fine-tuned checkpoint on its composition-held-out eval split.

Produces the same MAE metric set as training:
  HV, UTS, YS, elongation, ..., normalized_avg_well_supported, overall_masked

Usage (from repo root):
  python scripts/eval_mpea_checkpoint.py --run-dir artifacts/mpea-vanilla-large
  python scripts/eval_mpea_checkpoint.py --run-dir artifacts/mpea-hea-synth --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from finetune_modernbert_regression import (  # noqa: E402
    AUX_FEATURE_NAMES,
    COL_FORMULA,
    MPEADataset,
    MultiTaskRegressionModel,
    NUM_AUX_FEATURES,
    TARGET_COLUMNS,
    TARGET_SHORT_NAMES,
    TARGET_WELL_SUPPORTED_MIN_OBS,
    _from_pretrained_kwargs,
    build_dataframe,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, required=True, help="e.g. artifacts/mpea-vanilla-large")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--csv", type=Path, default=REPO / "MPEA_dataset.csv")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional JSON path (default: <run-dir>/eval_metrics_seed_<seed>.json)",
    )
    return p.parse_args()


@torch.no_grad()
def main() -> int:
    args = parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else REPO / args.run_dir
    ckpt = run_dir / "final"
    split_path = run_dir / f"seed_{args.seed}" / f"split_seed_{args.seed}.csv"
    scaling_path = ckpt / "target_scaling.json"
    model_pt = ckpt / "model.pt"

    for p in (ckpt, split_path, scaling_path, model_pt, args.csv):
        if not Path(p).exists():
            raise SystemExit(f"missing required file: {p}")

    scaling = json.loads(scaling_path.read_text(encoding="utf-8"))
    base_model = scaling["base_model_name"]
    target_mean = np.array(scaling["mean"], dtype=np.float32)
    target_std = np.array(scaling["std"], dtype=np.float32)
    aux_mean = np.array(scaling["aux_mean"], dtype=np.float32)
    aux_std = np.array(scaling["aux_std"], dtype=np.float32)

    # Prefer processed text/aux from the split CSV if present; else rebuild.
    split_df = pd.read_csv(split_path)
    eval_df = split_df[split_df["__split__"] == "eval"].copy()
    if "__text__" not in eval_df.columns:
        full = build_dataframe(str(args.csv))
        # align by formula+row order via merge on all original keys is hard;
        # rebuild and re-select by composition key from split
        raise SystemExit(
            f"{split_path} is missing __text__ columns; re-run fine-tune or use a full processed split."
        )

    raw_targets = eval_df[TARGET_COLUMNS].to_numpy(dtype=float)
    mask = (~np.isnan(raw_targets)).astype(np.float32)
    std_targets = np.nan_to_num((raw_targets - target_mean) / target_std, nan=0.0).astype(np.float32)

    aux_cols = [f"__aux_{name}__" for name in AUX_FEATURE_NAMES]
    aux_all = eval_df[aux_cols].to_numpy(dtype=np.float32)
    aux_norm = (aux_all - aux_mean) / aux_std
    # restore known flags + zero unknown condition values (same as training)
    from finetune_modernbert_regression import _N_CONDITIONS

    for k in range(_N_CONDITIONS):
        vidx, kidx = 2 * k, 2 * k + 1
        aux_norm[:, kidx] = aux_all[:, kidx]
        aux_norm[aux_all[:, kidx] == 0, vidx] = 0.0

    tokenizer = AutoTokenizer.from_pretrained(str(ckpt), **_from_pretrained_kwargs(str(ckpt)))
    enc = tokenizer(
        eval_df["__text__"].tolist(),
        truncation=True,
        max_length=args.max_length,
        padding="max_length",
    )
    ds = MPEADataset(enc, std_targets, mask, aux_norm.astype(np.float32))
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = MultiTaskRegressionModel(base_model, num_targets=len(TARGET_SHORT_NAMES))
    state = torch.load(model_pt, map_location="cpu")
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    preds_std = []
    for batch in loader:
        batch = {k: v.to(device) for k, v in batch.items() if k != "labels" and k != "label_mask"}
        # keep labels off device for metrics from stored arrays
        out = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            aux_features=batch["aux_features"],
        )
        preds_std.append(out["logits"].float().cpu().numpy())
    preds_std = np.concatenate(preds_std, axis=0)
    preds_real = preds_std * target_std + target_mean
    labels_real = np.nan_to_num(raw_targets, nan=0.0)

    abs_err = np.abs(preds_real - labels_real) * mask
    total_obs = pd.read_csv(args.csv)[TARGET_COLUMNS].notna().sum().to_numpy()
    well = total_obs >= TARGET_WELL_SUPPORTED_MIN_OBS

    metrics = {}
    normalized = []
    print(f"Eval checkpoint: {ckpt}")
    print(f"Eval rows: {len(eval_df)} (seed {args.seed} held-out compositions)")
    print("Per-target MAE (original units):")
    for j, name in enumerate(TARGET_SHORT_NAMES):
        denom = mask[:, j].sum()
        if denom <= 0:
            continue
        mae = float(abs_err[:, j].sum() / denom)
        metrics[f"eval_mae_{name}"] = mae
        tag = "well-supported" if well[j] else "SPARSE"
        print(f"  {name:28s} {mae:10.3f}   ({tag}, n_obs_dataset={int(total_obs[j])})")
        normalized.append((mae / target_std[j] if target_std[j] > 1e-8 else mae, bool(well[j])))

    if normalized:
        metrics["eval_mae_normalized_avg"] = float(np.mean([n for n, _ in normalized]))
        well_vals = [n for n, w in normalized if w]
        if well_vals:
            metrics["eval_mae_normalized_avg_well_supported"] = float(np.mean(well_vals))
    if mask.sum() > 0:
        metrics["eval_mae_overall_masked"] = float(abs_err.sum() / mask.sum())

    print("---")
    if "eval_mae_normalized_avg_well_supported" in metrics:
        print(
            f"  normalized_avg_well_supported {metrics['eval_mae_normalized_avg_well_supported']:.4f}"
        )
    if "eval_mae_normalized_avg" in metrics:
        print(f"  normalized_avg               {metrics['eval_mae_normalized_avg']:.4f}")
    if "eval_mae_overall_masked" in metrics:
        print(f"  overall_masked               {metrics['eval_mae_overall_masked']:.3f}")

    out = args.out or (run_dir / f"eval_metrics_seed_{args.seed}.json")
    payload = {
        "run_dir": str(run_dir),
        "checkpoint": str(ckpt),
        "seed": args.seed,
        "n_eval_rows": int(len(eval_df)),
        "metrics": metrics,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
