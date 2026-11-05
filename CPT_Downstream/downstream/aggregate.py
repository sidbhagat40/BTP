"""Aggregate downstream fine-tuning results into thesis-ready tables.

Reads the per-run artifacts produced by downstream.finetune_regression
(results.json + test_predictions.json) and emits:

  results_summary.json — per-arm seed mean±SD (MAE/RMSE/R2) for both protocols,
                         plus mean-predictor baselines;
  pairwise_report.json — paired-bootstrap 95% CIs over test rows for the
                         headline arm comparisons.

Pairing: every arm is evaluated on the identical test rows with identical
targets, so per-row error differences are paired. For a comparison of arms A
vs B we take, per seed s, d_s(td) = abs(err_A,s(td)) - abs(err_B,s(td)) for
test row td; the arm-level gap is the mean over seeds; the bootstrap CI
resamples test rows (2000 draws, fixed seed) — the row pairing is exact and
no cross-paper bootstrap needed at this granularity.
"""

import json
import os
from collections import defaultdict

import numpy as np

PAIRS = [
    ("B3", "B1", "tuned CPT vs original base"),
    ("B3", "B2", "tuned CPT vs old ad-hoc CPT (tuning-study value)"),
    ("B2", "B1", "old CPT vs original base (was CPT helping at all)"),
    ("L2", "L1", "tuned CPT large vs original large"),
    ("B3", "L2", "base tuned vs large tuned (capacity)"),
    ("L1", "B1", "original large vs original base (capacity)"),
]
# n_test per protocol (for CI granularity notes in the report)
PROTOCOLS = {"primary-C": "primary-C (n_test=110)",
             "secondary-CT": "secondary-CT (n_test=141)",
             "exploratory-T": "exploratory-T (n_test=31, exploratory/post-hoc)"}
SEEDS = [42, 43, 3704]
BOOT = 2000
RNG_SEED = 42024

METRICS = ("mae", "rmse", "r2")


def load_runs(root):
    runs = defaultdict(dict)  # protocol -> arm -> seed -> results
    preds = defaultdict(dict)  # protocol -> arm -> seed -> per-row arrays
    for dirpath, _dirs, files in os.walk(root):
        if "results.json" not in files:
            continue
        with open(os.path.join(dirpath, "results.json"), encoding="utf-8") as fh:
            res = json.load(fh)
        protocol = "secondary-CT" if "secondary-CT" in dirpath \
            else "exploratory-T" if "exploratory-T" in dirpath \
            else "primary-C"
        # decisive: directory or recorded arm; fall back on output dir parse
        arm, seed = res["arm"], int(res["seed"])
        runs.setdefault(protocol, {}).setdefault(arm, {})[seed] = res
        pred_file = os.path.join(dirpath, "test_predictions.json")
        if os.path.exists(pred_file):
            with open(pred_file, encoding="utf-8") as fh:
                preds.setdefault(protocol, {}).setdefault(arm, {})[seed] = json.load(fh)
    return runs, preds


def fmt_row(res, split):
    m = res["per_split"][split]
    b = res["per_split"][f"baseline_mean_predictor_{split}"]
    return {"mae": m["mae"], "rmse": m["rmse"], "r2": m["r2"], "baseline_mae": b["mae"]}


def seed_stats(protocol_row):
    out = {}
    for key in ("test", "validation"):
        per_seed = [fmt_row(r, key) for r in protocol_row]
        combo = {}
        for metric in METRICS:
            vals = [row[metric] for row in per_seed]
            combo[metric] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1))}
        combo["baseline_mae"] = float(np.mean([row["baseline_mae"] for row in per_seed]))
        out[key] = combo
    return out


def paired_bootstrap(preds, arm_a, arm_b):
    """MAE gap (B-A, positive = A has higher error / B better) over shared test rows.

    Points: seed-mean of per-row mean gap. CI: bootstrap resamples test rows;
    the *same* resampled rows are averaged across seeds, so the CI reflects
    test-set sampling, averaged over the 3 seeds.
    """
    seeds = sorted(set(preds[arm_a]) & set(preds[arm_b]))
    if len(seeds) < 1:
        return None
    gaps = []
    for seed in seeds:
        pa, pb = preds[arm_a][seed], preds[arm_b][seed]
        y = np.asarray(pa["targets"]["test"], dtype=float)
        ya = np.asarray(pa["predictions"]["test"], dtype=float)
        yb = np.asarray(pb["predictions"]["test"], dtype=float)
        if len(y) != len(pa["predictions"]["test"]):
            raise ValueError("targets/predictions length mismatch")
        gaps.append(np.abs(ya - y) - np.abs(yb - y))
    gaps = np.stack(gaps)  # (S, n) — identical test rows across seeds
    n = gaps.shape[1]
    rng = np.random.default_rng(RNG_SEED)
    idx = rng.integers(0, n, size=(BOOT, n))
    combined_draws = gaps[:, idx].mean(axis=1).mean(axis=0)
    return {"seeds": seeds,
            "mae_gap_per_seed_point": [float(g.mean()) for g in gaps],
            "mae_gap_point_seedmean": float(gaps.mean()),
            "mae_gap_ci95_combined": [float(np.percentile(combined_draws, 2.5)),
                                      float(np.percentile(combined_draws, 97.5))],
            "seed_direction_consistent": bool(np.all(
                np.sign([g.mean() for g in gaps]) == np.sign(gaps.mean()))),
            "note": "gap > 0 means the SECOND arm has lower MAE; row-bootstrap CI holds seeds fixed"}


def main():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--root", required=True, help="directory containing the 30 run subdirs")
    ap.add_argument("--protocol-pairs", default=None,
                    help="optional: protocol:label pairs; default both known protocols")
    args = ap.parse_args()
    runs, preds = load_runs(args.root)
    summary, pairwise = {}, {}
    for protocol, label in PROTOCOLS.items():
        if protocol not in runs:
            continue
        summary[protocol] = {}
        for arm in sorted(runs[protocol]):
            stats = seed_stats([runs[protocol][arm][s] for s in SEEDS if s in runs[protocol][arm]])
            summary[protocol][arm] = {"n_seeds": sum(1 for s in SEEDS if s in runs[protocol][arm]),
                                      "stats": stats,
                                      "hyperparams": {k: v for k, v in
                                                      runs[protocol][arm][SEEDS[0]]["hyperparameters"].items()
                                                      if k in ("batch_size", "gradient_accumulation")}}
        pairs_here = [p for p in PAIRS if p[0] in runs[protocol] and p[1] in runs[protocol]]
        for a, b, desc in pairs_here:
            boot = paired_bootstrap(preds[protocol], a, b)
            pairwise[f"{protocol}: {a} vs {b} ({desc})"] = boot
    with open(os.path.join(args.root, "results_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    with open(os.path.join(args.root, "pairwise_report.json"), "w", encoding="utf-8") as fh:
        json.dump(pairwise, fh, indent=2)
    print(json.dumps({"summary_keys": list(summary), "pairwise": list(pairwise)}, indent=2))


if __name__ == "__main__":
    main()
