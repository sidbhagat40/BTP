# Paired MLM evaluation

Split: diagnostic
Sample-limited run: False
Diagnostic-only corpus: True

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.15

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 2.017999 ± 0.227558 | 1.565181 ± 0.213939 |
| masked_token_accuracy | 0.580220 ± 0.065590 | 0.626778 ± 0.072421 |
| masked_token_top5_accuracy | 0.764330 ± 0.031733 | 0.825639 ± 0.028567 |
| paper_macro_mlm_loss | 1.963413 ± 0.162760 | 1.514374 ± 0.207252 |
| mask_replaced_top1_accuracy | 0.519418 ± 0.086320 | 0.582095 ± 0.095948 |

Relative reduction in mean token-weighted loss: 22.44%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.21577786401136062, 0.6967396944122303].
95% paired-paper bootstrap CI for CPT minus original accuracy: [-0.021969336472316837, 0.10488403366925107].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
