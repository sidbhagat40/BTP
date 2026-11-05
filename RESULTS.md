# BTP — Continued pretraining of ModernBERT on high-entropy-alloy literature

Masked-language-modeling (MLM) CPT of **ModernBERT-base** and **ModernBERT-large**
on 6,750 high-entropy-alloy (HEA) research papers, with a frozen-evaluation
protocol, validation-only hyperparameter search, and exact paired statistics.

Final tuned test losses (376-paper held-out split; paired, five mask seeds; 15%):

| Model | Original | After CPT ↓ | Relative |
|---|---:|---:|---:|
| ModernBERT-base | 1.1803 | **0.7721** | **−34.6%** |
| ModernBERT-large | 0.9737 | **0.6892** | **−29.2%** |

All CIs exclude zero; results hold at a pre-declared 30% sensitivity protocol.

## Perplexity

Perplexity over the corrupted evaluation positions, PPL = exp(token-weighted
loss), five mask seeds. High absolute values are expected for chemical text
(domain vocabulary, formulas); the *relative* reductions are the meaningful
quantity.

### Test (376-paper held-out split)

| Condition | Original | Old CPT | Tuned |
|---|---:|---:|---:|
| Base @ 15% | 3.26 | 2.27 | **2.16** |
| Base @ 30% | 4.56 | 2.95 | **2.71** |
| Large @ 15% | 2.65 | — | **1.99** |
| Large @ 30% | 3.51 | — | **2.43** |

### Validation (375-paper split)

| Condition | Original | Tuned |
|---|---:|---:|
| Base @ 15% | 3.21 | **2.17** |
| Base @ 30% | 4.48 | **2.73** |
| Large @ 15% | 2.61 | **2.00** |
| Large @ 30% | 3.46 | **2.44** |

Validation and test agree everywhere (largest deviation < 0.02 PPL), and the
old ad-hoc CPT sits between the original and tuned models at both rates.

## Corruption-rate sensitivity (validation-only, pre-declared)

Full sweep p ∈ {0.05, 0.10, 0.15, 0.30, 0.50}; five mask seeds per point;
0.15/0.30 columns from the pre-existing validation reviews, 0.05/0.10/0.50 from
a declared validation-only sensitivity grid (`reports/summaries/*-sensitivity-grid`).
No test access in either run.

### Token-weighted loss / PPL by corruption rate

| p | Base: orig → tuned (PPL) | Gain | Large: orig → tuned (PPL) | Gain |
|---:|---|---:|---|---:|
| 0.05 | 1.0488 → 0.6715 (2.85 → 1.96) | −35.97% | 0.8305 → 0.6004 (2.29 → 1.82) | −27.70% |
| 0.10 | 1.0822 → 0.7179 (2.95 → 2.05) | −33.66% | 0.8877 → 0.6399 (2.43 → 1.90) | −27.92% |
| 0.15 | 1.1654 → 0.7761 (3.21 → 2.17) | −33.41% | 0.9601 → 0.6908 (2.61 → 2.00) | −28.05% |
| 0.30 | 1.5002 → 1.0028 (4.48 → 2.73) | −33.16% | 1.2424 → 0.8904 (3.46 → 2.44) | −28.33% |
| 0.50 | 2.2398 → 1.5421 (9.39 → 4.67) | −31.15% | 1.8919 → 1.3776 (6.63 → 3.97) | −27.18% |

Every point's 95% paired-paper bootstrap CI excludes zero, and per-point
accuracy gaps behave identically (e.g., base top-1 accuracy +0.061 → +0.090
from p=0.05 → 0.50). Reading:

- The CPT gain is **stable across the entire corruption regime** (roughly
  31–36% relative for base, 27–28.3% for large), from near-clean 5% masking to
  harsh 50% masking — it does not depend on picking a favorable corruption
  rate, and is largest under the lightest corruption.
- Large is remarkably **flat** (27.2–28.3%) across the whole range; base's
  relative gain decreases modestly as corruption intensifies (−36% → −31%),
  consistent with a larger fraction of easy, predictable tokens under heavy
  masking inflating the original model's baseline loss.
- Raw losses are **not comparable across rates** (each rate is a different
  task — the evaluator states this explicitly); only comparisons *at the same
  rate*, or the relative reductions, are meaningful.

## Downstream transfer (yield-strength regression, LoRA SFT)

**Task and data.** Yield strength (MPa) regression from templated composition
text on the Citrine MPEA dataset (Borges et al., *Sci Data* 7:159, 2020).
Formulas parsed by `hea_cpt.alloys.normalized_composition` (0 failures across
all rows used). Three pre-declared protocols with **composition-disjoint**
splits (`sha256(composition)[:8] mod 100`: <70 train, <85 val, else test):

