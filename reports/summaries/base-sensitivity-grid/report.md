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
| token_weighted_mlm_loss | 1.048762 ± 0.003719 | 0.671526 ± 0.003664 |
| masked_token_accuracy | 0.770396 ± 0.001220 | 0.831546 ± 0.001160 |
| masked_token_top5_accuracy | 0.897037 ± 0.000768 | 0.943404 ± 0.000735 |
| paper_macro_mlm_loss | 1.036946 ± 0.006504 | 0.652440 ± 0.007051 |
| mask_replaced_top1_accuracy | 0.746461 ± 0.001258 | 0.813550 ± 0.001246 |

Relative reduction in mean token-weighted loss: 35.97%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.3653152012852827, 0.38828148475660035].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.059027085939520864, 0.06317201423777777].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.1

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.082153 ± 0.003377 | 0.717920 ± 0.002766 |
| masked_token_accuracy | 0.762048 ± 0.000512 | 0.822062 ± 0.000674 |
| masked_token_top5_accuracy | 0.891704 ± 0.000502 | 0.938121 ± 0.000349 |
| paper_macro_mlm_loss | 1.067620 ± 0.004668 | 0.696860 ± 0.004295 |
| mask_replaced_top1_accuracy | 0.736686 ± 0.000716 | 0.802982 ± 0.000829 |

Relative reduction in mean token-weighted loss: 33.66%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.35175859964018, 0.3760208873393051].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.05779816254620031, 0.062130660211198764].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.5

Masking seeds: [42, 43, 44, 45, 46]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 2.239842 ± 0.005451 | 1.542060 ± 0.003445 |
| masked_token_accuracy | 0.586231 ± 0.000840 | 0.676220 ± 0.000588 |
| masked_token_top5_accuracy | 0.749843 ± 0.000571 | 0.836685 ± 0.000439 |
| paper_macro_mlm_loss | 2.217288 ± 0.004829 | 1.500275 ± 0.003128 |
| mask_replaced_top1_accuracy | 0.542495 ± 0.000946 | 0.641653 ± 0.000728 |

Relative reduction in mean token-weighted loss: 31.15%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.6749047135726164, 0.7187236408955887].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.08671739118820793, 0.09288956326743768].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
