# Rigorous CPT evaluation and varied diagnostic probes

The original base and HEA-CPT base are **frozen checkpoints**. These commands do not train unless explicitly labelled as training ablations below. Copy the updated `hea_cpt/`, `examples/`, and optionally `tests/` folders, plus this file, to the server. No new dependencies beyond `requirements.txt` are needed. Your existing checkpoints and prepared data must remain in place.

All commands below run from the project root, with `hea-cpt` activated. Replace GPU `0` with the GPU **allocated to you**. Run jobs sequentially, not concurrently on an occupied GPU. Use fresh output directories. `--offline` uses cached/local checkpoints and prevents Hub requests. If the original base is not cached, download it on a connected machine and use `--original-model models/ModernBERT-base` instead.

## One-command sequential suite

Copy `run_evaluation.sh` as well if you want the complete evaluation sequence:

```bash
GPU_INDEX=0 nohup bash run_evaluation.sh > evaluation_suite.log 2>&1 &
```

```bash
tail -f evaluation_suite.log
```

This runs a smoke test, full validation, validation-only masking sensitivity, the prespecified test protocol, both hand-authored passage diagnostics, and all 32 probes. It loads the models sequentially, uses batch size 1, and never retrains or automatically selects new model settings. It performs many evaluation passes; budget GPU time accordingly. If the process fails, completed per-stage reports remain available. Run individual remaining commands below into fresh directories rather than overwriting earlier reports.

Defaults: original `answerdotai/ModernBERT-base`, adapted `outputs/base-full-cpt/final`, output `outputs/base-evaluation-suite`. Override with environment variables `ORIGINAL_MODEL`, `CPT_MODEL`, and `EVAL_OUTPUT_DIR`. For example, `ORIGINAL_MODEL=models/ModernBERT-base GPU_INDEX=0 bash run_evaluation.sh` uses a locally downloaded original checkpoint. The Bash launcher is intended for your Linux server; Python evaluation paths were integration-tested offline on tiny local models.

For immutable provenance, the original base commit from your completed run was `8949b909ec900327062f0ebf497f51aef5e6f0c8`. You can add `--original-revision 8949b909ec900327062f0ebf497f51aef5e6f0c8` to evaluation/probe commands. Every run records the resolved commit when available.

## 1. Smoke test the new evaluator

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --split validation --probabilities 0.15 --seeds 42 \
  --max-papers 2 --bootstrap-iterations 100 --offline \
  --output-dir outputs/evaluation-smoke
```

This uses the first two papers, retaining all their chunks. It is a pipeline check, not a representative result or a meaningful population confidence interval. Remove `--max-papers` for the full evaluations below.

## 2. Full validation: five masking seeds

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --split validation --probabilities 0.15 \
  --seeds 42 43 44 45 46 --batch-size 1 --offline \
  --output-dir outputs/base-full-validation-rigorous
```

This reconstructs uncorrupted chunks from `validation.jsonl`, using the saved tokenizer and the same non-overlapping 512-token chunking policy. It verifies that the raw JSONL hash matches your prepared manifest and retains source-paper/line identifiers. No papers are mixed and no final partial chunks are dropped. Seed 42 at 15% reproduces the earlier saved corruption policy.

Both checkpoints receive identical corruption for each seed, verified by a corruption SHA-256 fingerprint. The original is evaluated first and unloaded before the adapted model is loaded, avoiding two simultaneous GPU-resident models.

### Metrics

| Output metric | Definition |
|---|---|
| `token_weighted_mlm_loss` | Sum of labelled-token cross-entropies / number of labelled tokens |
| `masked_token_accuracy` | Top-1 correctness over all selected subword targets |
| `masked_token_top5_accuracy` | Target among five highest-scoring vocabulary tokens |
| `paper_macro_mlm_loss` | Mean of each paper's token-weighted loss; papers receive equal weight |
| `mask_replaced_top1_accuracy` | Top-1 accuracy restricted to selected positions whose input actually became `[MASK]` |

Special tokens and padding are excluded. The 80/10/10 policy includes selected targets that remain unchanged, so the main accuracy must not be confused with accuracy on entirely hidden tokens. At least one target per chunk is retained to avoid undefined loss on tiny final chunks; the realized selection fraction is reported.

Values for accuracy are fractions: multiply by 100 for percent. Loss is in natural-log units (nats). Do not call `exp(loss)` conventional autoregressive perplexity.

