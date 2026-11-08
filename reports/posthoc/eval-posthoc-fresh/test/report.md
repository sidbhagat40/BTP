# Paired MLM evaluation

Split: test
Sample-limited run: False
Diagnostic-only corpus: False

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.15

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.180332 ± 0.004296 | 0.772136 ± 0.002272 |
| masked_token_accuracy | 0.745663 ± 0.001026 | 0.811234 ± 0.000682 |
| masked_token_top5_accuracy | 0.879753 ± 0.000672 | 0.931767 ± 0.000183 |
| paper_macro_mlm_loss | 1.164245 ± 0.004590 | 0.753347 ± 0.002628 |
| mask_replaced_top1_accuracy | 0.718472 ± 0.000996 | 0.790805 ± 0.000693 |

Relative reduction in mean token-weighted loss: 34.58%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.39556693312067415, 0.4205104045938472].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.06354599424640882, 0.06760840253015503].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
