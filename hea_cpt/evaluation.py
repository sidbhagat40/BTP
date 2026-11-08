"""Exact MLM metrics, paper-level paired bootstrap and reproducible evaluation data."""

import hashlib
import json
import random
import statistics
from contextlib import nullcontext

from .audit import iter_documents
from .masking import mask_example, replacement_vocabulary


def original_chunks(path, tokenizer, max_length, source_sha256, max_papers=None):
    """Yield chunk dictionaries for every paper; masks are NOT drawn here yet.

    Each row carries paper_id/source_line/chunk_id provenance plus unmasked
    input ids and a special-tokens mask; evaluate_condition assigns masks.
    """
    del source_sha256  # Included in the datasets generator cache key.
    special_ids = set(tokenizer.all_special_ids)
    for paper_id, (line, text) in enumerate(iter_documents(path)):
        if max_papers is not None and paper_id >= max_papers:
            break
        encoded = tokenizer(text, truncation=True, max_length=max_length, stride=0,
                            return_overflowing_tokens=True, return_special_tokens_mask=True,
                            return_token_type_ids=False, padding=False)
        for chunk_id, ids in enumerate(encoded["input_ids"]):
            special = [int(flag or token in special_ids) for token, flag in
                       zip(ids, encoded["special_tokens_mask"][chunk_id])]
            if all(special):
                continue
            yield {"paper_id": paper_id, "source_line": line, "chunk_id": chunk_id,
                   "input_ids": ids, "attention_mask": encoded["attention_mask"][chunk_id],
                   "special_tokens_mask": special}


class EvaluationCollator:
    """Apply frozen evaluation masks and pair each batch with per-chunk metadata.

    Masks come from a deterministic per-(seed, split, paper, chunk) RNG so a
    model pair always sees byte-identical corruption; a SHA-256 fingerprint
    of every masked example is accumulated for corruption equality checks.
    """

    def __init__(self, tokenizer, probability, seed, split):
        """Store tokenizer, masking probability and the fingerprint namespace."""
        self.tokenizer, self.probability = tokenizer, probability
        self.seed, self.split = seed, split
        self.vocabulary = replacement_vocabulary(tokenizer)

    def __call__(self, rows):
        """Collate a batch, returning (padded tensors with labels, metadata list)."""
        import torch

        inputs, targets, metadata = [], [], []
        for row in rows:
            rng = random.Random(f"{self.seed}:{self.split}:{row['paper_id']}:{row['chunk_id']}")
            ids, labels = mask_example(row["input_ids"], row["special_tokens_mask"],
                                       self.tokenizer.mask_token_id, self.vocabulary,
                                       self.probability, rng)
            inputs.append({"input_ids": ids, "attention_mask": row["attention_mask"]})
            targets.append(labels)
            fingerprint = hashlib.sha256(json.dumps(
                [row["paper_id"], row["chunk_id"], ids, labels], separators=(",", ":")
            ).encode()).hexdigest()
            metadata.append({"paper_id": row["paper_id"], "source_line": row["source_line"],
                             "content_tokens": len(ids) - sum(row["special_tokens_mask"]),
                             "fingerprint": fingerprint})
        batch = self.tokenizer.pad(inputs, padding=True, pad_to_multiple_of=8, return_tensors="pt")
        batch["labels"] = torch.full_like(batch["input_ids"], -100)
        for i, labels in enumerate(targets):
            start = 0 if self.tokenizer.padding_side == "right" else batch["input_ids"].shape[1] - len(labels)
            batch["labels"][i, start:start + len(labels)] = torch.tensor(labels)
        return batch, metadata


def autocast_context(device, precision):
    """Return an active autocast context for CUDA bf16/fp16, or a no-op in fp32/CPU."""
    import torch

    return (torch.autocast("cuda", dtype=torch.bfloat16 if precision == "bf16" else torch.float16)
            if device.type == "cuda" and precision != "fp32" else nullcontext())


