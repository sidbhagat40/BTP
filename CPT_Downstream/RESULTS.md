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
