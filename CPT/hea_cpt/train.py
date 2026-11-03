"""Single-GPU ModernBERT CPT, resumable checkpoints and held-out evaluation."""

import argparse
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .common import (
    environment_versions, file_sha256, read_json, require_empty_directory, write_json,
)


@dataclass
class CPTConfig:
    model_name_or_path: str
    data_dir: str
    output_dir: str
    revision: str = "main"
    learning_rate: float = 5e-5
    num_train_epochs: float = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 8
    weight_decay: float = 0.01
    warmup_ratio: float = 0.06
    max_grad_norm: float = 1.0
    precision: str = "auto"
    gradient_checkpointing: bool = True
    eval_steps: int = 500
    logging_steps: int = 25
    save_total_limit: int = 2
    validation_max_samples: int | None = 1024
    seed: int = 42
    validation_seed: int | None = None
    token_weighted_eval: bool = False

    def validate(self):
        for field in ("per_device_train_batch_size", "per_device_eval_batch_size",
                      "gradient_accumulation_steps", "eval_steps", "logging_steps", "save_total_limit"):
            if getattr(self, field) < 1:
                raise ValueError(f"{field} must be positive.")
        if self.validation_max_samples is not None and self.validation_max_samples < 1:
            raise ValueError("validation_max_samples must be positive or null (full validation).")
        if self.learning_rate <= 0 or self.num_train_epochs <= 0 or self.max_grad_norm <= 0:
            raise ValueError("Learning rate, epochs and gradient norm must be positive.")
        if not 0 <= self.warmup_ratio < 1 or self.weight_decay < 0:
            raise ValueError("Invalid warmup ratio or weight decay.")


def choose_precision(requested, cpu):
    import torch

    if requested not in ("auto", "bf16", "fp16", "fp32"):
        raise ValueError("precision must be auto, bf16, fp16 or fp32.")
    if cpu:
        if requested not in ("auto", "fp32"):
            raise ValueError("Use fp32 for the CPU smoke test.")
        return "fp32"
    if not torch.cuda.is_available():
        raise ValueError("CUDA is unavailable. Install CUDA PyTorch on the server, or use --cpu for smoke tests.")
    if torch.cuda.device_count() != 1:
        raise ValueError("Select exactly one GPU with CUDA_VISIBLE_DEVICES (do not combine unequal GPUs).")
    if requested == "auto":
        return "bf16" if torch.cuda.is_bf16_supported() else "fp16"
    if requested == "bf16" and not torch.cuda.is_bf16_supported():
        raise ValueError("This GPU does not support bf16; use auto or fp16.")
    return requested


