"""Training / evaluation curves from trainer_state.json log histories.

Sources: --root containing `outputs/...` trees with CHECKPOINTS/*/trainer_state.json
(the trainer-states tarball extracted in-place) — e.g. the merged down-results dir.

Figures:
  fig-sft-loss-curves.png    per protocol: train loss vs epoch, all 45 runs
  fig-sft-eval-curves.png    per protocol: eval MAE vs epoch, best epoch starred
  fig-cpt-loss-curves.png    CPT-side: old full-CPT run + all tuning trials
  sft_curve_summary.csv      per run: best epoch, best eval MAE, steps
"""

import argparse
import csv
import glob
import json
import os
import re

import numpy as np

ARMS = ["B1", "B2", "B3", "L1", "L2"]
ARM_COLORS = {"B1": "#4477aa", "B2": "#ee6677", "B3": "#228833",
              "L1": "#ccbb44", "L2": "#aa3377"}
PROT_ORDER = ["primary-C", "secondary-CT", "exploratory-T"]
ARM_TAG = {"B1": "B1 original", "B2": "B2 old CPT", "B3": "B3 tuned CPT",
           "L1": "L1 original large", "L2": "L2 tuned CPT large"}


def newest_state(run_dir):
    """The most-advanced trainer_state.json under a run directory (max global_step)."""
    cands = glob.glob(os.path.join(run_dir, "**", "trainer_state.json"), recursive=True)
    best, best_step = None, -1
    for c in cands:
        try:
            st = json.load(open(c, encoding="utf-8"))
        except Exception:
            continue
        if st.get("global_step", -1) > best_step:
            best, best_step = st, st.get("global_step", -1)
    return best


