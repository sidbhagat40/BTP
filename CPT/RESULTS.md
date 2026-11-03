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
Details: `RESULTS.md`.

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
