"""Compare original and CPT checkpoints with exact MLM metrics, without training."""

import argparse
import csv
from pathlib import Path

from .common import environment_versions, file_sha256, read_json, require_empty_directory, write_json
from .evaluation import evaluate_condition, original_chunks, paired_bootstrap, summarize_runs, write_evaluation_report
from .train import choose_precision


def load_evaluation_model(path, tokenizer, revision=None, offline=False, max_length=512):
    """Load eval-only MLM model matching our tokenizer; configure for inference.

    Enforces ModernBERT with a long-enough context window and a vocab/token
    map identical to the prepared tokenizer; disables reference compile and
    enables sparse prediction.
    """
    from transformers import AutoConfig, AutoModelForMaskedLM, AutoTokenizer

    revision = None if Path(path).is_dir() else revision
    other = AutoTokenizer.from_pretrained(path, revision=revision, local_files_only=offline)
    if tokenizer.get_vocab() != other.get_vocab() or tokenizer.special_tokens_map != other.special_tokens_map:
        raise ValueError(f"Tokenizer mismatch: {path}")
    config = AutoConfig.from_pretrained(path, revision=revision, local_files_only=offline)
    if config.model_type != "modernbert" or max_length > config.max_position_embeddings:
        raise ValueError("Need ModernBERT with a context window at least as long as the chunks.")
    config.reference_compile, config.sparse_prediction = False, True
    model = AutoModelForMaskedLM.from_pretrained(
        path, revision=revision, config=config, local_files_only=offline,
        use_safetensors=True, attn_implementation="sdpa",
    )
    return model


