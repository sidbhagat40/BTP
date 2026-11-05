# HEA ModernBERT: continued pretraining (CPT)

**Extended evaluation:** see [`EVALUATION.md`](EVALUATION.md) for exact token-weighted metrics, paper-level confidence intervals, masking sensitivity/training ablations, 32 varied scientific/English probes, and general-language diagnostics.

**Hyperparameter tuning:** see [`TUNING.md`](TUNING.md) for a resumable, validation-only search over learning rate, training masking, weight decay and warmup, followed by full-length confirmation and optional training-seed repetitions.

Continue **`answerdotai/ModernBERT-base` and `answerdotai/ModernBERT-large` independently** on high-entropy-alloy literature using **masked-language modeling (MLM)**. This stage needs raw text, not task labels. Supervised fine-tuning comes later; no causal-LM or instruction-tuning objective is used here.

## Your corpus

| Split | Papers | Purpose |
|---|---:|---|
| `train.jsonl` | 6,750 | Parameter updates |
| `validation.jsonl` | 375 | Before/after comparison and checkpoint selection |
| `test.jsonl` | 376 | Final, held-out evaluation only |

Each JSONL record is `{"text": "Title: ...\n\nAbstract: ..."}`. The initial inspection found no exact document duplicates or matching titles across splits. Re-run the audit when data changes. Original JSONL files and `LLM_PAPERS/` are never modified.

The initial 512-token preparation is complete in `artifacts/hea-512/`:

| Split | Chunks | Tokens, including special tokens |
|---|---:|---:|
| Train | 109,785 | 54,490,132 |
| Validation | 6,319 | 3,139,414 |
| Test | 6,180 | 3,068,086 |

The saved data was reloaded and checked with the real tokenizer and a tiny randomly initialized ModernBERT. See `reports/preparation_check.json`. This is a data/pipeline check, **not** completed base/large CPT or a model-quality result.

## 1. Set up the SSH GPU server

Copy this project (code, configs and the three JSONL files) to your server. The local `.venv/` is **not** portable; create a new environment on the server. Python 3.10–3.12 is recommended.

