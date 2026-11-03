#!/usr/bin/env bash
# Sequential, offline evaluation only. Does NOT start training-mask ablations.
# Run from the project root: GPU_INDEX=0 bash run_evaluation.sh
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${GPU_INDEX:-0}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

ORIGINAL="${ORIGINAL_MODEL:-answerdotai/ModernBERT-base}"
CPT="${CPT_MODEL:-outputs/base-full-cpt/final}"
ROOT="${EVAL_OUTPUT_DIR:-outputs/base-evaluation-suite}"

if [[ ! -f hea_cpt/evaluate.py ]]; then
  echo "Run this script from the project root with the hea-cpt environment activated." >&2
  exit 1
fi
if [[ -e "$ROOT" ]]; then
  echo "Output path already exists: $ROOT. Set EVAL_OUTPUT_DIR to a fresh path." >&2
  exit 1
fi
mkdir -p "$ROOT"

quantitative() {
  python -m hea_cpt.evaluate --original-model "$ORIGINAL" --cpt-model "$CPT" \
    --batch-size 1 --offline "$@"
}

echo "1/7: New evaluator smoke test"
quantitative --split validation --probabilities 0.15 --seeds 42 \
  --max-papers 2 --bootstrap-iterations 100 --output-dir "$ROOT/smoke"

echo "2/7: Full validation, five masking seeds"
quantitative --split validation --probabilities 0.15 --seeds 42 43 44 45 46 \
  --output-dir "$ROOT/validation"

echo "3/7: Validation-only masking sensitivity (NOT training-mask tuning)"
quantitative --split validation --probabilities 0.10 0.15 0.30 --seeds 42 43 44 \
  --output-dir "$ROOT/mask-sensitivity"

echo "4/7: Prespecified full test protocol, five masking seeds"
quantitative --split test --probabilities 0.15 --seeds 42 43 44 45 46 \
  --output-dir "$ROOT/test"

echo "5/7: Hand-authored materials passage diagnostics (not a benchmark)"
quantitative --input-file examples/materials_demo.jsonl --split diagnostic \
  --probabilities 0.15 --seeds 42 43 44 45 46 --output-dir "$ROOT/materials-demo"

echo "6/7: Hand-authored English passage diagnostics (not a forgetting benchmark)"
quantitative --input-file examples/general_english_demo.jsonl --split diagnostic \
  --probabilities 0.15 --seeds 42 43 44 45 46 --output-dir "$ROOT/english-demo"

echo "7/7: All 32 controlled cloze probes, including alloy-composition comparisons"
python -m hea_cpt.probes --original-model "$ORIGINAL" --cpt-model "$CPT" \
  --offline --output-dir "$ROOT/probes"

echo "Completed. Quantitative reports: $ROOT/*/report.md"
echo "Side-by-side example report: $ROOT/probes/comparison.md"
