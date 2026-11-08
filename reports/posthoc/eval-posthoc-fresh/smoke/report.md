# Paired MLM evaluation

Split: validation
Sample-limited run: True
Diagnostic-only corpus: False

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.15

Masking seeds: [42]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.293526 ± 0.000000 | 0.879005 ± 0.000000 |
| masked_token_accuracy | 0.731392 ± 0.000000 | 0.784466 ± 0.000000 |
| masked_token_top5_accuracy | 0.864078 ± 0.000000 | 0.916505 ± 0.000000 |
| paper_macro_mlm_loss | 1.275495 ± 0.000000 | 0.843101 ± 0.000000 |
| mask_replaced_top1_accuracy | 0.700000 ± 0.000000 | 0.760317 ± 0.000000 |

Relative reduction in mean token-weighted loss: 32.05%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.3703386829243117, 0.4944499952114868].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.04723618090452261, 0.06363636363636363].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
