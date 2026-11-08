# Paired MLM evaluation

Split: validation
Sample-limited run: False
Diagnostic-only corpus: False

Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.
mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.
Standard deviation is across masking seeds, not independent CPT training runs.

## Selection probability 0.1

Masking seeds: [42, 43, 44]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.082420 ± 0.002374 | 0.717307 ± 0.002565 |
| masked_token_accuracy | 0.762032 ± 0.000321 | 0.822190 ± 0.000666 |
| masked_token_top5_accuracy | 0.891690 ± 0.000356 | 0.938102 ± 0.000487 |
| paper_macro_mlm_loss | 1.065711 ± 0.003058 | 0.695080 ± 0.004557 |
| mask_replaced_top1_accuracy | 0.736653 ± 0.000587 | 0.803151 ± 0.000860 |

Relative reduction in mean token-weighted loss: 33.73%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.35236886435515996, 0.37731874081841926].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.05787624484237986, 0.062352592760099676].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.15

Masking seeds: [42, 43, 44]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.165367 ± 0.002780 | 0.776219 ± 0.003731 |
| masked_token_accuracy | 0.748151 ± 0.000469 | 0.810757 ± 0.000796 |
| masked_token_top5_accuracy | 0.881937 ± 0.000417 | 0.931344 ± 0.000600 |
| paper_macro_mlm_loss | 1.149200 ± 0.002107 | 0.751968 ± 0.003524 |
| mask_replaced_top1_accuracy | 0.721337 ± 0.000130 | 0.790566 ± 0.000642 |

Relative reduction in mean token-weighted loss: 33.39%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.37575445198013574, 0.4021798716494262].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.06028239976003782, 0.0647926114270478].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

## Selection probability 0.3

Masking seeds: [42, 43, 44]

| Metric | Original mean ± SD | CPT mean ± SD |
|---|---:|---:|
| token_weighted_mlm_loss | 1.500478 ± 0.003919 | 1.003491 ± 0.003472 |
| masked_token_accuracy | 0.694200 ± 0.000591 | 0.767891 ± 0.001130 |
| masked_token_top5_accuracy | 0.841025 ± 0.000602 | 0.904258 ± 0.000521 |
| paper_macro_mlm_loss | 1.481719 ± 0.004083 | 0.973574 ± 0.002882 |
| mask_replaced_top1_accuracy | 0.661656 ± 0.000932 | 0.742972 ± 0.001557 |

Relative reduction in mean token-weighted loss: 33.12%.
95% paired-paper bootstrap CI for original minus CPT loss: [0.480419254414267, 0.5126563926667939].
95% paired-paper bootstrap CI for CPT minus original accuracy: [0.07095244178954117, 0.076202474019709].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