The earlier Trainer metric averaged chunk losses (with batch size 1); this evaluator uses exact token weighting. Its loss therefore need not exactly match the earlier 1.19856 / 0.82683 figures, even at the same seed. It is a different aggregation, not evidence of model corruption.

### Uncertainty

- Means and sample standard deviations are reported over masking seeds.
- A paired bootstrap resamples **source papers**, not correlated chunks, 2,000 times. The same paper sample is used for both models and every masking seed.
- Positive `original loss - CPT loss` favors CPT; positive `CPT accuracy - original accuracy` favors CPT.
- Intervals quantify paper-sampling uncertainty conditional on these checkpoints/seeds. They do **not** measure independent CPT-training-seed uncertainty or prove universal scientific reasoning.

### Files to inspect/share

```text
report.md                 Readable metric and confidence-interval tables
summary.json              Aggregate original/CPT comparisons
summary.csv               Spreadsheet-friendly means and standard deviations
evaluation_config.json    Inputs, versions, hashes, precision and model commits
paper_mapping.json        Source JSONL line for each evaluated paper ID
original_p*_seed*.json    Per-run metrics and per-paper sufficient statistics
cpt_p*_seed*.json         Matching adapted-model records
```

## 3. Evaluation-mask sensitivity: validation only

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --split validation --probabilities 0.10 0.15 0.30 \
  --seeds 42 43 44 --batch-size 1 --offline \
  --output-dir outputs/base-validation-mask-sensitivity
```

**This is not training-mask tuning.** It asks whether the benefit of the already-trained CPT checkpoint persists when more or less input is corrupted. Compare original versus CPT **within each masking probability**. Do not select an "optimal" rate by simply picking the smallest loss across different masking probabilities: those are different prediction tasks.

The CLI rejects multi-probability sweeps on `--split test`. Corruption is paired between models within each condition; it is not assumed to be nested or identical across different probabilities. Different conditions have different numbers of supervised targets.

## 4. Full test evaluation: prespecified 15%, five seeds

Freeze the protocol before running:

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --split test --probabilities 0.15 \
  --seeds 42 43 44 45 46 --batch-size 1 --offline \
  --output-dir outputs/base-test-rigorous
```

This covers all 376 test papers and 6,180 chunks. Do not use the results to choose training settings. You have already inspected this test set's earlier results; disclose that history. Any new tuning motivated by test outcomes needs a fresh untouched holdout for confirmatory claims.

## 5. Varied scientific and English examples: compare every probe

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.probes \
  --cpt-model outputs/base-full-cpt/final \
  --offline --output-dir outputs/base-probe-comparison
```

Read **`outputs/base-probe-comparison/comparison.md`**. It contains every probe, expected answer, explanation, each model's full candidate ranking, and unrestricted top-five single-subword predictions. `comparison.json` contains the underlying scores and category counts. Do not cherry-pick only examples CPT wins.

The 32 examples in `examples/evaluation_probes.jsonl` cover:

- Cantor-alloy elements, refractory elements, ideal configurational entropy and the limits of entropy-based phase claims.
- FCC/BCC/HCP, XRD, loading modes, hardness versus strength, unit conversions and composition basis.
- **Same composition:** `CoCrFeMnNi` / `NiMnFeCrCo`; `Fe50Ni50` / `FeNi`; `Al0.5CoCrFeNi` / `AlCo2Cr2Fe2Ni2`.
- **Different composition:** `AlCoCrFeNi` / `Al0.5CoCrFeNi`; replacing Ni with Cu; ternary versus five-element compositions.
- Identical nominal composition does not establish identical processing, phases or properties. Exact yield strength cannot be determined from a formula alone.
- General-English grammar, irregular plurals, synonyms, contextual completion, negation, entailment and string-order controls.

### What "are these alloys the same?" means

The included formula comparisons are explicitly about **normalized atomic ratios**, assuming omitted coefficients equal one. An independent deterministic checker parses simple element/decimal formulas with exact rational arithmetic. It is the composition reference, **not** a result produced by either neural model. It does not handle weight-percent conversion, aliases, parentheses or processing state. Do not interpret it as determining whether two specimens are the same material.

ModernBERT is an encoder MLM, not a chat model. These examples are controlled cloze probes, not open-ended scientific answers. For example:

> As atomic-ratio formulas, Fe50Ni50 and FeNi have the {answer} normalized elemental composition.

Candidates: `same`, `different`. Expected under the stated convention: `same`.

### Candidate scores and limitations

Each candidate is inserted into the complete sentence, tokenized with the native tokenizer, and **all candidate subwords are masked simultaneously**. The mean conditional log probability of the candidate's target subwords is used for ranking. This supports multi-subword words, formulas and numbers without pretending they are single tokens.

This is an exploratory span-MLM preference score, **not** pseudo-log-likelihood with all other answer tokens visible, a normalized candidate posterior, or calibrated scientific confidence. Candidates with different token counts have different mask patterns; mean normalization does not eliminate length effects. The unrestricted one-mask predictions are single subwords and may be fragments, punctuation or unexpected answers. They are not automatically full-word completions. Tied candidate scores are reported and do not count as uniquely correct.

Expected answers/explanations are hand-authored teaching references, not a validated benchmark. Review them with your supervisor. Do not report these small illustrative probes as definitive reasoning or factual-accuracy improvements.

## 6. Materials and general-English passage diagnostics

Two small **hand-authored demo corpora** are included. They are neither unseen external benchmarks nor sufficient evidence of general-language forgetting.

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --input-file examples/materials_demo.jsonl --split diagnostic \
  --probabilities 0.15 --seeds 42 43 44 45 46 --offline \
  --output-dir outputs/base-materials-demo
```

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.evaluate \
  --cpt-model outputs/base-full-cpt/final \
  --input-file examples/general_english_demo.jsonl --split diagnostic \
  --probabilities 0.15 --seeds 42 43 44 45 46 --offline \
  --output-dir outputs/base-english-demo
