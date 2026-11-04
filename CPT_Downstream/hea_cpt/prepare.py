"""Audit and tokenize each paper into non-overlapping, document-local chunks."""

import argparse
import hashlib
import random
from pathlib import Path

from .audit import SPLITS, audit_corpus, iter_documents
from .common import environment_versions, require_empty_directory, write_json
from .masking import mask_example, replacement_vocabulary


def generate_chunks(path, tokenizer, max_length, split, seed, mlm_probability, source_sha256):
    # The source hash is also part of Dataset.from_generator's cache fingerprint.
    del source_sha256
    vocabulary = replacement_vocabulary(tokenizer)
    all_special = set(tokenizer.all_special_ids)
    for document_index, (_, text) in enumerate(iter_documents(path)):
        encoded = tokenizer(
            text, truncation=True, max_length=max_length, stride=0,
            return_overflowing_tokens=True, return_special_tokens_mask=True,
            return_token_type_ids=False, padding=False,
        )
        for chunk_index, ids in enumerate(encoded["input_ids"]):
            special = encoded["special_tokens_mask"][chunk_index]
            # Literal special tokens in source text must never become MLM targets either.
            special = [int(flag or token in all_special) for token, flag in zip(ids, special)]
            if all(special):
                continue
            row = {"input_ids": ids, "attention_mask": encoded["attention_mask"][chunk_index]}
            if split == "train":
                row["special_tokens_mask"] = special
            else:
                rng = random.Random(f"{seed}:{split}:{document_index}:{chunk_index}")
                row["input_ids"], row["labels"] = mask_example(
                    ids, special, tokenizer.mask_token_id, vocabulary, mlm_probability, rng,
                )
            yield row


def prepare_dataset(data_dir, output_dir, tokenizer_name, revision="main", max_length=512,
                    mlm_probability=0.15, seed=42):
    from datasets import Dataset, DatasetDict, Features, List, Value
    from transformers import AutoTokenizer

    if max_length < 8 or max_length % 8:
        raise ValueError("max_length must be a positive multiple of 8 (at least 8).")
    if not 0 < mlm_probability < 1:
        raise ValueError("mlm_probability must be between 0 and 1.")
    report = audit_corpus(data_dir)
    if not report["passed"]:
        raise ValueError("Corpus audit failed: " + "; ".join(report["errors"]))
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, revision=revision, use_fast=True)
    if not tokenizer.is_fast or tokenizer.mask_token_id is None or tokenizer.pad_token_id is None:
        raise ValueError("A fast tokenizer with mask and pad tokens is required.")
    if max_length > tokenizer.model_max_length:
        raise ValueError(f"Requested length exceeds tokenizer limit {tokenizer.model_max_length}.")
    output_dir = require_empty_directory(output_dir)
    write_json(output_dir / "audit.json", report)
    prepared, statistics = {}, {}
    for split in SPLITS:
        fields = {"input_ids": List(Value("int32")), "attention_mask": List(Value("int8"))}
        fields["special_tokens_mask" if split == "train" else "labels"] = List(Value("int32"))
        dataset = Dataset.from_generator(
            generate_chunks,
            gen_kwargs={
                "path": str(Path(data_dir) / f"{split}.jsonl"), "tokenizer": tokenizer,
                "max_length": max_length, "split": split, "seed": seed,
                "mlm_probability": mlm_probability,
                "source_sha256": report["splits"][split]["sha256"],
            },
            features=Features(fields), cache_dir=str(output_dir / "build_cache"),
        )
        if not len(dataset):
            raise ValueError(f"No maskable chunks found in {split}.")
        tokens = sum(sum(row) for row in dataset["attention_mask"])
        statistics[split] = {"chunks": len(dataset), "tokens_including_special": tokens}
        prepared[split] = dataset
        print(f"{split}: {len(dataset):,} chunks; {tokens:,} tokens including special tokens")
    DatasetDict(prepared).save_to_disk(str(output_dir / "dataset"))
    tokenizer.save_pretrained(output_dir / "tokenizer")
    write_json(output_dir / "manifest.json", {
        "format_version": 1, "tokenizer_name": tokenizer_name, "tokenizer_revision": revision,
        "tokenizer_sha256": hashlib.sha256(tokenizer.backend_tokenizer.to_str().encode()).hexdigest(),
        "max_length": max_length, "mlm_probability": mlm_probability, "seed": seed,
        "evaluation_masks": "frozen per document/chunk; same corruption for every evaluation",
        "chunking": "non-overlapping; no cross-document packing; keep final partial chunks",
        "statistics": statistics, "source_files": report["splits"],
        "versions": environment_versions(),
    })
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output-dir", default="artifacts/hea-512")
    parser.add_argument("--tokenizer", default="answerdotai/ModernBERT-base")
    parser.add_argument("--revision", default="main", help="Use a Hub commit SHA for an immutable tokenizer.")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--mlm-probability", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_dataset(args.data_dir, args.output_dir, args.tokenizer, args.revision,
                    args.max_length, args.mlm_probability, args.seed)


if __name__ == "__main__":
    main()