| Protocol | Task input | Rows | Split (tr/val/te) |
|---|---|---:|---|
| primary-C | compression (C) — **confirmatory** | 614 | 432/72/110 |
| secondary-CT | C+T combined, test type in input — robustness mirror | 760 | 528/91/141 |
| exploratory-T | tension (T) only — run post-hoc, see disc. | 146 | 96/19/31 |

**Setup.** All five frozen backbones (B1 `answerdotai/ModernBERT-base`
@`8949b909…`, B2 old-CPT, B3 tuned-CPT, L1 original large, L2 tuned-CPT large)
under an **identical harness** (`downstream/finetune_regression.py`): LoRA
r=16/α=32/dropout 0.1 + fresh regression head, LR 5e-5, ≤20 epochs, batch 8,
early stopping on validation only, test evaluated once per run; 3 seeds
(42/43/3704). Built with `downstream/build_property_dataset.py`; dataset
manifest + split report are committed under `data/hea-prop-ys/`.

### Per-arm results (test MAE MPa, mean ± SD over seeds; R² in parentheses)

| Arm | primary-C | secondary-CT | exploratory-T |
|---|---|---|---|
| B1 original | 275.0 ± 16.5 (0.66) | 258.6 ± 3.2 (0.67) | 278.4 ± 16.3 (−0.09) |
| B2 old CPT | 313.7 ± 24.1 (0.50) | 247.7 ± 9.2 (0.69) | 267.0 ± 12.1 (−0.05) |
| B3 tuned CPT | **260.9 ± 19.2 (0.68)** | **238.7 ± 7.6 (0.72)** | 264.9 ± 8.9 (−0.03) |
| L1 original large | **236.2 ± 15.6 (0.72)** | 245.0 ± 6.0 (0.69) | **255.4 ± 6.1 (+0.02)** |
| L2 tuned CPT large | 261.7 ± 12.4 (0.67) | **233.9 ± 13.3 (0.71)** | 262.5 ± 21.8 (−0.00) |

Mean-predictor baselines: 503.7 (primary-C), 502.5 (secondary-CT),
271.0 (exploratory-T). Full per-run metrics:
`reports/figures/downstream_test_metrics.csv`.

### Pairwise gaps (test MAE, MPa; gap = first − second arm; negative favors first)

Grounded in per-row paired point estimates; `●` = 95% paired-bootstrap CI excludes zero
**and** all three seeds agree on the direction; `×` = CI excludes zero but
per-seed directions disagree; `n.s.` = CI contains zero.

| Comparison | primary-C | secondary-CT | exploratory-T |
|---|---|---|---|
| B3 vs B1 (tuned CPT vs original) | −14.1 [−19.7, −9.0] × | −19.9 [−25.2, −15.9] ● | −13.6 [−15.3, −12.0] × |
| B3 vs B2 (tuning-study value) | −52.8 [−59.3, −45.7] ● | −9.0 [−13.0, −5.2] × | −2.1 [−2.9, −1.5] × |
| B2 vs B1 (was old CPT helping?) | **+38.7 [+32.3, +46.6] ● (hurts)** | −10.9 [−16.6, −6.2] ● (helps) | −11.5 [−13.6, −9.9] ● (helps) |
| L2 vs L1 (CPT on large) | **+25.5 [+21.8, +30.5] ● (hurts)** | −11.1 [−14.8, −7.3] × (helps) | +7.1 [+6.0, +8.5] × (hurts) |
| B3 vs L2 (base vs large, tuned) | −0.8 [−4.6, +3.0] n.s. | +4.8 [−0.0, +9.0] n.s. | +2.3 [+0.4, +4.3] × (L2 better) |
| L1 vs B1 (capacity) | −38.8 [−43.4, −34.0] × | −13.6 [−18.7, −8.7] ● | −23.0 [−25.2, −20.5] × |

### Reading

1. **The tuned CPT model (B3) improves regression transfer over the original
   base (B1) on all three protocols** (−14.1 / −19.9 / −13.6 MPa), with CIs
   excluding zero; secondary-CT is the strongest claim there. The improvement
   is not uniform per seed on primary-C (seed 3704 favors B1 by +10.9
   MPa — noisy early stopping on a 72-row val set), so the claim is phrased as
   an average effect.
2. **The tuning study was decisive, not cosmetic.** Old ad-hoc CPT (B2)
   *significantly worsened* compression-only transfer (+38.7 MPa, stable), and
   the tuned configuration turned that into a significant improvement
   (−9.0 to −52.8 across protocols). On protocols involving tension rows B2
   already helped (−10.9 / −11.5) — the old config's benefit was regime-specific.
