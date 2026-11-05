"""EDA figures for the CPT stage (tuning-screen, sensitivity grid, test reviews).

Reads the frozen summary artifacts under reports/summaries/ (checked into the
repo) and writes PNGs + one flat CSV to --out. No server data needed. For
training-loss/eval curves (trainer_state.json log_history) see
eda/plot_curves.py once the trainer-state tarball is available.

Figures:
  fig-cpt-tuning.png      hyperparameter screen: val loss vs LR and vs mask
  fig-cpt-sensitivity.png MLM loss / masked-token accuracy vs mask probability
                          (original vs tuned-CPT), base and large
  fig-cpt-test-review.png test-set comparisons at p=0.15 / 0.30 for both sizes
                          (+ old-ad-hoc CPT for base at p=0.30)
  fig-cpt-seed-variance.png  tuning-study training-seed variance
  cpt_sensitivity.csv     flat appendix of every comparison
"""

import argparse
import csv
import json
import os

import numpy as np

SUM_BASE = "base"
SUM_LARGE = "large"
MODELS_DIR_DEFAULTS = {
    "base": {"sensitivity": "base-sensitivity-grid",
             "val_review": "base-tuned-validation-review",
             "test_p015": "base-tuned-test-p015",
             "test_p030": "base-tuned-test-p030",
             "oldcpt_p030": "base-oldcpt-test-p030",
             "tuning_results": "base-tuning/results.json",
             "seed_summary": "base-tuning/training_seed_summary.json"},
    "large": {"sensitivity": "large-sensitivity-grid",
              "val_review": "large-tuned-validation-review",
              "test_p015": "large-tuned-test-p015",
              "test_p030": "large-tuned-test-p030",
              "oldcpt_p030": None,
              "tuning_results": "large-tuning/results.json",
              "seed_summary": "large-tuning/training_seed_summary.json"},
}


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def comparisons_by_mask(path):
    if not path or not os.path.exists(path):
        return {}
    d = load(path)
    return {c["masking_probability"]: c for c in d["comparisons"]}


def fig_tuning(ax_l, ax_m, tuning_rows, chosen, size):
    stages = sorted({r["stage"] for r in tuning_rows})
    stage_colors = dict(zip(stages, __import__("matplotlib").pyplot.cm.tab10(np.linspace(0.0, 1.0, len(stages)))))
    mask_colors = {m: c for m, c in zip(sorted({r["training_mlm_probability"] for r in tuning_rows}),
                                        ["#4477aa", "#228833", "#aa3377", "#ccbb44", "#ee6677"])}
    seen = set()
    for r in tuning_rows:
        lab = f"mask {r['training_mlm_probability']:g}"
        x = max(r["learning_rate"], 1e-6)
        y = r["validation_loss"]
        ax_l.plot(x, y, "o", ms=6, alpha=0.8, color=mask_colors[r["training_mlm_probability"]],
                  label=lab if lab not in seen else None)
        seen.add(lab)
    ax_l.plot(chosen["learning_rate"], chosen["validation_loss"], "*", ms=18,
              color="crimson", label="confirmed", zorder=5)
    ax_l.axvline(chosen["learning_rate"], color="crimson", ls="--", lw=1)
    ax_l.set_xscale("log")
    ax_l.set_xlabel("learning rate")
    ax_l.set_ylabel("validation loss")
    ax_l.set_title(f"{size}: validation loss vs LR")
    ax_l.legend(fontsize=7, ncol=1)

    for stage in stages:
        rows = [r for r in tuning_rows if r["stage"] == stage]
        ax_m.plot([r["training_mlm_probability"] for r in rows],
                  [r["validation_loss"] for r in rows], "o", ms=6, alpha=0.8,
                  color=stage_colors[stage], label=stage)
    ax_m.plot(chosen["training_mlm_probability"], chosen["validation_loss"],
              "*", ms=18, color="crimson", zorder=5)
    ax_m.axvline(chosen["training_mlm_probability"], color="crimson", ls="--", lw=1)
    ax_m.set_xlabel("training masking probability")
    ax_m.set_ylabel("validation loss")
    ax_m.set_title(f"{size}: validation loss vs training mask")
    ax_m.legend(fontsize=8)


