"""EDA figures for the downstream yield-strength fine-tuning (SFT) results.

Inputs: the per-run artifacts produced by downstream.finetune_regression
(arranged as <root>/<run-dir>/{results.json,test_predictions.json}) plus the
aggregate outputs written by downstream/aggregate.py in the same root.

Outputs (--out dir):
  fig-mae-by-arm.png       grouped bars: test MAE per arm x protocol, seed dots
  fig-r2-by-arm.png        grouped bars: test R2 per arm x protocol, seed dots
  fig-forest-pairs.png     forest plot: 95% CIs for the pairwise MAE gaps
  fig-pred-vs-target.png   test predictions vs targets grid (protocol x arm)
  fig-abscorr-hist.png     |abs error| distributions per arm, per protocol
  downstream_test_metrics.csv  flat CSV of every run's test metrics (appendix)

All figures use seed-stream data as light dots where applicable; bars are
seed means. Gap sign convention (forest plot): gap = MAE(A) - MAE(B), so a
point left of zero favors the FIRST arm of "A vs B".
"""

import argparse
import json
import os

import numpy as np

ARMS = ["B1", "B2", "B3", "L1", "L2"]
ARM_COLORS = {"B1": "#4477aa", "B2": "#ee6677", "B3": "#228833",
              "L1": "#ccbb44", "L2": "#aa3377"}
PROT_ORDER = ["primary-C", "secondary-CT", "exploratory-T"]
PROT_N = {"primary-C": 110, "secondary-CT": 141, "exploratory-T": 31}


def load_runs(root):
    runs = []
    for dirpath, _dirs, files in os.walk(root):
        if "results.json" not in files:
            continue
        with open(os.path.join(dirpath, "results.json"), encoding="utf-8") as fh:
            res = json.load(fh)
        protocol = "secondary-CT" if "secondary-CT" in dirpath \
            else "exploratory-T" if "exploratory-T" in dirpath else "primary-C"
        pred = {}
        pred_file = os.path.join(dirpath, "test_predictions.json")
        if os.path.exists(pred_file):
            with open(pred_file, encoding="utf-8") as fh:
                pred = json.load(fh)
        runs.append({"protocol": protocol, "arm": res["arm"], "seed": res["seed"],
                     "res": res, "pred": pred})
    return runs


def fig_mae(ax, runs, metric, ylabel, baseline_key=None):
    protocols = [p for p in PROT_ORDER if any(r["protocol"] == p for r in runs)]
    width = 0.15
    xs = np.arange(len(protocols))
    for i, arm in enumerate(ARMS):
        means, sds, seeds_all = [], [], []
        for p in protocols:
            vals = [r["res"]["per_split"]["test"][metric] for r in runs
                    if r["arm"] == arm and r["protocol"] == p]
            seeds_all.append(vals)
            means.append(np.mean(vals) if vals else np.nan)
            sds.append(np.std(vals, ddof=1) if len(vals) > 1 else 0.0)
        pos = xs + (i - 2) * width
        ax.bar(pos, means, width * 0.92, yerr=sds, capsize=2,
               color=ARM_COLORS[arm], label=arm, zorder=2)
        rng = np.random.default_rng(7)
        for x0, vals in zip(pos, seeds_all):
            ax.scatter(rng.uniform(x0 - width * 0.25, x0 + width * 0.25, len(vals)),
                       vals, s=9, color="k", alpha=0.45, zorder=3)
    if baseline_key:
        for x0, p in zip(xs, protocols):
            base = np.mean([r["res"]["per_split"][baseline_key]["mae"] for r in runs
                            if r["protocol"] == p and r["arm"] == "B1"])
            ax.hlines(base, x0 - 0.45, x0 + 0.45, colors="crimson",
                      linestyles="--", lw=1.2, zorder=1)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{p}\nn_test={PROT_N[p]}" for p in protocols])
    ax.set_ylabel(ylabel)
    ax.set_title(f"Test {ylabel} by arm and protocol "
                 f"(bars = seed mean ± SD, dots = seeds, dashed = mean-predictor)",
                 pad=14)
    ax.legend(ncol=5, fontsize=8, loc="upper right")