def metrics_from_papers(papers):
    """Aggregate per-paper counters into the exact token-weighted metric set."""
    count = sum(row["targets"] for row in papers)
    if not count:
        raise ValueError("No labelled text tokens were evaluated.")
    masked_count = sum(row["mask_token_targets"] for row in papers)
    content_count = sum(row["content_tokens"] for row in papers)
    return {
        "token_weighted_mlm_loss": sum(row["nll_sum"] for row in papers) / count,
        "masked_token_accuracy": sum(row["top1_correct"] for row in papers) / count,
        "masked_token_top5_accuracy": sum(row["top5_correct"] for row in papers) / count,
        "paper_macro_mlm_loss": statistics.mean(row["nll_sum"] / row["targets"] for row in papers),
        "mask_replaced_top1_accuracy": (sum(row["mask_token_correct"] for row in papers) / masked_count
                                         if masked_count else None),
        "labelled_tokens": count, "content_tokens": content_count,
        "realized_selection_fraction": count / content_count,
        "mask_replaced_labelled_tokens": masked_count,
        "papers": len(papers), "chunks": sum(row["chunks"] for row in papers),
    }


def evaluate_condition(model, tokenizer, chunks, probability, seed, split, device, precision, batch_size):
    """Evaluate one model under one (probability, seed) condition.

    Streams masked batches in inference mode, accumulates per-paper NLL/top1/
    top5 counters, refuses non-finite losses, and returns per-paper records
    plus aggregate metrics and a corruption fingerprint.
    """
    import torch
    import torch.nn.functional as functional
    from torch.utils.data import DataLoader
    from tqdm.auto import tqdm

    loader = DataLoader(chunks, batch_size=batch_size, shuffle=False, num_workers=0,
                        collate_fn=EvaluationCollator(tokenizer, probability, seed, split))
    papers, corruption_hash = {}, hashlib.sha256()
    model.eval()
    with torch.inference_mode():
        for batch, metadata in tqdm(loader, desc=f"p={probability} seed={seed}"):
            batch = {name: value.to(device) for name, value in batch.items()}
            selected = batch["labels"] != -100
            labels = batch["labels"][selected]
            with autocast_context(device, precision):
                logits = model(**batch).logits
            if logits.ndim != 2 or logits.shape[0] != labels.numel():
                raise ValueError("Expected sparse ModernBERT logits for exactly the labelled positions.")
            logits = logits.float()
            losses = functional.cross_entropy(logits, labels, reduction="none").double().cpu()
            if not torch.isfinite(losses).all():
                raise ValueError("Non-finite evaluation loss; stop rather than publishing invalid metrics.")
            top = logits.topk(min(5, logits.shape[-1]), dim=-1).indices
            correct1 = (top[:, 0] == labels).cpu()
            correct5 = (top == labels[:, None]).any(dim=1).cpu()
            mask_positions = (batch["input_ids"][selected] == tokenizer.mask_token_id).cpu()
            counts = selected.sum(dim=1).tolist()
            offset = 0
            for info, count in zip(metadata, counts):
                part = slice(offset, offset + count)
                offset += count
                corruption_hash.update(info["fingerprint"].encode())
                paper = papers.setdefault(info["paper_id"], {
                    "paper_id": info["paper_id"], "source_line": info["source_line"],
                    "nll_sum": 0.0, "targets": 0, "top1_correct": 0, "top5_correct": 0,
                    "mask_token_targets": 0, "mask_token_correct": 0,
                    "content_tokens": 0, "chunks": 0,
                })
                paper["nll_sum"] += losses[part].sum().item()
                paper["targets"] += count
                paper["top1_correct"] += correct1[part].sum().item()
                paper["top5_correct"] += correct5[part].sum().item()
                paper["mask_token_targets"] += mask_positions[part].sum().item()
                paper["mask_token_correct"] += (correct1[part] & mask_positions[part]).sum().item()
                paper["content_tokens"] += info["content_tokens"]
                paper["chunks"] += 1
    papers = sorted(papers.values(), key=lambda row: row["paper_id"])
    return {"probability": probability, "seed": seed, "corruption_sha256": corruption_hash.hexdigest(),
            "metrics": metrics_from_papers(papers), "per_paper": papers}