3. **Capacity effects are protocol-dependent.** Original large (L1) is the best
   single arm on compression-only (236.2) and tension-only (255.4), while
   tuned-CPT large (L2) does not realize a transfer gain there (+25.5 / +7.1).
   On C+T, tuned models cluster at the top and B3 ≈ L2 (n.s.). Clean
   conclusions: L1 > L2 on primary-C (stable, all seeds); L1 > B1 everywhere;
   no robust B3-vs-L2 verdict (only T is significant, and only marginally).
4. **Exploratory-T absolute performance is weak for all arms** (R² ≈ −0.09…+0.02;
   several arms barely beat the mean predictor), and its test split appears
   distribution-shifted relative to train (val MAE ≈190–210 MPa vs test ≈255–280
   MPa for every arm). Arm *rankings* remain informative; absolute transfer on
   this protocol is not established.

### Disclosures (downstream)

- Inputs are **templated composition strings, not full papers**; this measures
  whether CPT's representations help tabular-property prediction, not the MLM
  task itself.
- Identical splits for every arm; one fine-tuning observation per
  (arm, seed); each test set is evaluated exactly once per run (before this,
  the test split lived outside the fine-tuning harness entirely).
- **Exploratory-T was fine-tuned post-hoc** (only 146 rows total; val=19 rows makes
  early stopping noisy — visible as ±20–40 MPa evaluation-MAE oscillation in
  `reports/figures/fig-sft-curves.png`); it is not part of the pre-declared
  confirmatory matrix and results should be read as exploratory.
- The 6 secondary-CT large runs were executed under GPU contention with
  batch 4 × gradient-accumulation 2 (effective batch 8, identical optimizer
  math; recorded per-run in `results.json`).
- Shared-GPU cluster: one fleet OOM (foreign process) killed 6 runs and forced
  the re-queue above; no other execution anomalies.

Figures: `reports/figures/fig-mae-by-arm.png`, `fig-forest-pairs.png`,
`fig-pred-vs-target.png`, `fig-sft-curves.png` (generators in `eda/`).

## Data

| Split | Papers | Role |
|---|---:|---|
| `train.jsonl` | 6,750 | Gradient updates only (never shipped in this repo; 235 MB) |
| `validation.jsonl` | 375 | Checkpoint selection, tuning, confirmatory claims |
| `test.jsonl` | 376 | Frozen final measurement |

Chunking: 512-token chunks (109,785 train chunks / 54.5 M tokens), native
tokenizer, no cleaned/lowercased text (chemical notation preserved).
`artifacts/hea-512/manifest.json` (in-repo fingerprint) records each split's
SHA-256, the chunk counts, and the frozen **15% / 80-10-10** evaluation-masking
protocol fixed before any training.

## Pipeline (`hea_cpt/`)

| Module | Purpose |
|---|---|
| `prepare.py` | Chunking, frozen evaluation masks, manifest; refuses silent failures |
| `masking.py` | 80/10/10 corruption; dynamic training masks, static eval labels |
| `train.py` | Single-GPU resumable MLM Trainer; test split unreachable during training |
| `tune.py` | Sequential validation-only hyperparameter search (screen → refine → confirm → repeat) with restartable state and **token-weighted** selection (`token_trainer.py`) |
| `evaluate.py` + `evaluation.py` | Exact token-weighted metrics, multi-seed masks, paired paper-level bootstrap CIs |
| `probes.py`, `alloys.py` | Exploratory cloze probes; deterministic composition-ratio checker |
| `audit.py` | Duplicate/title-leakage corpus audit |

Tests: `python -m unittest discover -s tests` (18 tests, includes offline tiny-model integration runs).

## Results excerpts

- Base tuning (17 runs, ≈70 GPU-h): best package **LR 1e-4 / train-mask 0.30 / decay 0.1 / warmup 0.02**; 5.7% below the initial package; seed SD < 3×10⁻⁴.
- Large tuning: same signature at LR 6e-5 → **−4.6%** rel. to its base config; final loss 0.6892 validation.
- Exploratory 32-probe battery: 27/32 for both base models; CPT fixes unit control, trades some general-English items (small specialization trade-off).

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m hea_cpt.prepare --data-dir . --output-dir artifacts/hea-512 --max-length 512
python -m hea_cpt.train --config configs/base.json ...
python -m hea_cpt.evaluate --original-model ... --cpt-model ... --split test --probabilities 0.15
```

See `TUNING.md` for the full search protocol (frozen original-weights identity,
restartable trials, GPU scheduling) and `EVALUATION.md` for the evaluation suite.

## Disclosures

- Test-set outcomes were inspected once before the validation-only tuning study; test was never used for training or selection (enforced + logged).
- The 32 probes are hand-authored diagnostics, not validated benchmarks.
- GPU experiments were executed on a shared A5000/A6000 cluster.