def parse_sft_run_name(name):
    """Split a `down-<protocol>-<arm>-s<seed>` run name into (protocol, arm, seed)."""
    m = re.match(r"down-(primary-C|secondary-CT|exploratory-T)-(B\d|L\d)-s(\d+)", name)
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def main():
    """Render the SFT/CPT curve figures and the per-run curve summary CSV."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="dir containing outputs/ (extracted tarball)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outputs = os.path.join(args.root, "outputs")
    run_dirs = [os.path.basename(d) for d in sorted(glob.glob(os.path.join(outputs, "down-*")))
                if os.path.isdir(d)]

    # ---- SFT curves -------------------------------------------------------
    sft = {}  # protocol -> arm -> seed -> state
    for name in run_dirs:
        if name == "down-smoke-B2":
            continue
        parsed = parse_sft_run_name(name)
        if not parsed:
            continue
        st = newest_state(os.path.join(outputs, name))
        if st:
            sft.setdefault(parsed[0], {}).setdefault(parsed[1], {})[int(parsed[2])] = st

    rows = []
    fig, axes = plt.subplots(len(PROT_ORDER), 2, figsize=(13, 4.2 * len(PROT_ORDER)), squeeze=False)
    for i, proto in enumerate(p for p in PROT_ORDER if p in sft):
        ax_tr, ax_ev = axes[i]
        best_info = {}
        for arm in (a for a in ARMS if a in sft[proto]):
            for seed, st in sorted(sft[proto][arm].items()):
                hist = st["log_history"]
                tr = [(h.get("epoch"), h["loss"]) for h in hist if "loss" in h and "epoch" in h]
                ev = [(h.get("epoch"), h.get("eval_mae")) for h in hist if "eval_mae" in h]
                if not tr:
                    continue
                xs, ys = zip(*tr)
                color = ARM_COLORS[arm]
                ax_tr.plot(xs, ys, lw=1.0, alpha=0.8, color=color,
                           label=(ARM_TAG[arm] + f" seed {seed}") if seed == 42 and False else None)
                if ev:
                    ex, ey = zip(*ev)
                    ax_ev.plot(ex, ey, "-o", ms=3, lw=1.0, alpha=0.8, color=color)
                    k = int(np.argmin(ey))
                    best_info.setdefault(arm, []).append((seed, ex[k], ey[k]))
                    ax_ev.plot(ex[k], ey[k], "*", ms=14, color=color, zorder=5)
        # one summary line per arm outside loop for the legend
        handles, labels = [], []
        for arm in (a for a in ARMS if a in sft[proto]):
            if arm in sft[proto]:
                handles.append(plt.Line2D([], [], color=ARM_COLORS[arm], lw=2))
                labels.append(f"{ARM_TAG[arm]} (3 seeds)")
        for ax, title in ((ax_tr, f"{proto}: train loss"), (ax_ev, f"{proto}: eval MAE (★ = early-stop best)")):
            ax.set_title(title)
            ax.set_xlabel("epoch")
            ax.legend(handles, labels, fontsize=8)
            ax.grid(alpha=0.25)
        ax_ev.set_ylabel("eval MAE (MPa)")
        for arm, items in best_info.items():
            for seed, ep, mae in items:
                rows.append([proto, arm, seed, f"{ep:g}", f"{mae:.2f}"])
    fig.suptitle("Downstream fine-tuning curves (3 seeds per arm overlaid)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-sft-curves.png"), dpi=200)
    plt.close(fig)

    with open(os.path.join(args.out, "sft_curve_summary.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["protocol", "arm", "seed", "best_epoch", "best_eval_mae"])
        w.writerows(rows)

    # ---- CPT curves --------------------------------------------------------
    groups = [("base-full-cpt (old ad-hoc CPT)", "base-full-cpt"),
              ("base-tuning trials", "base-tuning"),
              ("large-tuning trials", "large-tuning")]
    fig, axes = plt.subplots(3, 1, figsize=(11, 12), squeeze=False)
    for i, (title, sub) in enumerate(groups):
        ax = axes[i][0]
        base = os.path.join(outputs, sub)
        state_dirs = []
        for dirpath, dirs, _files in os.walk(base):
            if "trainer_state.json" in _files:
                state_dirs.append(dirpath)
        best_by_run = {}
        for sd in state_dirs:
            rel = os.path.relpath(sd, base)
            seg = rel.split(os.sep)
            run_name = "/".join(seg[0:2]) if seg[0] == "runs" and len(seg) > 1 else seg[0]
            st = json.load(open(os.path.join(sd, "trainer_state.json"), encoding="utf-8"))
            gs = st.get("global_step", -1)
            if run_name not in best_by_run or gs > best_by_run[run_name][0]:
                best_by_run[run_name] = (gs, st)
        for run_name, (gs, st) in sorted(best_by_run.items()):
            hist = st["log_history"]
            tr = [(h.get("step"), h["loss"]) for h in hist if "loss" in h]
            ev = [(h.get("step"), h["eval_loss"]) for h in hist if "eval_loss" in h]
            highlight = ("confirm" in run_name.lower()) or ("full" in sub)
            color = "#228833" if highlight else ("#ee6677" if "screen" in run_name else "#4477aa")
            lw = 2.0 if highlight else 0.8
            a = 1.0 if highlight else 0.45
            if tr:
                xs, ys = zip(*tr)
                ax.plot(xs, ys, lw=lw, alpha=a, color=color,
                        label=f"{run_name} (train)" if highlight or len(best_by_run) < 12 else None)
            if ev:
                xs, ys = zip(*ev)
                ax.plot(xs, ys, "--", lw=lw, alpha=a, color=color,
                        label=f"{run_name} (val)" if highlight or len(best_by_run) < 12 else None)
        ax.set_title(title)
        ax.set_xlabel("optimizer step")
        ax.set_ylabel("loss")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
    fig.suptitle("CPT training curves (bold green = confirmed configs; dashed = validation)")
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, "fig-cpt-loss-curves.png"), dpi=200)
    plt.close(fig)
    print("wrote curve figures to", args.out)


if __name__ == "__main__":
    main()
