"""
Continued MLM pretraining of ModernBERT-base on the synthetic HEA corpus.

Purpose
-------
This is the SECOND stage of the AlloyBERT pipeline: continued (domain-
adaptive) masked-language-model pretraining of an already-pretrained
ModernBERT checkpoint on the synthetic alloy text corpus you generated.
This stage is unsupervised -- it needs no numeric labels, only text -- and
its only job is to shift ModernBERT's representations toward this domain's
vocabulary and reasoning patterns before you later attach a regression head
and fine-tune on real, literature-derived property data (a separate, later
stage that still needs to happen).

Honest caveat given your corpus size
-------------------------------------
~600 passages is small for continued pretraining. Realistically this will
nudge the model's representations toward alloy vocabulary rather than
deeply reshape them -- that's still useful, but don't expect dramatic
before/after differences, and watch eval loss closely: with this little
data it's easy to overfit if you push epochs too high. Defaults below
(3 epochs, small LR) are chosen conservatively for that reason; if eval
loss starts rising while train loss keeps falling, stop early rather than
pushing further.

Requirements
------------
    pip install "transformers>=4.48" datasets accelerate torch --break-system-packages
ModernBERT support landed in transformers 4.48 -- an older version will
fail to recognize the architecture, so check `transformers.__version__`
first if you hit a "model type not recognized" error.

Usage
-----
    python pretrain_modernbert_mlm.py \\
        --corpus hea_corpus.jsonl \\
        --model_name answerdotai/ModernBERT-base \\
        --output_dir ./heabert-base-pretrained \\
        --num_train_epochs 3

For ModernBERT-large later, just point --model_name at
answerdotai/ModernBERT-large (and likely lower --per_device_train_batch_size
to fit memory).
"""

import argparse
import math
import os

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForMaskedLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
    set_seed,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=str, default="hea_corpus.jsonl", help="Path to the JSONL corpus (needs a 'text' field per line).")
    ap.add_argument("--model_name", type=str, default="answerdotai/ModernBERT-base")
    ap.add_argument("--output_dir", type=str, default="./heabert-base-pretrained")
    ap.add_argument("--max_length", type=int, default=384, help="Token truncation length. Passages run ~150-250 tokens; 384 gives headroom.")
    ap.add_argument(
        "--mlm_probability",
        type=float,
        default=0.30,
        help="Fraction of tokens masked per example. ModernBERT's own pretraining recipe used 30%% "
        "(higher than BERT's classic 15%%) -- matching that tends to work better for continued "
        "pretraining of this architecture specifically.",
    )
    ap.add_argument("--num_train_epochs", type=float, default=3.0, help="Kept low deliberately -- see the overfitting caveat above.")
    ap.add_argument("--per_device_train_batch_size", type=int, default=8)
    ap.add_argument("--per_device_eval_batch_size", type=int, default=8)
    ap.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Effective batch size = per_device_train_batch_size * this * num_gpus.")
    ap.add_argument("--learning_rate", type=float, default=2e-5, help="Kept an order of magnitude below typical from-scratch pretraining LR -- this is CONTINUED pretraining, not training from random init.")
    ap.add_argument("--warmup_ratio", type=float, default=0.1)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--eval_fraction", type=float, default=0.10, help="Fraction of the corpus held out for eval loss / perplexity tracking.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--logging_steps", type=int, default=10)
    args = ap.parse_args()

    set_seed(args.seed)

    if not os.path.exists(args.corpus):
        raise SystemExit(f"Corpus file not found: {args.corpus}")

    # ------------------------------------------------------------------
    # 1. Load and split the corpus
    # ------------------------------------------------------------------
    raw = load_dataset("json", data_files=args.corpus)["train"]
    print(f"Loaded {len(raw)} passages from {args.corpus}")
    if len(raw) < 50:
        print("[warn] very small corpus -- continued pretraining benefit will be limited; consider generating more before investing much compute here.")

    split = raw.train_test_split(test_size=args.eval_fraction, seed=args.seed)
    train_raw, eval_raw = split["train"], split["test"]
    print(f"Train: {len(train_raw)} | Eval: {len(eval_raw)}")

    # ------------------------------------------------------------------
    # 2. Tokenizer + tokenization
    # ------------------------------------------------------------------
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    def tokenize_fn(examples):
        # No padding here -- DataCollatorForLanguageModeling pads dynamically per
        # batch, which is more efficient than padding every example to max_length.
        return tokenizer(examples["text"], truncation=True, max_length=args.max_length)

    columns_to_remove = raw.column_names  # drop composition/processing_route/etc. metadata; keep only input_ids/attention_mask
    train_tokenized = train_raw.map(tokenize_fn, batched=True, remove_columns=columns_to_remove)
    eval_tokenized = eval_raw.map(tokenize_fn, batched=True, remove_columns=columns_to_remove)

    # ------------------------------------------------------------------
    # 3. Model + MLM data collator
    # ------------------------------------------------------------------
    model = AutoModelForMaskedLM.from_pretrained(args.model_name)

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=args.mlm_probability,
    )

    # ------------------------------------------------------------------
    # 4. Trainer
    # ------------------------------------------------------------------
    # transformers v5 dropped TrainingArguments(warmup_ratio=...) -- only
    # warmup_steps is accepted now, so compute the equivalent step count
    # from args.warmup_ratio ourselves.
    steps_per_epoch = max(1, len(train_tokenized) // (args.per_device_train_batch_size * args.gradient_accumulation_steps))
    total_steps = steps_per_epoch * math.ceil(args.num_train_epochs)
    warmup_steps = max(1, int(total_steps * args.warmup_ratio))

    # Detect actual hardware capability rather than assuming a GPU with bf16
    # support is available -- a mismatched CUDA driver/PyTorch build (as seen
    # here) makes torch.cuda.is_available() report False even when nvidia-smi
    # shows a GPU, and forcing bf16=True in that case fails validation instead
    # of just falling back. use_cpu is set explicitly when no GPU is usable,
    # since transformers requires that explicit opt-in rather than inferring it.
    cuda_available = torch.cuda.is_available()
    use_bf16 = cuda_available and torch.cuda.is_bf16_supported()
    use_fp16 = cuda_available and not use_bf16
    if not cuda_available:
        print("[warn] no usable CUDA GPU detected (driver/PyTorch build mismatch, or no GPU) -- training on CPU. This will be considerably slower; fixing the driver/torch mismatch is worth doing before a larger run.")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=args.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=args.logging_steps,
        report_to="none",
        use_cpu=not cuda_available,
        bf16=use_bf16,
        fp16=use_fp16,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=eval_tokenized,
        data_collator=data_collator,
    )

    trainer.train()

    # ------------------------------------------------------------------
    # 5. Final eval + save
    # ------------------------------------------------------------------
    eval_metrics = trainer.evaluate()
    eval_loss = eval_metrics.get("eval_loss")
    if eval_loss is not None:
        try:
            perplexity = math.exp(eval_loss)
        except OverflowError:
            perplexity = float("inf")
        print(f"Final eval loss: {eval_loss:.4f} | perplexity: {perplexity:.2f}")

    final_dir = os.path.join(args.output_dir, "final")
    trainer.save_model(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"Saved HEABERT checkpoint to {final_dir}")
    print("This checkpoint is the domain-adapted encoder. The next stage (regression")
    print("fine-tuning) is separate and needs a real, labeled composition->property dataset.")


if __name__ == "__main__":
    main()