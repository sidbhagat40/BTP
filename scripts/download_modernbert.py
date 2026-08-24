"""
Download ModernBERT into the repo so you can load it offline later.

This does not replace the Hugging Face cache. It copies a complete snapshot
into models/modernbert-large (gitignored, ~1.5 GB).

  python scripts/download_modernbert.py
  python scripts/download_modernbert.py --base
"""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", action="store_true")
    args = p.parse_args()

    repo_id = "answerdotai/ModernBERT-base" if args.base else "answerdotai/ModernBERT-large"
    dest = MODELS_DIR / ("modernbert-base" if args.base else "modernbert-large")
    dest.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {repo_id}")
    print(f"  -> {dest}")
    snapshot_download(repo_id=repo_id, local_dir=str(dest))
    weights = dest / "model.safetensors"
    if weights.exists():
        mb = weights.stat().st_size / (1024 * 1024)
        print(f"Done. Weights: {mb:.1f} MB at {weights}")
    else:
        print("Download finished but model.safetensors was not found; check the folder.")


if __name__ == "__main__":
    main()