def fig_forest(ax, pairwise):
    protocols = [p for p in PROT_ORDER
                 if any(k.startswith(p + ":") for k in pairwise)]
    nprot = len(protocols)
    for col, p in enumerate(protocols):
        keys = [k for k in pairwise if k.startswith(p + ":")]
        keys.sort()
        for row, key in enumerate(keys):
            v = pairwise[key]
            g = v["mae_gap_point_seedmean"]
            lo, hi = v["mae_gap_ci95_combined"]
            y = col * 12 + row  # vertical band per protocol
            marker = "o" if v.get("seed_direction_consistent") else "x"
            color = "#228833" if lo * hi > 0 else "#999999"
            ax.errorbar(g, y, xerr=[[g - lo], [hi - g]], fmt=marker,
                        ms=7, mfc=color, mec=color, ecolor=color,
                        capsize=3, lw=1.4)
        ax.axvline(0, color="k", lw=0.8)
        # label each protocol band on the right margin
        ax.text(1.01, col * 12 + 2.5, p, transform=ax.get_yaxis_transform(),
                rotation=90, va="center", ha="left", fontsize=9,
                color="#555555", fontweight="bold")
    ax.axvline(0, color="k", lw=0.8)
    labels = sorted(k.split(": ", 1)[1].split(" (")[0] for k in
                    pairwise if k.startswith(protocols[0] + ":"))
    ax.set_yticks([c * 12 + r for c in range(nprot) for r in range(len(labels))])
    ax.set_yticklabels(labels * nprot, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("MAE gap (MPa): first arm − second arm\n"
                  "← favors first arm     0     favors second arm →")
    ax.set_title("Pairwise test-MAE gaps: bootstrap 95% CI (o = all seeds agree on sign, x = not)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    globals()["plt"] = plt

    runs = load_runs(args.root)
    summary = json.load(open(os.path.join(args.root, "results_summary.json"), encoding="utf-8"))
    pairwise = json.load(open(os.path.join(args.root, "pairwise_report.json"), encoding="utf-8"))

    # ---- fig 1: MAE bars -------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    fig_mae(ax, runs, "mae", "MAE (MPa)", "baseline_mean_predictor_test")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-mae-by-arm.png"), dpi=200)
    plt.close(fig)

    # ---- fig 2: R2 bars --------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    fig_mae(ax, runs, "r2", "R² (test)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-r2-by-arm.png"), dpi=200)
    plt.close(fig)

    # ---- fig 3: forest ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 6))
    fig_forest(ax, pairwise)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-forest-pairs.png"), dpi=200)
    plt.close(fig)

    # ---- fig 4: prediction vs target grid --------------------------------
    protocols = [p for p in PROT_ORDER if any(r["protocol"] == p for r in runs)]
    arms_here = [a for a in ARMS if any(r["arm"] == a for r in runs)]
    fig, axes = plt.subplots(len(protocols), len(arms_here),
                             figsize=(2.4 * len(arms_here), 2.4 * len(protocols)),
                             sharex="col", squeeze=False)
    lims_cache = {}
    for p in protocols:
        ys = np.concatenate([r["pred"]["targets"]["test"] for r in runs
                             if r["protocol"] == p and r["pred"]])
        lims_cache[p] = (ys.min() - 100, ys.max() + 100)
    for i, p in enumerate(protocols):
        for j, arm in enumerate(arms_here):
            ax = axes[i][j]
            rs = [r for r in runs if r["arm"] == arm and r["protocol"] == p and r["pred"]]
            for r in rs:
                y = np.asarray(r["pred"]["targets"]["test"])
                yhat = np.asarray(r["pred"]["predictions"]["test"])
                ax.scatter(y, yhat, s=8, alpha=0.5,
                           color=ARM_COLORS[arm], edgecolors="none")
            lo, hi = lims_cache[p]
            ax.plot([lo, hi], [lo, hi], "k--", lw=0.8)
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
            if rs:
                mae = np.mean([r["res"]["per_split"]["test"]["mae"] for r in rs])
                r2 = np.mean([r["res"]["per_split"]["test"]["r2"] for r in rs])
                ax.set_title(f"{arm}  MAE {mae:.0f}  R² {r2:.2f}", fontsize=8)
            if i == len(protocols) - 1:
                ax.set_xlabel("target (MPa)", fontsize=8)
            if j == 0:
                ax.set_ylabel(f"{p}\npred (MPa)", fontsize=8)
    fig.suptitle("Test predictions vs targets, colored by arm (all seeds overlaid)",
                 y=1.0)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-pred-vs-target.png"), dpi=200)
    plt.close(fig)

    # ---- fig 5: abs-correlation-adjacent histogram of |error| -------------
    fig, axes = plt.subplots(1, len(protocols), figsize=(4.2 * len(protocols), 4.4),
                             squeeze=False)
    for i, p in enumerate(protocols):
        ax = axes[0][i]
        for arm in arms_here:
            errs = []
            for r in runs:
                if r["arm"] == arm and r["protocol"] == p and r["pred"]:
                    e = np.abs(np.asarray(r["pred"]["predictions"]["test"]) -
                               np.asarray(r["pred"]["targets"]["test"]))
                    errs.append(e)
            if errs:
                ax.hist(np.concatenate(errs), bins=25, histtype="step", lw=1.5,
                        color=ARM_COLORS[arm], label=f"{arm} (mean {np.concatenate(errs).mean():.0f})",
                        density=True)
        ax.set_title(f"{p} (test n={PROT_N[p]})", fontsize=9)
        ax.set_xlabel("|error| (MPa)")
        ax.set_ylabel("density")
        ax.legend(fontsize=7)
    fig.suptitle("Absolute test-error distributions per arm (seeds pooled)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-abserror-hist.png"), dpi=200)
    plt.close(fig)

    # ---- CSV: flat per-run test metrics -----------------------------------
    import csv
    with open(os.path.join(args.out, "downstream_test_metrics.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["protocol", "arm", "seed", "mae", "rmse", "r2",
                    "baseline_mae", "batch_size", "gradient_accumulation"])
        for r in sorted(runs, key=lambda r: (PROT_ORDER.index(r["protocol"]),
                                             ARMS.index(r["arm"]), r["seed"])):
            t = r["res"]["per_split"]["test"]
            hp = r["res"].get("hyperparameters", {})
            w.writerow([r["protocol"], r["arm"], r["seed"],
                        f"{t['mae']:.2f}", f"{t['rmse']:.2f}", f"{t['r2']:.4f}",
                        f"{r['res']['per_split']['baseline_mean_predictor_test']['mae']:.2f}",
                        hp.get("batch_size", ""), hp.get("gradient_accumulation", "")])
    print("wrote figures to", args.out)


if __name__ == "__main__":
    main()