```

For a real retention evaluation, supply an independent general-English JSONL with one document per `{"text": "..."}` record, documenting source, license, selection method and document count. Run with `--input-file data/general_english_holdout.jsonl --split test --probabilities 0.15`. Use the same original/CPT checkpoints and masking policy. Different domains may have different baseline difficulty: compare model changes within each corpus, not raw cross-domain loss alone. Known overlap with original pretraining may limit "unseen text" claims.

## 7. Optional: ACTUAL training-mask ablations (new CPT runs)

Only do this if you have additional GPU time. Your existing 15% run remains unchanged. The updated `hea_cpt.train` supports **`--train-mlm-probability`**, which changes dynamic **training** corruption only; the saved 15% validation/test masks remain fixed.

For example, start a **new run from the original pretrained base**, not your already-adapted checkpoint:

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.train \
  --config configs/base.json --batch-size 1 --eval-batch-size 1 \
  --gradient-accumulation-steps 32 --train-mlm-probability 0.30 \
  --output-dir outputs/base-full-cpt-trainmask30
```

Optionally repeat with `--train-mlm-probability 0.10` and a different fresh output directory. Keep data, epochs, learning rate, effective batch and training seed constant for the initial controlled comparison. Equal epochs/updates still expose different numbers of supervised masked targets; report that difference. Training rates can also interact with learning rate and budget.

Compare candidate checkpoints on the **same validation evaluation** at 15% and the same masking seeds using `hea_cpt.evaluate`. Select using validation, never test or hand-picked probes. For stronger conclusions, repeat training with multiple independent training seeds. If resuming an ablation, supply the same `--train-mlm-probability` override; changing it during resume is rejected. Existing 15% runs remain resumable without this flag.

Do not change `artifacts/hea-512/manifest.json` or regenerate its validation labels to tune training. That would confound the comparison. These scripts do not auto-start ablation training or choose a rate based on your test results.

## 8. What completes the research evaluation

- Keep an original-versus-CPT downstream fine-tuning comparison with identical labelled splits and tuning budgets; ideally use at least three fine-tuning seeds.
- For unseen-paper downstream claims, exclude downstream validation/test papers from CPT training. Exact text/title checks alone do not prove independence across preprint/publisher versions.
- Use task metrics (MAE/RMSE/R² for regression, macro-F1 for classification, entity-level F1 for extraction), not cloze preference as a substitute.
- Repeat the same protocol for large when an adequately free allocated GPU is available. These CLIs accept a large original checkpoint and a corresponding large CPT checkpoint; they do not require retraining base.

## Verification

```bash
python -m unittest discover -s tests -v
```

Tests exercise exact weighting, composition normalization/rejection, paper grouping, reconstruction of existing masks, multiple masking seeds/probabilities, zero paired differences for identical tiny models, prevention of test sweeps, all probe candidates, offline execution and training-only probability overrides. Local tests use randomly initialized tiny models; actual original/CPT comparisons must be run on your server. No scientific prediction results are fabricated here.