def subset(dataset, maximum, seed):
    if maximum is None or maximum >= len(dataset):
        return dataset
    if maximum < 1:
        raise ValueError("Sample limits must be positive.")
    return dataset.shuffle(seed=seed).select(range(maximum))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--eval-batch-size", type=int)
    parser.add_argument("--gradient-accumulation-steps", type=int)
    parser.add_argument("--precision", choices=("auto", "bf16", "fp16", "fp32"))
    parser.add_argument("--max-steps", type=int, default=-1, help="Optimizer steps; use 2 for a smoke test.")
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-eval-samples", type=int)
    parser.add_argument("--train-mlm-probability", type=float,
                        help="Optional TRAINING-only mask-rate ablation; saved evaluation masks stay unchanged.")
    parser.add_argument("--resume-from-checkpoint", help="Checkpoint directory, or 'latest' in the output directory.")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--eval-split", choices=("validation", "test"), default="validation")
    parser.add_argument("--model-path", help="Saved CPT model to evaluate; only valid with --eval-only.")
    parser.add_argument("--cpu", action="store_true", help="CPU smoke tests, not full-corpus training.")
    args = parser.parse_args()

    config = CPTConfig(**read_json(args.config))
    for cli, field in (("data_dir", "data_dir"), ("output_dir", "output_dir"),
                       ("batch_size", "per_device_train_batch_size"),
                       ("eval_batch_size", "per_device_eval_batch_size"),
                       ("gradient_accumulation_steps", "gradient_accumulation_steps"),
                       ("precision", "precision")):
        if getattr(args, cli) is not None:
            setattr(config, field, getattr(args, cli))
    config.validate()
    if args.max_steps == 0 or args.max_steps < -1:
        parser.error("--max-steps must be -1 (epochs) or a positive integer.")
    if any(value is not None and value < 1 for value in (args.max_train_samples, args.max_eval_samples)):
        parser.error("Sample limits must be positive.")
    if args.train_mlm_probability is not None and (args.eval_only or not 0 < args.train_mlm_probability < 1):
        parser.error("--train-mlm-probability must lie between 0 and 1 and is only valid for training.")
    if args.model_path and not args.eval_only:
        parser.error("--model-path is only for evaluation. Use --resume-from-checkpoint to resume training.")
    if args.eval_split == "test" and not args.eval_only:
        parser.error("The test split is only available with --eval-only, never for checkpoint selection.")
    if args.eval_only and (not args.output_dir or args.resume_from_checkpoint):
        parser.error("Evaluation requires a new --output-dir and cannot resume training.")
    if int(os.environ.get("WORLD_SIZE", "1")) > 1:
        parser.error("This entry point targets one GPU. Select it with CUDA_VISIBLE_DEVICES.")

    import torch
    from datasets import load_from_disk
    from transformers import AutoConfig, AutoModelForMaskedLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
    from transformers.trainer_utils import get_last_checkpoint

    from .masking import MLMCollator

    precision = choose_precision(config.precision, args.cpu)
    set_seed(config.seed)
    data_dir, output_dir = Path(config.data_dir), Path(config.output_dir)
    manifest_path = data_dir / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported prepared-data format; prepare this corpus again.")
    training_probability = (args.train_mlm_probability if args.train_mlm_probability is not None
                            else manifest["mlm_probability"])
    tokenizer = AutoTokenizer.from_pretrained(data_dir / "tokenizer")
    # Trainer's fast padding path may mark this flag; do not spam the padding advisory.
    tokenizer.deprecation_warnings["Asking-to-pad-a-fast-tokenizer"] = True
    datasets = load_from_disk(str(data_dir / "dataset"))
    if args.eval_only:
        evaluation_data = subset(datasets[args.eval_split], args.max_eval_samples, config.seed)
        training_data = None
    else:
        limit = args.max_eval_samples if args.max_eval_samples is not None else config.validation_max_samples
        evaluation_data = subset(datasets["validation"], limit,
                                 config.seed if config.validation_seed is None else config.validation_seed)
        training_data = subset(datasets["train"], args.max_train_samples, config.seed)

    resume = None
    if args.resume_from_checkpoint:
        resume = (get_last_checkpoint(str(output_dir)) if args.resume_from_checkpoint == "latest"
                  else args.resume_from_checkpoint)
        if not resume or not (Path(resume) / "trainer_state.json").is_file():
            raise ValueError("No resumable Trainer checkpoint was found.")
        if Path(resume).resolve().parent != output_dir.resolve():
            raise ValueError("Resume into the checkpoint's original output directory.")
        previous = read_json(output_dir / "run_config.json")
        if (asdict(CPTConfig(**previous["config"])) != asdict(config)
                or previous["manifest_sha256"] != file_sha256(manifest_path)
                or previous["max_train_samples"] != args.max_train_samples
                or previous["max_eval_samples"] != args.max_eval_samples
                or previous.get("training_mlm_probability", previous["prepared_data"]["mlm_probability"])
                != training_probability):
            raise ValueError("Resume configuration/data changed. Restore the original config and sample limits.")
    else:
        require_empty_directory(output_dir)

    # A resumed run should not depend on the Hub's current 'main' checkpoint or network access.
    model_path = args.model_path or resume or config.model_name_or_path
    revision = None if Path(model_path).is_dir() else config.revision
    upstream_tokenizer = AutoTokenizer.from_pretrained(model_path, revision=revision)
    if (tokenizer.get_vocab() != upstream_tokenizer.get_vocab()
            or tokenizer.special_tokens_map != upstream_tokenizer.special_tokens_map):
        raise ValueError("Prepared tokenizer differs from this model's tokenizer. Prepare compatible data first.")
    model_config = AutoConfig.from_pretrained(model_path, revision=revision)
    if model_config.model_type != "modernbert":
        raise ValueError("This pipeline is for ModernBERT masked language models.")
    if manifest["max_length"] > model_config.max_position_embeddings:
        raise ValueError("Prepared chunks exceed the model's context length.")
    model_config.reference_compile = False
    model_config.sparse_prediction = True  # Project only labelled tokens to the large vocabulary.
    model = AutoModelForMaskedLM.from_pretrained(
        model_path, revision=revision, config=model_config, attn_implementation="sdpa",
    )

    run = {
        "config": asdict(config), "model_loaded": model_path,
        "model_commit": getattr(model.config, "_commit_hash", None),
        "manifest_sha256": file_sha256(manifest_path), "prepared_data": manifest,
        "precision_used": precision,
        "gpu": None if args.cpu else torch.cuda.get_device_name(0),
        "gpu_vram_gib": None if args.cpu else round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
        "versions": environment_versions(), "max_steps": args.max_steps,
        "max_train_samples": args.max_train_samples, "max_eval_samples": args.max_eval_samples,
        "training_mlm_probability": training_probability,
        "training_chunks": len(training_data) if training_data is not None else 0,
        "evaluation_chunks": len(evaluation_data),
        "evaluation_split": args.eval_split if args.eval_only else "validation",
        "effective_batch_size": config.per_device_train_batch_size * config.gradient_accumulation_steps,
        "resume_from_checkpoint": resume,
    }
    write_json(output_dir / ("resume_config.json" if resume else "run_config.json"), run)
    print(f"Device: {run['gpu'] or 'CPU'}; precision: {precision}; effective batch: {run['effective_batch_size']}")
    print(f"Evaluation: {len(evaluation_data):,} chunks with frozen masks. Test is never used for training.")

    training_args = TrainingArguments(
        output_dir=str(output_dir), use_cpu=args.cpu,
        learning_rate=config.learning_rate, num_train_epochs=config.num_train_epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        weight_decay=config.weight_decay, warmup_ratio=config.warmup_ratio,
        max_grad_norm=config.max_grad_norm, lr_scheduler_type="cosine", optim="adamw_torch",
        bf16=precision == "bf16", fp16=precision == "fp16",
        gradient_checkpointing=config.gradient_checkpointing and not args.eval_only,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        eval_strategy="no" if args.eval_only else "steps",
        save_strategy="no" if args.eval_only else "steps",
        eval_steps=config.eval_steps, save_steps=config.eval_steps,
        logging_steps=config.logging_steps, logging_first_step=True,
        save_total_limit=config.save_total_limit, load_best_model_at_end=not args.eval_only,
        metric_for_best_model="eval_loss", greater_is_better=False,
        prediction_loss_only=True, remove_unused_columns=False,
        report_to="none", seed=config.seed, data_seed=config.seed,
        dataloader_num_workers=0, dataloader_pin_memory=not args.cpu,
    )
    trainer_class, callbacks = Trainer, []
    if config.token_weighted_eval:
        from .token_trainer import FinalEvaluationCallback, TokenWeightedTrainer

        trainer_class, callbacks = TokenWeightedTrainer, [FinalEvaluationCallback()]
    trainer = trainer_class(
        model=model, args=training_args, train_dataset=training_data, eval_dataset=evaluation_data,
        data_collator=MLMCollator(tokenizer, training_probability), processing_class=tokenizer,
        callbacks=callbacks,
    )
    # Use standard mean-MLM-loss accumulation; do not pass Trainer's optional loss kwargs.
    trainer.model_accepts_loss_kwargs = False
    if args.eval_only:
        metrics = trainer.evaluate(metric_key_prefix=args.eval_split)
        trainer.save_metrics(args.eval_split, metrics)
        print(metrics)
        return

    # Reuse the exact same corrupted validation chunks before/after CPT and across model sizes.
    if not resume:
        baseline = trainer.evaluate(metric_key_prefix="baseline_validation")
        trainer.save_metrics("baseline_validation", baseline)
    result = trainer.train(resume_from_checkpoint=resume)
    trainer.save_metrics("train", result.metrics)
    trainer.save_state()
    metrics = trainer.evaluate(metric_key_prefix="cpt_validation")
    trainer.save_metrics("cpt_validation", metrics)
    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(output_dir / "final")
    write_json(output_dir / "selection.json", {
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "best_validation_loss": trainer.state.best_metric,
        "final_is_best_checkpoint": trainer.state.best_model_checkpoint is not None,
        "loss_weighting": "labelled_tokens" if config.token_weighted_eval else "trainer_batch_mean",
        "note": "If no scheduled checkpoint was reached (e.g. smoke test), final contains the last weights.",
    })
    print(f"Saved CPT model and tokenizer to {output_dir / 'final'}")


if __name__ == "__main__":
    main()