```bash
nvidia-smi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install CUDA-enabled PyTorch appropriate for the server's GPU and NVIDIA driver. One example for a **CUDA 12.6-compatible driver/GPU** is:

```bash
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126
python -m pip install -r requirements.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Use the [PyTorch installation selector](https://pytorch.org/get-started/locally/) if your driver/hardware needs a different wheel. Installing the Python dependencies alone does not guarantee a working CUDA installation. The Hugging Face checkpoints are downloaded on the server's first run; allow disk space for the HF cache, prepared data, models and optimizer checkpoints (several GB per model).

## 2. Audit and prepare the corpus once

If you copy the existing **`artifacts/hea-512/`** directory to the server along with the code, skip preparation and use it directly. The saved Arrow datasets are portable between this Windows machine and the Linux server. `build_cache/` inside that directory is only a preparation cache and does not need to be copied; keep `dataset/`, `tokenizer/`, `manifest.json` and `audit.json`.

Otherwise, run these commands from the project root for a fresh preparation:

```bash
python -m hea_cpt.audit --data-dir . --output reports/corpus_audit.json
python -m hea_cpt.prepare --data-dir . --output-dir artifacts/hea-512 --max-length 512
```

Preparation:

- Checks malformed/empty records, normalized exact duplicates and titles crossing splits. Stops on problems instead of silently changing splits.
- Keeps chemical formulas, case, symbols and units. Does **not** lowercase or aggressively clean scientific text.
- Uses the original ModernBERT tokenizer. All paper text is emitted as non-overlapping chunks with native special tokens; the last short chunk is retained. Chunks never cross paper or split boundaries.
- Uses 15% token selection and 80% `[MASK]` / 10% random-token / 10% unchanged corruption. At least one text token is selected in each chunk to prevent undefined loss for tiny remainders.
- Saves **fixed validation/test masks**. Both models and all checkpoints see the same evaluation corruption. Training masks are sampled dynamically.
- Records source SHA-256 hashes, token counts, tokenizer identity and dependency versions in `manifest.json`.

Base and large share the official tokenizer, so use the same prepared data for both. The training command checks vocabulary and special-token compatibility. To change sequence length, masking rate or masking seed, prepare a **new** directory; existing artifacts are never overwritten.

For immutable Hub downloads, set `--revision <tokenizer-commit-SHA>` during preparation and set each model config's `revision` to its respective model commit SHA. Otherwise `main` is used; run metadata records the resolved model commit when available.

## 3. Smoke test on the server

Select the GPU index reported by `nvidia-smi` (index `0` below is only an example):

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/base.json --max-steps 2 --max-train-samples 32 --max-eval-samples 16 --output-dir outputs/smoke-base
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/large.json --max-steps 2 --max-train-samples 32 --max-eval-samples 16 --output-dir outputs/smoke-large
```

A smoke test verifies execution, not model quality. Its final weights are the last weights if no scheduled checkpoint was reached.

## 4. Train base, then large

On your **48 GB GPU**, run the two jobs sequentially:

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/base.json
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/large.json
```

Use `tmux` or your server's job scheduler so training survives an SSH disconnect. Do not launch both jobs on the same GPU together. This pipeline deliberately uses one GPU per job; it does not combine a 48 GB and a 24 GB GPU.

| Setting | Base | Large |
|---|---:|---:|
| Initial sequence length | 512 | 512 |
| Microbatch | 4 | 2 |
| Gradient accumulation | 8 | 16 |
| Effective sequences/update | 32 | 32 |
| Learning rate | 5e-5 | 3e-5 |
| Maximum epochs | 3 | 3 |
| Warmup | 6% | 6% |
| Weight decay | 0.01 | 0.01 |

These are starting hyperparameters, not a guarantee of optimal results or memory fit. Use the smoke tests to measure actual memory. Precision automatically selects bf16 when supported, otherwise fp16; model parameters/optimizer state remain full precision. Gradient checkpointing, sparse MLM prediction and PyTorch SDPA are enabled. FlashAttention and `torch.compile` are not required.

For the **24 GB GPU**, start with a smaller microbatch while preserving effective batch size:

```bash
CUDA_VISIBLE_DEVICES=1 python -m hea_cpt.train --config configs/base.json --batch-size 2 --eval-batch-size 2 --gradient-accumulation-steps 16 --output-dir outputs/base-24gb
CUDA_VISIBLE_DEVICES=1 python -m hea_cpt.train --config configs/large.json --batch-size 1 --eval-batch-size 1 --gradient-accumulation-steps 32 --output-dir outputs/large-24gb
```

The large model's fit still depends on the actual GPU/software stack. If an OOM occurs, lower **both** train/eval microbatches. Do not start with the full 8192-token context: it is much more expensive. A later long-context experiment can use separately prepared 1024/2048-token data and smaller batches.

### Checkpointing and resume

Every 500 optimizer updates, the script evaluates a fixed, seeded subset of up to 1,024 validation chunks and saves a checkpoint. Set `validation_max_samples` to `null` in the config for full validation during training. The lowest validation-loss checkpoint is reloaded before exporting `final/`; the test set never influences this decision.

Resume an interrupted run with its original config, overrides and sample limits:

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/base.json --resume-from-checkpoint latest
```

Or supply a specific `outputs/.../checkpoint-N` path. Resume restores Trainer model, optimizer, scheduler, step and RNG state. Use the same software/hardware for the closest reproducibility; GPU kernels can still be nondeterministic. `--max-steps` is a testing override, not a way to reproduce an uninterrupted schedule by extending an already completed run.

## 5. Evaluate and keep the CPT checkpoints for fine-tuning

Each training directory contains:

- `baseline_validation_results.json`: original model on the fixed validation subset.
- `cpt_validation_results.json`: selected CPT model on the same subset.
- `checkpoint-*/`: resumable training state.
- `final/`: model and tokenizer to initialize downstream fine-tuning.
- `run_config.json`, `selection.json`, `trainer_state.json`: provenance and learning curves.

Lower MLM validation loss is better, but does not prove better downstream predictions. Report this as **masked-token MLM loss**, not autoregressive perplexity. Trainer averages per-batch mean losses with example weighting; it is not an exact corpus-wide, token-weighted likelihood.

After choosing settings using **validation only**, compare the original and adapted models on the **full test set**. Evaluation-only mode defaults to the full requested split, ignoring the training validation-subset limit:

```bash
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/base.json --eval-only --eval-split test --output-dir outputs/base-original-test
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/base.json --eval-only --eval-split test --model-path outputs/modernbert-base-hea-cpt/final --output-dir outputs/base-cpt-test
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/large.json --eval-only --eval-split test --output-dir outputs/large-original-test
CUDA_VISIBLE_DEVICES=0 python -m hea_cpt.train --config configs/large.json --eval-only --eval-split test --model-path outputs/modernbert-large-hea-cpt/final --output-dir outputs/large-cpt-test
```

Use `--eval-split validation` for a full validation comparison instead. An evaluation requires a fresh output directory to avoid overwriting results. Do not repeatedly tune against test results.

### Research cautions

- Exact-text/title checks are not a near-duplicate detector. Inspect preprint/publisher versions and shared content; group related documents before splitting if necessary.
- Before subsequent supervised fine-tuning, exclude papers belonging to the downstream validation/test sets from CPT training as well, if the intended evaluation requires unseen papers. Existing CPT splits alone cannot establish downstream independence.
- Inspect text extraction quality, references, boilerplate and non-HEA papers before spending GPU time. The audit is a structural/leakage check, not a scientific relevance assessment.
- Keep an original-model, no-CPT downstream baseline for **each** model size, with the same labels, data splits and fine-tuning protocol. That comparison establishes the benefit of CPT. A general-domain held-out set can additionally measure forgetting.
- Check literature licensing/data-use permissions; do not publish full-text papers without appropriate rights.

## Downstream fine-tuning (yield-strength SFT)

The CPT checkpoints are compared on a supervised task: yield strength (MPa)
regression from templated composition text, Citrine MPEA dataset (Borges et
al., *Sci Data* 2020), LoRA (r=16, α=32) + regression head under an identical
harness for all arms.

```bash
# 1. Build the composition-disjoint dataset (deterministic; manifest + split_report frozen)
python -m downstream.build_property_dataset --csv <MPEA_dataset.csv> --output-dir data/hea-prop-ys

# 2. Fine-tune one arm/seed/protocol (see RESULTS.md for the full 45-run matrix)
python -m downstream.finetune_regression --model-path <arm checkpoint or hub id> \
  --arm <B1|B2|B3|L1|L2> --seed 42 --data-dir data/hea-prop-ys --role-prefix primary-C \
  --output-dir outputs/down-primary-C-<ARM>-s42

# 3. Aggregate seed means / paired-bootstrap CIs, then plot
python -m downstream.aggregate --root outputs
python -m eda.plot_downstream_eda --root outputs --out reports/figures
```

Protocols, per-arm numbers, pairwise CIs with seed-stability flags, and all
disclosures: **`RESULTS.md` → "Downstream transfer"**. Summary JSONs live in
`reports/summaries/down-aggregate/`; figures in `reports/figures/`. `eda/`
additionally regenerates the CPT tuning/sensitivity/loss-curve figures.

## Tests

```bash
python -m unittest discover -s tests -v
```

The dependency-free tests cover audit/masking safeguards. With requirements installed, an offline tiny-model integration test exercises tokenizer overflow, final-chunk preservation, fixed evaluation masks, loss computation, training, checkpoint selection, resume and held-out evaluation. It does not download or train the full base/large checkpoints.
