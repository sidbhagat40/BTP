# Synthetic data splits

Created by `python scripts/split_synthetic_data.py` from `data/data.json`.

| File | Role | Use in MLM? |
|------|------|-------------|
| `train.jsonl` | Continual pre-training | Yes |
| `val.jsonl` | Eval loss / early stopping | Eval only |
| `probe_pool.jsonl` | Later T/F, MCQ, cloze generation | **Never** |
| `split_manifest.json` | Seed, fractions, id lists | — |
| `*_ids.txt` | One id per line | Leakage checks |

Fractions: 80% / 10% / 10%, stratified by `kind`, seed `42`.
