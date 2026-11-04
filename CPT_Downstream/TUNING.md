# Validation-only ModernBERT CPT tuning

The completed base CPT run is a baseline, not an established optimum. This
workflow searches the most useful optimization choices with a bounded budget.
All trials start from the same **original pretrained model**. Only the train
split supplies gradient updates. Validation selects checkpoints and trials.

## Search protocol

| Stage | Search | Budget per trial | Validation |
|---|---|---|---|
| `screen` | 3 learning rates × training masking `{0.15, 0.30}` | 2,000 optimizer updates | Fixed 1,024-chunk subset |
| `refine` | Best screen LR/mask; weight decay `{0, 0.1}` × warmup `{0.02, 0.10}` | 2,000 optimizer updates | Same subset |
| `confirm` | Best two short-run configurations plus the baseline, deduplicated | 3 epochs, restarted from original weights | Full validation |
| `repeat` (recommended when budget permits) | Full-run winner and baseline, deduplicated, with two additional training seeds | 3 epochs each | Full validation |

Screening holds weight decay at the source config value (normally `0.01`) and
warmup at `0.06`. Refinement is a small joint search, not a claim to have isolated
individual parameter effects. It may miss interactions with the other screened
learning rates/mask rates. All short-run candidates remain eligible for promotion.

Other choices:

- Effective batch size **32 chunks**: microbatch 1 × accumulation 32 on one GPU.
  This is a documented resource/optimization choice, not a tuned optimum.
  Batch-size tuning is deferred to avoid expanding the LR/batch search. If a
  larger microbatch fits, choose it at study initialization while keeping the
  same effective batch; do not change it midway through the study.
- `max_grad_norm=1.0`: keep the clipping threshold from the baseline config.
  Review logged gradient norms and numerical stability if training is unstable.
- `logging_steps`: inherited from the config (normally 25); not accuracy-tuned.
- `eval_steps=500`: equal checkpoint-selection opportunity within each stage.
- **Training duration is selected through checkpoints within a three-epoch
  maximum**, not through a separate epoch grid. The final budget endpoint is
  evaluated and saved even when it is not divisible by the evaluation interval.
- Cosine decay, sequence length, tokenizer, precision policy and training data
  are held fixed. Changing these later creates a new study.

The primary objective is **token-weighted MLM validation loss**, including the
unchanged targets in the 80/10/10 corruption policy. Every trial uses the same
saved **15% validation corruption**, regardless of training masking rate. The new
optional Trainer calculates the weighted average from each batch's native mean
MLM loss and number of non-ignored labels, without retaining vocabulary logits.
It is used for checkpoint selection and trial ranking. Existing configs retain
their previous evaluation behavior unless `token_weighted_eval` is enabled.

The validation subset seed is fixed at 42 independently of the training seed.
The repeat stage changes training seeds, not evaluation masks or validation
membership. Best checkpoint weights are exported under each trial's `final/`.

## Transfer to the SSH server

Transfer **`tuning_update.zip`** to `~/BTP/CPT/`. It contains pipeline code,
tests, requirements and this guide, without model weights, data or configs.
Extract it into the existing project:

```bash
cd ~/BTP/CPT
conda activate hea-cpt
python -m zipfile -e tuning_update.zip .
python -m hea_cpt.tune --help
```

Use one available, allocated GPU. GPU `0` below is an example; shared GPU memory
pressure can still cause OOM. Run long jobs inside a persistent terminal such as
tmux. Run stages sequentially, with only one runner per study.

## ModernBERT-base: initialize once

Use the original base commit from the completed baseline run:

```bash
python -m hea_cpt.tune init \
  --config configs/base.json \
  --study outputs/base-tuning \
  --original-revision 8949b909ec900327062f0ebf497f51aef5e6f0c8 \
  --learning-rates 2e-5 5e-5 1e-4
```

Initialization freezes the plan and writes six screening trials; it does not
load a model onto the GPU. It defaults to microbatch/evaluation batch 1,
effective batch 32, 2,000 screening steps, and a three-epoch full-run budget.
If using locally downloaded original weights, add
`--original-model models/ModernBERT-base`. Local model files are hashed and
verified before a stage runs. Hub models require an immutable commit ID.

The config's learning rate must be included in the search. This ensures the
source-config baseline is represented. Never point `--original-model` at
`outputs/base-full-cpt/final` or another adapted checkpoint.

## Run tuning

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.tune run \
  --study outputs/base-tuning --stage screen
```

After screening finishes:

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.tune run \
  --study outputs/base-tuning --stage refine
```

After refinement finishes:

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.tune run \
  --study outputs/base-tuning --stage confirm
```

`HF_HUB_OFFLINE=1` requires the original model at the pinned revision to already
be cached (as expected after the previous base run), or local weights. If the
revision is not cached, download it before launching the offline stages.

Full runs **restart** from the original weights with a fresh full-duration
cosine schedule. They do not extend the completed short-run schedule. Short-run
rankings may reverse at full duration, which is why confirmation is required.
The fresh full baseline is always `confirm-01`; it uses the same metric,
validation corpus and endpoint checkpoint policy as the other confirmation
runs. Preserve the earlier completed CPT run as a historical baseline too.

Optional training-seed confirmation:

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.tune run \
  --study outputs/base-tuning --stage repeat
```

