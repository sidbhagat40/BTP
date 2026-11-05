"""LoRA regression fine-tuning of a frozen CPT-pipeline model on the MPEA yield-strength task.

One process = one (model-init, seed) run. Designed for a sweep driven by a loop:
  for arm in B1 B2 B3 L1 L2; for seed in 42 43 3704.

Provenance: every run records the dataset manifest SHA-256, the initial model's
config.json and model.safetensors hashes (the frozen-identity pattern from the
tuning study), and the full effective hyperparameter set. Test predictions per
row are saved so aggregation can compute paired-paper bootstrap CIs without
re-running anything. The evaluation split is read-only and never written.

Usage:
  python -m downstream.finetune_regression \
      --model-path outputs/base-tuning/runs/confirm-02/final \
      --arm B3 --seed 42 --data-dir data/hea-prop-ys --output-dir outputs/down-b3-s42
"""

import argparse
import gc
import hashlib
import json
import math
import os

import numpy as np
import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          DataCollatorWithPadding, EarlyStoppingCallback,
                          Trainer, TrainingArguments, set_seed)


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def regression_metrics(y_true, y_pred):
    err = np.asarray(y_pred) - np.asarray(y_true)
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {"mae": mae, "rmse": rmse, "r2": 1.0 - ss_res / ss_tot}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-path", required=True)
    ap.add_argument("--model-revision", default=None,
                    help="HF revision (only for hub models, e.g. pinned original-base commit)")
    ap.add_argument("--arm", required=True, help="e.g. B1/B2/B3/L1/L2")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--data-dir", required=True, help="dir with primary-C-{train,validation,test}.jsonl")
    ap.add_argument("--manifest", default=None, help="path to manifest.json; default <data-dir>/manifest.json")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--role-prefix", default="primary-C", help="file prefix from build_property_dataset")
    # hyperparameters (frozen defaults; sweep only via --lr)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--gradient-accumulation", type=int, default=1,
                    help="effective batch = batch-size x this; keep product equal across arms")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.1)
    ap.add_argument("--weight-decay", type=float, default=0.05)
    ap.add_argument("--warmup-ratio", type=float, default=0.1)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()

    manifest_path = args.manifest or os.path.join(args.data_dir, "manifest.json")
    files = {}
    for split in ("train", "validation", "test"):
        files[split] = os.path.join(args.data_dir, f"{args.role_prefix}-{split}.jsonl")
        if not os.path.exists(files[split]):
            raise SystemExit(f"Missing dataset file: {files[split]}")
    manifest_sha = sha256_of_file(manifest_path)

    os.makedirs(args.output_dir, exist_ok=True)
    set_seed(args.seed)
    torch.cuda.empty_cache()
    revision_kwargs = {"revision": args.model_revision} if args.model_revision else {}

    dataset = load_dataset("json", data_files={k: str(v) for k, v in files.items()})
    targets = np.array([x["target"] for x in dataset["train"]], dtype=np.float64)
    y_mean, y_std = float(targets.mean()), float(targets.std())
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, **revision_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_fn(examples):
        enc = tokenizer(examples["text"], truncation=True, max_length=args.max_length)
        enc["labels"] = [(float(y) - y_mean) / y_std for y in examples["target"]]
        return enc

    tokenized = dataset.map(tokenize_fn, batched=True,
                            remove_columns=[c for c in dataset["train"].column_names if c != "labels"])

    def compute_metrics(eval_pred):
        preds, labels = eval_pred
        p = np.squeeze(preds) * y_std + y_mean
        t = np.squeeze(labels) * y_std + y_mean
        return regression_metrics(t, p)

    def build_model():
        model = AutoModelForSequenceClassification.from_pretrained(
            args.model_path, num_labels=1, problem_type="regression",
            attn_implementation="sdpa", reference_compile=False, torch_dtype=torch.float32,
            **revision_kwargs)
        model.config.pad_token_id = tokenizer.pad_token_id
        cfg = LoraConfig(task_type=TaskType.SEQ_CLS, r=args.lora_r, lora_alpha=args.lora_alpha,
                         target_modules=["Wqkv", "Wo", "Wi"], bias="none",
                         lora_dropout=args.lora_dropout, modules_to_save=["classifier", "head"])
        peft_model = get_peft_model(model, cfg)
        peft_model.enable_input_require_grads()
        return peft_model

    model = build_model()
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir=os.path.join(args.output_dir, "CHECKPOINTS"),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=16,
        gradient_accumulation_steps=args.gradient_accumulation,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        max_grad_norm=1.0,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        report_to="none",
        logging_strategy="steps", logging_steps=50, logging_first_step=True,
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_rmse", greater_is_better=False,
        seed=args.seed, dataloader_num_workers=2, remove_unused_columns=False,
        label_names=["labels"])
    trainer = Trainer(model=model, processing_class=tokenizer,
                      train_dataset=tokenized["train"], eval_dataset=tokenized["validation"],
                      args=targs, data_collator=DataCollatorWithPadding(tokenizer),
                      compute_metrics=compute_metrics,
                      callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)])
    trainer.train()

    results = {"arm": args.arm, "seed": args.seed,
               "lr": args.lr, "epochs": args.epochs, "per_split": {}}
    raw_targets, raw_predictions = {}, {}
    for split in ("validation", "test"):
        out = trainer.predict(tokenized[split])
        pred = np.squeeze(out.predictions) * y_std + y_mean
        true = np.array([x["target"] for x in dataset[split]], dtype=np.float64)
        results["per_split"][split] = regression_metrics(true, pred)
        results["per_split"][f"baseline_mean_predictor_{split}"] = regression_metrics(
            true, np.full_like(true, y_mean))
        raw_predictions[split] = pred.tolist()
        raw_targets[split] = true.tolist()

    results["dataset_manifest_sha256"] = manifest_sha
    config_path = os.path.join(args.model_path, "config.json")
    if os.path.exists(config_path):
        identity = {"path": args.model_path, "config_sha256": sha256_of_file(config_path)}
        safet = os.path.join(args.model_path, "model.safetensors")
        if os.path.exists(safet):
            identity["safetensors_sha256"] = sha256_of_file(safet)
    else:
        identity = {"path": args.model_path, "revision": args.model_revision,
                    "note": "hub-resolved; snapshot hashes not pinned by this run"}
    results["model_identity"] = identity
    results["hyperparameters"] = {"lora_r": args.lora_r, "lora_alpha": args.lora_alpha,
                                  "lora_dropout": args.lora_dropout, "weight_decay": args.weight_decay,
                                  "warmup_ratio": args.warmup_ratio, "batch_size": args.batch_size, "gradient_accumulation": args.gradient_accumulation,
                                  "max_length": args.max_length, "patience": args.patience}

    seed_pred_path = os.path.join(args.output_dir, "test_predictions.json")
    with open(seed_pred_path, "w", encoding="utf-8") as fh:
        json.dump({"arm": args.arm, "seed": args.seed,
                   "targets": raw_targets, "predictions": raw_predictions}, fh)
    with open(os.path.join(args.output_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(json.dumps(results["per_split"], indent=2))
    del trainer, model
    gc.collect(); torch.cuda.empty_cache()
    print("Saved:", os.path.join(args.output_dir, "results.json"))


if __name__ == "__main__":
    main()