def main():
    """CLI entry point: run the paired original-vs-CPT evaluation and write reports.

    Guards the protocol (validation-only sweeps, positive parameters, corpus
    hash agreement), evaluates both models per probability/seed, and writes
    per-run JSON, summary.json, report.md and summary.csv.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-model", default="answerdotai/ModernBERT-base")
    parser.add_argument("--original-revision", default="main")
    parser.add_argument("--cpt-model", required=True)
    parser.add_argument("--prepared-dir", default="artifacts/hea-512")
    parser.add_argument("--raw-dir", default=".")
    parser.add_argument("--input-file", help="Optional independent general-domain or diagnostic JSONL.")
    parser.add_argument("--split", choices=("validation", "test", "diagnostic"), required=True)
    parser.add_argument("--probabilities", nargs="+", type=float, default=[0.15])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--bootstrap-iterations", type=int, default=2000)
    parser.add_argument("--max-papers", type=int, help="First N papers only: smoke test, not a full evaluation.")
    parser.add_argument("--precision", choices=("auto", "fp32", "bf16", "fp16"), default="auto")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    probabilities = sorted(set(args.probabilities))
    seeds = sorted(set(args.seeds))
    if any(not 0 < value < 1 for value in probabilities):
        parser.error("Masking probabilities must lie between 0 and 1.")
    if args.split == "test" and len(probabilities) > 1:
        parser.error("Run masking-probability sweeps on validation, not the test set.")
    if args.split == "diagnostic" and not args.input_file:
        parser.error("Diagnostic evaluation requires --input-file.")
    if args.batch_size < 1 or args.bootstrap_iterations < 1 or (args.max_papers is not None and args.max_papers < 1):
        parser.error("Batch size, bootstrap iterations and sample limits must be positive.")

    import torch
    from datasets import Dataset, Features, List, Value
    from transformers import AutoTokenizer, set_seed

    set_seed(42)
    precision = choose_precision(args.precision, args.cpu)
    device = torch.device("cpu" if args.cpu else "cuda:0")
    prepared_dir = Path(args.prepared_dir)
    manifest = read_json(prepared_dir / "manifest.json")
    source = Path(args.input_file) if args.input_file else Path(args.raw_dir) / f"{args.split}.jsonl"
    source_hash = file_sha256(source)
    if not args.input_file and source_hash != manifest["source_files"][args.split]["sha256"]:
        raise ValueError("Raw corpus differs from the corpus used for CPT preparation.")
    tokenizer = AutoTokenizer.from_pretrained(prepared_dir / "tokenizer", local_files_only=True)
    tokenizer.deprecation_warnings["Asking-to-pad-a-fast-tokenizer"] = True
    output = require_empty_directory(args.output_dir)
    metadata = {
        "arguments": vars(args), "source_sha256": source_hash,
        "prepared_manifest_sha256": file_sha256(prepared_dir / "manifest.json"),
        "versions": environment_versions(), "precision": precision,
        "device": "CPU" if args.cpu else torch.cuda.get_device_name(0),
        "sample_limited": args.max_papers is not None,
        "corruption": "80/10/10 replacements; at least one target per chunk; 15% is the primary protocol",
        "warning": "Changing evaluation masking probability is a sensitivity analysis, not tuning the CPT training mask rate.",
    }
    write_json(output / "evaluation_config.json", metadata)
    features = Features({"paper_id": Value("int32"), "source_line": Value("int32"),
                         "chunk_id": Value("int32"), "input_ids": List(Value("int32")),
                         "attention_mask": List(Value("int8")), "special_tokens_mask": List(Value("int8"))})
    chunks = Dataset.from_generator(original_chunks, gen_kwargs={
        "path": str(source), "tokenizer": tokenizer, "max_length": manifest["max_length"],
        "source_sha256": source_hash, "max_papers": args.max_papers,
    }, features=features, cache_dir=str(output / "chunk_cache"))
    if not len(chunks):
        raise ValueError("No maskable chunks in input.")
    # Keep a source-line mapping without duplicating full copyrighted paper text.
    mapping = {}
    for row in chunks.select_columns(["paper_id", "source_line"]):
        mapping[str(row["paper_id"])] = row["source_line"]
    write_json(output / "paper_mapping.json", {"source_file": str(source), "paper_id_to_line": mapping})
    runs = {"original": {}, "cpt": {}}
    for name, model_path in (("original", args.original_model), ("cpt", args.cpt_model)):
        model = load_evaluation_model(model_path, tokenizer,
                                      args.original_revision if name == "original" else None,
                                      args.offline, manifest["max_length"]).to(device)
        metadata[f"{name}_resolved_commit"] = getattr(model.config, "_commit_hash", None)
        write_json(output / "evaluation_config.json", metadata)
        for probability in probabilities:
            condition_runs = []
            for seed in seeds:
                result = evaluate_condition(model, tokenizer, chunks, probability, seed, args.split,
                                            device, precision, args.batch_size)
                write_json(output / f"{name}_p{probability:g}_seed{seed}.json", result)
                condition_runs.append(result)
            runs[name][probability] = condition_runs
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    summary = {"split": args.split, "source_sha256": source_hash,
               "sample_limited": args.max_papers is not None,
               "diagnostic_only": args.split == "diagnostic", "comparisons": []}
    csv_rows = []
    for probability in probabilities:
        original, cpt = runs["original"][probability], runs["cpt"][probability]
        a, b = summarize_runs(original), summarize_runs(cpt)
        a_loss, b_loss = a["token_weighted_mlm_loss"]["mean"], b["token_weighted_mlm_loss"]["mean"]
        comparison = {"masking_probability": probability, "seeds": seeds, "original": a, "cpt": b,
                      "mean_loss_reduction": a_loss - b_loss,
                      "relative_mean_loss_reduction_percent": 100 * (a_loss - b_loss) / a_loss,
                      "mean_accuracy_increase": b["masked_token_accuracy"]["mean"] - a["masked_token_accuracy"]["mean"],
                      "paired_paper_bootstrap": paired_bootstrap(original, cpt, args.bootstrap_iterations)}
        summary["comparisons"].append(comparison)
        for name, values in (("original", a), ("cpt", b)):
            for metric, scores in values.items():
                csv_rows.append({"probability": probability, "model": name, "metric": metric, **scores})
    write_json(output / "summary.json", summary)
    write_evaluation_report(output / "report.md", summary)
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Evaluation complete: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