With seed 42 initially, this adds seeds 43 and 44 for the baseline and the
validation-selected winner. If the baseline wins, it is repeated only once per
additional seed. Report means and SD across training seeds, not just the best
seed. Five evaluation masking seeds are not five training replications.

### Expected cost

At the prior base run's throughput, ten short runs take about **18 hours**, and
two or three full confirmation runs add about **18–28 hours**: approximately
**37–46 GPU-hours before extra evaluation overhead**. Full validation at each
checkpoint adds overhead relative to the old subset-based run; 30% training
masking can also change throughput. This is an estimate, not a time guarantee.
The repeat stage adds two or four full runs (roughly another 18–37 hours before
extra overhead). Large will take longer. Each trial retains up to two Trainer
checkpoints plus its export; check available disk space before a multi-run study.

## Results and interruptions

```bash
python -m hea_cpt.tune report --study outputs/base-tuning
cat outputs/base-tuning/report.md
```

The study produces:

```text
study.json                    # immutable inputs, original identity and protocol
screen.json / refine.json     # frozen jobs and promotion evidence
confirm.json / repeat.json
trial_configs/                # complete per-run configurations
runs/<trial>/                 # checkpoints, metrics, final model, tuning_result.json
results.csv / results.json    # per-trial validation scores and model paths
report.md                     # stage-specific ranked tables
training_seed_summary.json    # full-run mean/SD grouped by hyperparameters
```

Rank confirmation candidates by full-validation loss. Do not compare a
screening subset score directly with a full-validation score. Tables for an
incomplete stage are provisional; promotion requires all previous-stage trials
to finish. A trial's `selection.json` records its selected checkpoint, and
`trainer_state.json` contains validation curves and logged training metrics.

To resume, rerun the **same stage command**. Completed trials are skipped;
interrupted ones resume their latest Trainer checkpoint with the same planned
budget. If interruption occurs before the first checkpoint, the runner asks you
to move that partial trial directory aside before restarting the trial. It does
not erase partial work. A crash during export is also recoverable from a saved
checkpoint. `--trial screen-01` can restrict a stage to one trial for diagnosis.

The runner creates `running.lock` to prevent simultaneous writes. A normal exit
or Python error removes it. After a killed process/server reboot, verify that
the old runner **and its training subprocess** have stopped, then remove the
stale `running.lock` file and rerun the stage. If training itself failed,
`report` still summarizes previously completed trials.

Initialize studies on the server, in their final location. Paths are frozen and
absolute. To change budgets, source model, search settings or prepared data,
create a new study directory. Never edit generated trial configs in place.

## ModernBERT-large

Run a separate study when enough GPU memory is available. For your downloaded
original large weights and the default large baseline learning rate `3e-5`:

```bash
python -m hea_cpt.tune init \
  --config configs/large.json \
  --original-model models/ModernBERT-large \
  --study outputs/large-tuning \
  --learning-rates 1e-5 3e-5 6e-5
```

Use the same `run` commands with `--study outputs/large-tuning`. Both model sizes
start with microbatch 1 and effective batch 32. Base's winning settings are not
automatically large's winning settings. Fix the earlier GPU-memory availability
problem before launching a long large study.

## Interpretation and next evaluation

This is a bounded search over four hyperparameters, with checkpoint-based
duration selection. It does not prove global optimality. Document the search
space, short/full budgets, fixed choices, all tried configurations, and seed
variability in the project report.

The existing test scores were already inspected. This workflow never evaluates
test data or uses those scores for promotion. Disclose the prior inspection;
if test observations motivate changes, a fresh, untouched, paper-disjoint
holdout is needed for a new confirmatory claim. New masks on old test papers
do not create an untouched holdout. The tiny illustrative probes should not be
used as a tuning objective.

After full confirmation, evaluate the chosen model against the original with
the existing rigorous **validation** evaluator and multiple fixed masking seeds
(use the winning model path from `results.csv`):

```bash
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 python -m hea_cpt.evaluate \
  --original-model answerdotai/ModernBERT-base \
  --original-revision 8949b909ec900327062f0ebf497f51aef5e6f0c8 \
  --cpt-model outputs/base-tuning/runs/CONFIRM_WINNER/final \
  --split validation --probabilities 0.15 --seeds 42 43 44 45 46 \
  --batch-size 1 --offline --output-dir outputs/base-tuning-validation-review
```

Replace `CONFIRM_WINNER` before running. For large, also replace the original
model and study paths. General-language retention requires a substantial
independent validation corpus and a predefined criterion if it is a selection
goal. The current search optimizes HEA MLM loss only. Finally, compare original
versus CPT initialization on the labelled downstream task with matched tuning
budgets and paper-disjoint splits; lower MLM loss alone does not establish
better downstream performance.
