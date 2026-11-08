# Paired MLM evaluation

Split: validation
Sample-limited run: False
Diagnostic-only corpus: False

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.15

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.165424 ± 0.002009 | 0.776079 ± 0.002654 |
| masked_token_accuracy | 0.748107 ± 0.000429 | 0.810789 ± 0.000568 |
| masked_token_top5_accuracy | 0.881777 ± 0.000367 | 0.931354 ± 0.000510 |
| paper_macro_mlm_loss | 1.150426 ± 0.002267 | 0.752597 ± 0.002710 |
| mask_replaced_top1_accuracy | 0.721116 ± 0.000567 | 0.790406 ± 0.000561 |

Relative reduction in mean token-weighted loss: 33.41%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.3761934006277128, 0.4017226852654408].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.0603984299262302, 0.06479737851183662].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
