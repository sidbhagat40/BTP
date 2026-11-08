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
| token_weighted_mlm_loss | 1.377169 ± 0.175829 | 1.746622 ± 0.239644 |
| masked_token_accuracy | 0.655637 ± 0.058024 | 0.596747 ± 0.033598 |
| masked_token_top5_accuracy | 0.862734 ± 0.053311 | 0.821731 ± 0.027758 |
| paper_macro_mlm_loss | 1.333944 ± 0.148656 | 1.685474 ± 0.218049 |
| mask_replaced_top1_accuracy | 0.613414 ± 0.061263 | 0.550929 ± 0.056104 |

Relative reduction in mean token-weighted loss: -26.83%.
95% paired-paper bootstrap CI for original minus CPT loss: [-0.5177181132733227, -0.2210078777571391].
95% paired-paper bootstrap CI for CPT minus original accuracy: [-0.08455427400431147, -0.03229377107810632].
Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.

Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.
This does not measure downstream accuracy, factual reliability, or training-seed variability.
