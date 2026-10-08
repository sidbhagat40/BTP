"""Shared helpers for HEA-BERT MLM training."""

from __future__ import annotations

import json
from pathlib import Path

import torch
from torch.utils.data import Dataset


def load_jsonl(path: Path | str) -> list[dict]:
    path = Path(path)
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class TextJsonlDataset(Dataset):
    """Tokenized MLM dataset; labels are filled by DataCollatorForLanguageModeling."""

    def __init__(self, path: Path | str, tokenizer, max_length: int = 512) -> None:
        self.rows = load_jsonl(path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        if not self.rows:
            raise ValueError(f"empty dataset: {path}")
        if any("text" not in r for r in self.rows):
            raise ValueError(f"every row needs a text field: {path}")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict:
        text = self.rows[idx]["text"]
        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_special_tokens_mask=True,
        )
        return {
            "input_ids": enc["input_ids"],
            "attention_mask": enc["attention_mask"],
            "special_tokens_mask": enc["special_tokens_mask"],
        }


def resolve_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def pick_precision(bf16_flag: bool, fp16_flag: bool) -> tuple[bool, bool]:
    """Return (use_bf16, use_fp16) with safe fallbacks."""
    if not torch.cuda.is_available():
        return False, False
    if bf16_flag and torch.cuda.is_bf16_supported():
        return True, False
    if fp16_flag or bf16_flag:
        # fall back to fp16 if bf16 requested but unsupported
        return False, True
    return False, False