def paired_bootstrap(original_runs, adapted_runs, iterations=2000, seed=2026):
    """Resample papers, paired across models and masking seeds (not individual chunks)."""
    import numpy as np

    if len(original_runs) != len(adapted_runs) or not original_runs:
        raise ValueError("Need corresponding model runs for every masking seed.")
    paper_ids = [row["paper_id"] for row in original_runs[0]["per_paper"]]
    ids = np.random.default_rng(seed).integers(0, len(paper_ids), size=(iterations, len(paper_ids)))
    loss_samples, accuracy_samples, macro_samples = [], [], []
    for original, adapted in zip(original_runs, adapted_runs):
        if ((original["seed"], original["probability"], original["corruption_sha256"])
                != (adapted["seed"], adapted["probability"], adapted["corruption_sha256"])):
            raise ValueError("Models did not receive identical evaluation corruption.")
        for run in (original, adapted):
            if [row["paper_id"] for row in run["per_paper"]] != paper_ids:
                raise ValueError("Paper mapping differs between runs.")
        a, b = original["per_paper"], adapted["per_paper"]
        counts = np.array([row["targets"] for row in a])
        if not np.array_equal(counts, [row["targets"] for row in b]):
            raise ValueError("Supervised-token counts differ between models.")
        loss_delta = np.array([x["nll_sum"] - y["nll_sum"] for x, y in zip(a, b)])
        accuracy_delta = np.array([y["top1_correct"] - x["top1_correct"] for x, y in zip(a, b)])
        loss_samples.append(loss_delta[ids].sum(axis=1) / counts[ids].sum(axis=1))
        accuracy_samples.append(accuracy_delta[ids].sum(axis=1) / counts[ids].sum(axis=1))
        macro_samples.append((loss_delta / counts)[ids].mean(axis=1))

    def interval(samples):
        """Percentile (2.5%, 97.5%) interval of the bootstrap draws."""
        return np.quantile(np.mean(samples, axis=0), [0.025, 0.975]).tolist()

    return {
        "unit": "source paper; paired across models and all masking seeds",
        "papers": len(paper_ids),
        "iterations": iterations, "bootstrap_seed": seed,
        "positive_means": "CPT improvement",
        "loss_reduction_95ci": interval(loss_samples),
        "accuracy_increase_95ci": interval(accuracy_samples),
        "paper_macro_loss_reduction_95ci": interval(macro_samples),
        "scope": "Paper-sampling uncertainty conditional on these checkpoints and masking seeds; not training-seed uncertainty.",
    }


def summarize_runs(runs):
    """Mean and SD-across-mask-seeds for each headline metric over seed runs."""
    keys = ("token_weighted_mlm_loss", "masked_token_accuracy", "masked_token_top5_accuracy",
            "paper_macro_mlm_loss", "mask_replaced_top1_accuracy")
    return {key: {"mean": statistics.mean(values),
                  "std_across_mask_seeds": statistics.stdev(values) if len(values) > 1 else 0.0}
            for key in keys if (values := [run["metrics"][key] for run in runs
                                          if run["metrics"][key] is not None])}


def write_evaluation_report(path, summary):
    """Render the Markdown report from one summary.json structure."""
    from pathlib import Path

    lines = ["# Paired MLM evaluation", "", f"Split: {summary['split']}",
             f"Sample-limited run: {summary['sample_limited']}",
             f"Diagnostic-only corpus: {summary['diagnostic_only']}", "",
             "Accuracy is over selected subword tokens, including the unchanged part of 80/10/10 corruption.",
             "mask_replaced_top1_accuracy separately scores positions actually replaced by the mask token.",
             "Standard deviation is across masking seeds, not independent CPT training runs.", ""]
    for item in summary["comparisons"]:
        lines.extend([f"## Selection probability {item['masking_probability']}", "",
                      f"Masking seeds: {item['seeds']}", "",
                      "| Metric | Original mean ± SD | CPT mean ± SD |",
                      "|---|---:|---:|"])
        for metric, original in item["original"].items():
            cpt = item["cpt"][metric]
            lines.append(f"| {metric} | {original['mean']:.6f} ± {original['std_across_mask_seeds']:.6f} | "
                         f"{cpt['mean']:.6f} ± {cpt['std_across_mask_seeds']:.6f} |")
        interval = item["paired_paper_bootstrap"]
        lines.extend(["", f"Relative reduction in mean token-weighted loss: {item['relative_mean_loss_reduction_percent']:.2f}%.",
                      f"95% paired-paper bootstrap CI for original minus CPT loss: {interval['loss_reduction_95ci']}.",
                      f"95% paired-paper bootstrap CI for CPT minus original accuracy: {interval['accuracy_increase_95ci']}.",
                      "Positive differences favor CPT. Intervals are conditional on these checkpoints and masking seeds.", ""])
    lines.extend(["Do not choose an 'optimal' masking rate by comparing raw losses across different corruption tasks.",
                  "This does not measure downstream accuracy, factual reliability, or training-seed variability."])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
