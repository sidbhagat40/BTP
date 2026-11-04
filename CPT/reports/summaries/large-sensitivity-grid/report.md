# Paired MLM evaluation

Split: validation
Sample-limited run: False
Diagnostic-only corpus: False

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.05

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 0.830503 ± 0.003583 | 0.600422 ± 0.003220 |
| masked_token_accuracy | 0.803580 ± 0.000757 | 0.845331 ± 0.000616 |
| masked_token_top5_accuracy | 0.923854 ± 0.000734 | 0.952254 ± 0.000733 |
| paper_macro_mlm_loss | 0.817781 ± 0.007127 | 0.584850 ± 0.006050 |
| mask_replaced_top1_accuracy | 0.782867 ± 0.001078 | 0.828757 ± 0.000776 |

Relative reduction in mean token-weighted loss: 27.70%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.22090848818093045, 0.23868035451820188].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.03993045060990168, 0.04343127405474015].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.1

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 0.887749 ± 0.003079 | 0.639883 ± 0.002659 |
| masked_token_accuracy | 0.792928 ± 0.000837 | 0.836512 ± 0.000890 |
| masked_token_top5_accuracy | 0.917040 ± 0.000418 | 0.947726 ± 0.000303 |
| paper_macro_mlm_loss | 0.873387 ± 0.004344 | 0.622327 ± 0.003045 |
| mask_replaced_top1_accuracy | 0.770658 ± 0.000903 | 0.818882 ± 0.000968 |

Relative reduction in mean token-weighted loss: 27.92%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.23823606932762698, 0.2568834110336535].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.041809607889648506, 0.04527585443648859].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.5

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.891890 ± 0.003452 | 1.377617 ± 0.002567 |
| masked_token_accuracy | 0.630950 ± 0.000646 | 0.702034 ± 0.000555 |
| masked_token_top5_accuracy | 0.793909 ± 0.000387 | 0.858195 ± 0.000448 |
| paper_macro_mlm_loss | 1.867147 ± 0.002996 | 1.340817 ± 0.002619 |
| mask_replaced_top1_accuracy | 0.591590 ± 0.000826 | 0.670066 ± 0.000720 |

Relative reduction in mean token-weighted loss: 27.18%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.4953103210118928, 0.5314853016093565].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.0682514693168622, 0.07359958720177694].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
