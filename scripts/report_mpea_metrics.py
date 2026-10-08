"""
Print MPEA regression metrics in the same style as the finetune script summary.

Prefers trustworthy re-eval files (eval_metrics_seed_*.json) when present;
falls back to seeds_summary.json from training.

Usage (from repo root):
  python scripts/report_mpea_metrics.py
  python scripts/report_mpea_metrics.py --dirs artifacts/mpea-vanilla-large artifacts/mpea-hea-synth
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

METRIC_ORDER = [
    "eval_mae_HV",
    "eval_mae_UTS_MPa",
    "eval_mae_YS_MPa",
    "eval_mae_elongation_pct",
    "eval_mae_elongation_plastic_pct",
    "eval_mae_exp_density",
    "eval_mae_exp_youngs_modulus_GPa",
    "eval_mae_grain_size_um",
    "eval_mae_normalized_avg",
    "eval_mae_normalized_avg_well_supported",
    "eval_mae_overall_masked",
]

DEFAULT_DIRS = [
    REPO / "artifacts" / "mpea-vanilla-large",
    REPO / "artifacts" / "mpea-hea-synth",
]


def _as_summary_from_eval(eval_payload: dict, model_name: str) -> dict:
    metrics = eval_payload["metrics"]
    summary = {}
    for k, v in metrics.items():
        if not k.startswith("eval_mae_"):
            continue
        summary[k] = {"mean": float(v), "std": 0.0, "n": 1}
    return {
        "model_name": model_name,
        "seeds": [eval_payload.get("seed", 42)],
        "summary_mean_std": summary,
        "source": "reeval",
        "n_eval_rows": eval_payload.get("n_eval_rows"),
    }


def load_summary(path: Path) -> dict:
    reevals = sorted(path.glob("eval_metrics_seed_*.json"))
    scaling = path / "final" / "target_scaling.json"
    model_name = path.name
    if scaling.exists():
        model_name = json.loads(scaling.read_text(encoding="utf-8")).get(
            "base_model_name", model_name
        )
    if reevals:
        payload = json.loads(reevals[-1].read_text(encoding="utf-8"))
        return _as_summary_from_eval(payload, model_name)

    summary_path = path / "seeds_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"missing metrics in {path}. Run: "
            f"python scripts/eval_mpea_checkpoint.py --run-dir {path}"
        )
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    data["source"] = "training_seeds_summary"
    return data


def fmt_row(label: str, mean: float, std: float, n: int) -> str:
    return f"  {label:32s} {mean:10.3f} +/- {std:.3f}  (n={n})"


def print_block(data: dict) -> list[str]:
    src = data.get("source", "unknown")
    lines = [
        f"Summary across {len(data['seeds'])} seed(s) for {data['model_name']}",
        f"(source: {src})",
        "=" * 70,
    ]
    stats = data.get("summary_mean_std", {})
    for key in METRIC_ORDER:
        if key not in stats:
            continue
        s = stats[key]
        label = key.replace("eval_mae_", "")
        lines.append(fmt_row(label, s["mean"], s["std"], s["n"]))
    for key in sorted(stats):
        if key.startswith("eval_mae_") and key not in METRIC_ORDER:
            s = stats[key]
            label = key.replace("eval_mae_", "")
            lines.append(fmt_row(label, s["mean"], s["std"], s["n"]))
    lines.append("")
    print("\n".join(lines))
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", type=Path, default=DEFAULT_DIRS)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "artifacts" / "mpea_metrics_comparison.md",
    )
    args = ap.parse_args()

    loaded = []
    for d in args.dirs:
        d = d if d.is_absolute() else REPO / d
        loaded.append((d, load_summary(d)))

    all_lines: list[str] = [
        "# MPEA fine-tune metrics comparison",
        "",
        "Same MAE metric set as `finetune_modernbert_regression.py`.",
        "",
        "Uses `eval_metrics_seed_*.json` from `scripts/eval_mpea_checkpoint.py` when present",
        "(correct held-out numbers for saved checkpoints).",
        "",
    ]

    comparison: dict = {"models": []}
    for d, data in loaded:
        block = print_block(data)
        all_lines.append(f"## {d.name}")
        all_lines.append("")
        all_lines.append(f"Init checkpoint: `{data['model_name']}`")
        all_lines.append(f"Metric source: `{data.get('source')}`")
        all_lines.append("")
        all_lines.append("```")
        all_lines.extend(block)
        all_lines.append("```")
        all_lines.append("")
        comparison["models"].append(
            {
                "dir": str(d),
                "model_name": data["model_name"],
                "seeds": data["seeds"],
                "source": data.get("source"),
                "summary_mean_std": data["summary_mean_std"],
            }
        )

    if len(loaded) == 2:
        (_, a), (_, b) = loaded
        sa, sb = a["summary_mean_std"], b["summary_mean_std"]
        all_lines.append("## Side-by-side (mean MAE)")
        all_lines.append("")
        all_lines.append("| Metric | A (vanilla) | B (HEA-synth) | Δ (B−A) |")
        all_lines.append("|--------|--:|--:|--:|")
        deltas = {}
        for key in METRIC_ORDER:
            if key not in sa or key not in sb:
                continue
            ma, mb = sa[key]["mean"], sb[key]["mean"]
            label = key.replace("eval_mae_", "")
            delta = mb - ma
            deltas[label] = {"a": ma, "b": mb, "delta_b_minus_a": delta}
            all_lines.append(f"| {label} | {ma:.4g} | {mb:.4g} | {delta:+.4g} |")
        all_lines.append("")
        all_lines.append(
            "Negative Δ ⇒ B better. For 5-seed mean±std like the base screenshot, "
            "re-run `python scripts/run_mpea_comparison.py --num-seeds 5` "
            "(metric packing bug is fixed for future training runs)."
        )
        comparison["side_by_side"] = deltas

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    json_out = args.out.with_suffix(".json")
    json_out.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Wrote {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