def fig_sensitivity(ax, comps, title):
    masks = sorted(comps)
    x = np.arange(len(masks))
    series = [("original", "#4477aa"), ("cpt", "#228833")]
    metric_names = [("token_weighted_mlm_loss", "MLM loss"),
                    ("masked_token_accuracy", "masked-token accuracy")]
    series_names = {"original": "original", "cpt": "tuned CPT"}
    for k, (mname, label) in enumerate(metric_names):
        axm = ax[k]
        for sname, color in series:
            mu = [comps[m][sname][mname]["mean"] for m in masks]
            sd = [comps[m][sname][mname]["std_across_mask_seeds"] for m in masks]
            axm.errorbar(x, mu, yerr=sd, marker="o", ms=5, capsize=3,
                         color=color, label=series_names[sname], lw=1.4)
        axm.set_xticks(x)
        axm.set_xticklabels([f"{m:g}" for m in masks])
        axm.set_xlabel("masking probability (evaluation)")
        axm.set_ylabel(label)
        axm.grid(alpha=0.25)
        if k == 0:
            axm.set_title(title)
            axm.legend(fontsize=8)


def fig_test_review(axes, dirs, title):
    """One row per size: bars of token_weighted_mlm_loss for original / cpt
    (+ old CPT) at the two evaluation mask rates."""
    saved_labels = []
    for row, (name, paths) in enumerate(dirs.items()):
        ax = axes[row]
        entries = []
        for label, path in paths:
            c = comparisons_by_mask(path)
            for mask, comp in sorted(c.items()):
                entries.append((mask, label, comp))
        entries.sort()
        labels = [f"p={m:g}" for m, _l, _c in entries]
        xs = np.arange(len(entries))
        for k, (mask, label, comp) in enumerate(entries):
            color = {"original": "#4477aa", "original (old-CPT dir)": "#999999",
                     "tuned CPT": "#228833", "old CPT": "#ee6677"}[label]
            mu = comp["original" if label.startswith("original") else "cpt"]\
                ["token_weighted_mlm_loss"]
            ax.bar(k, mu["mean"], yerr=mu["std_across_mask_seeds"], color=color,
                   capsize=3, width=0.7)
            ax.text(k, mu["mean"] * 1.003, label, ha="center", va="bottom",
                    fontsize=7)
        saved_labels = labels
        ax.set_xticks(xs)
        ax.set_xticklabels(labels)
        ax.set_ylabel("token-weighted MLM loss")
        ax.set_title(name)
    _ = saved_labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summaries", default=os.path.join(os.path.dirname(__file__), "..", "reports", "summaries"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary_root = args.summaries

    # ---- fig 1: tuning screens (one row per model size) -------------------
    chosen = {}
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), squeeze=False)
    for i, size in enumerate(("base", "large")):
        rows = load(os.path.join(summary_root, MODELS_DIR_DEFAULTS[size]["tuning_results"]))
        best = min(rows, key=lambda r: r["validation_loss"])
        chosen[size] = best
        fig_tuning(axes[i][0], axes[i][1], rows, best, size)
    fig.suptitle("CPT hyperparameter screen (crimson star = best trial)", y=0.995)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-cpt-tuning.png"), dpi=200)
    plt.close(fig)

    # ---- fig 2: sensitivity grid (grid + validation review merged) --------
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), squeeze=False)
    all_rows = []
    for i, size in enumerate(("base", "large")):
        cfg = MODELS_DIR_DEFAULTS[size]
        comps = {}
        comps.update(comparisons_by_mask(os.path.join(summary_root, cfg["sensitivity"], "summary.json")))
        for m, c in comparisons_by_mask(os.path.join(summary_root, cfg["val_review"], "summary.json")).items():
            comps.setdefault(m, c)
        fig_sensitivity(axes[i], comps, f"{size}: evaluation-mask sweep on validation")
        for m, c in sorted(comps.items()):
            for sname in ("original", "cpt"):
                for metric in ("token_weighted_mlm_loss", "masked_token_accuracy"):
                    v = c[sname][metric]
                    all_rows.append([size, m, sname, metric, f"{v['mean']:.5f}",
                                     f"{v['std_across_mask_seeds']:.5f}"])
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-cpt-sensitivity.png"), dpi=200)
    plt.close(fig)

    # ---- fig 3: test reviews (grouped bars per size x eval-mask) -----------
    fig, ax = plt.subplots(figsize=(10, 5))
    groups = []  # (group_label, [(series, mean, sd, color), ...])
    for size in ("base", "large"):
        for mask, path in ((0.15, MODELS_DIR_DEFAULTS[size]["test_p015"]),
                           (0.30, MODELS_DIR_DEFAULTS[size]["test_p030"])):
            comps = comparisons_by_mask(os.path.join(summary_root, path, "summary.json"))
            comp = comps[min(comps)]  # only one mask per test dir
            series = []
            o = comp["original"]["token_weighted_mlm_loss"]
            series.append(("original " + size, o["mean"], o["std_across_mask_seeds"], "#4477aa"))
            c = comp["cpt"]["token_weighted_mlm_loss"]
            series.append((f"tuned CPT  ({mask:.0%})" if size == "base" else f"tuned CPT ({mask:.0%})",
                           c["mean"], c["std_across_mask_seeds"], "#228833"))
            if size == "base" and mask == 0.30:
                oc = comparisons_by_mask(os.path.join(summary_root,
                                                     MODELS_DIR_DEFAULTS["base"]["oldcpt_p030"], "summary.json"))
                v = oc[min(oc)]["cpt"]["token_weighted_mlm_loss"]
                # the "cpt" entry of the old-CPT directory IS the old ad-hoc model
                series.append(("old ad-hoc CPT", v["mean"], v["std_across_mask_seeds"], "#ee6677"))
            groups.append((f"{size}  p={mask:g}", series))
    bin_w = 0.27
    xpos = 0.0
    tick_pos, tick_lab = [], []
    for gi, (glabel, series) in enumerate(groups):
        starts = xpos + np.arange(len(series)) * bin_w
        for (label, mu, sd, color), x0 in zip(series, starts):
            ax.bar(x0, mu, yerr=sd, width=bin_w * 0.9, color=color, capsize=3)
            rel = ""
            if label != series[0][0]:
                base_val = series[0][1]
                rel = f"  ({(mu - base_val) / base_val:+.1%})"
            ax.text(x0, mu * 1.01, f"{label}{rel}", ha="center", va="bottom",
                    fontsize=7, rotation=90)
        tick_pos.append(starts.mean())
        tick_lab.append(glabel)
        xpos += len(series) * bin_w + 0.55
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_lab)
    ax.set_ylabel("token-weighted MLM loss (test)")
    ax.set_title("Test-set MLM loss per arm (error bars = across-mask-seed SD; % = vs original)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-cpt-test-review.png"), dpi=200)
    plt.close(fig)

    # ---- fig 4: training-seed variance -------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), squeeze=False)
    for i, size in enumerate(("base", "large")):
        rows = load(os.path.join(summary_root, MODELS_DIR_DEFAULTS[size]["seed_summary"]))
        ax = axes[0][i]
        xs = np.arange(len(rows))
        mu = [r["mean_validation_loss"] for r in rows]
        sd = [r["std_across_training_seeds"] or 0.0 for r in rows]
        labs = [json.dumps({k: v for k, v in r["parameters"].items()
                            if k in ("learning_rate", "training_mlm_probability")})
                .replace("learning_rate", "lr").replace("training_mlm_probability", "m")
                .replace('"', "") for r in rows]
        ax.bar(xs, mu, yerr=sd, capsize=2, color="#4477aa")
        ax.set_xticks(xs)
        ax.set_xticklabels(labs, rotation=45, fontsize=6, ha="right")
        ax.set_ylabel("mean validation loss")
        ax.set_title(f"{size}: training-seed spread")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-cpt-seed-variance.png"), dpi=200)
    plt.close(fig)

    # ---- CSV appendix -------------------------------------------------------
    with open(os.path.join(args.out, "cpt_sensitivity.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["size", "masking_probability", "model", "metric", "mean", "std"])
        w.writerows(all_rows)
    print("wrote CPT figures to", args.out)


if __name__ == "__main__":
    main()
