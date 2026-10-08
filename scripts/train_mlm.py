"""
Continual MLM pre-training of ModernBERT-large on synthetic RHEA text.

Uses only data/splits/train.jsonl and data/splits/val.jsonl.
Never reads probe_pool.jsonl.

Usage (from repo root):
  python scripts/train_mlm.py --config configs/mlm_synth.yaml
  python scripts/train_mlm.py --config configs/mlm_synth.yaml --max-steps 20   # smoke
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import torch
import yaml
from transformers import (
    AutoModelForMaskedLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    set_seed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from hea_bert.data import TextJsonlDataset, pick_precision  # noqa: E402

PROBE_POOL_NAME = "probe_pool.jsonl"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return cfg


def resolve_path(p: str | Path) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def assert_no_probe_leak(train_file: Path, val_file: Path) -> None:
    for p in (train_file, val_file):
        if p.name == PROBE_POOL_NAME or "probe_pool" in p.parts:
            raise RuntimeError(f"Refusing to train/eval on probe pool path: {p}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MLM continual pre-train ModernBERT-large")
    p.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "mlm_synth.yaml")
    p.add_argument("--max-steps", type=int, default=None, help="override for smoke tests")
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(resolve_path(args.config))

    model_path = resolve_path(cfg["model_path"])
    train_file = resolve_path(cfg["train_file"])
    val_file = resolve_path(cfg["val_file"])
    output_dir = resolve_path(args.output_dir or cfg["output_dir"])

    assert_no_probe_leak(train_file, val_file)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run: python scripts/download_modernbert.py"
        )
    if not train_file.exists() or not val_file.exists():
        raise FileNotFoundError(
            "Missing splits. Run: python scripts/split_synthetic_data.py"
        )

    seed = int(cfg.get("seed", 42))
    set_seed(seed)

    max_length = int(cfg.get("max_length", 512))
    mlm_probability = float(cfg.get("mlm_probability", 0.15))

    print(f"Model:      {model_path}")
    print(f"Train:      {train_file}")
    print(f"Val:        {val_file}")
    print(f"Output:     {output_dir}")
    print(f"Max length: {max_length}  MLM p={mlm_probability}  seed={seed}")

    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForMaskedLM.from_pretrained(
        str(model_path),
        local_files_only=True,
    )

    train_ds = TextJsonlDataset(train_file, tokenizer, max_length=max_length)
    val_ds = TextJsonlDataset(val_file, tokenizer, max_length=max_length)
    print(f"Examples:   train={len(train_ds)}  val={len(val_ds)}")

    collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=mlm_probability,
    )

    use_bf16, use_fp16 = pick_precision(
        bool(cfg.get("bf16", True)),
        bool(cfg.get("fp16", False)),
    )
    print(f"Precision:  bf16={use_bf16}  fp16={use_fp16}  cuda={torch.cuda.is_available()}")

    per_device_train_batch_size = int(cfg.get("per_device_train_batch_size", 4))
    gradient_accumulation_steps = int(cfg.get("gradient_accumulation_steps", 8))
    num_train_epochs = float(cfg.get("num_train_epochs", 3))
    warmup_ratio = float(cfg.get("warmup_ratio", 0.06))

    # transformers>=5 dropped warmup_ratio; derive warmup_steps instead
    effective_batch = max(1, per_device_train_batch_size * gradient_accumulation_steps)
    steps_per_epoch = max(1, math.ceil(len(train_ds) / effective_batch))
    if args.max_steps is not None:
        total_steps = int(args.max_steps)
    else:
        total_steps = max(1, int(math.ceil(steps_per_epoch * num_train_epochs)))
    warmup_steps = int(cfg.get("warmup_steps", max(0, int(total_steps * warmup_ratio))))
    print(
        f"Schedule:   steps/epoch≈{steps_per_epoch}  total_steps≈{total_steps}  "
        f"warmup_steps={warmup_steps}"
    )

    train_args_kw = dict(
        output_dir=str(output_dir),
        per_device_train_batch_size=per_device_train_batch_size,
        per_device_eval_batch_size=int(cfg.get("per_device_eval_batch_size", 4)),
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=float(cfg.get("learning_rate", 2e-5)),
        weight_decay=float(cfg.get("weight_decay", 0.01)),
        num_train_epochs=num_train_epochs,
        warmup_steps=warmup_steps,
        lr_scheduler_type=str(cfg.get("lr_scheduler_type", "linear")),
        max_grad_norm=float(cfg.get("max_grad_norm", 1.0)),
        logging_steps=int(cfg.get("logging_steps", 10)),
        eval_strategy=str(cfg.get("eval_strategy", "epoch")),
        save_strategy=str(cfg.get("save_strategy", "epoch")),
        save_total_limit=int(cfg.get("save_total_limit", 2)),
        load_best_model_at_end=bool(cfg.get("load_best_model_at_end", True)),
        metric_for_best_model=str(cfg.get("metric_for_best_model", "eval_loss")),
        greater_is_better=bool(cfg.get("greater_is_better", False)),
        bf16=use_bf16,
        fp16=use_fp16,
        dataloader_num_workers=int(cfg.get("dataloader_num_workers", 0)),
        report_to=cfg.get("report_to", "none"),
        seed=seed,
        remove_unused_columns=False,
    )
    if args.max_steps is not None:
        train_args_kw["max_steps"] = int(args.max_steps)
        train_args_kw["eval_strategy"] = "steps"
        train_args_kw["save_strategy"] = "steps"
        train_args_kw["eval_steps"] = max(1, int(args.max_steps))
        train_args_kw["save_steps"] = max(1, int(args.max_steps))
        print(f"Smoke mode: max_steps={args.max_steps}")

    training_args = TrainingArguments(**train_args_kw)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        processing_class=tokenizer,
    )

    # Baseline val loss before any training steps (full run only)
    if args.max_steps is None:
        print("Evaluating vanilla ModernBERT-large on val (baseline)...")
        baseline = trainer.evaluate()
        baseline_loss = baseline.get("eval_loss")
        if baseline_loss is not None:
            ppl = math.exp(baseline_loss) if baseline_loss < 20 else float("inf")
            print(f"Baseline eval_loss={baseline_loss:.4f}  perplexity≈{ppl:.2f}")
        metrics_path = output_dir / "baseline_metrics.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            __import__("json").dumps(baseline, indent=2),
            encoding="utf-8",
        )

    print("Starting MLM training...")
    train_result = trainer.train()
    trainer.save_model(str(output_dir / "best_or_final"))
    tokenizer.save_pretrained(str(output_dir / "best_or_final"))

    metrics = trainer.evaluate()
    loss = metrics.get("eval_loss")
    if loss is not None:
        ppl = math.exp(loss) if loss < 20 else float("inf")
        metrics["perplexity"] = ppl
        print(f"Final eval_loss={loss:.4f}  perplexity≈{ppl:.2f}")

    out_metrics = output_dir / "train_metrics.json"
    payload = {
        "train": train_result.metrics,
        "eval": metrics,
        "config": {k: (str(v) if isinstance(v, Path) else v) for k, v in cfg.items()},
        "model_path": str(model_path),
        "train_file": str(train_file),
        "val_file": str(val_file),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    out_metrics.write_text(
        __import__("json").dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Saved metrics -> {out_metrics}")
    print(f"Saved model   -> {output_dir / 'best_or_final'}")
    print("Done. probe_pool.jsonl was not used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
