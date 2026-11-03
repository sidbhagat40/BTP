"""Side-by-side, exploratory cloze probes; not a scientific QA benchmark."""

import argparse
import json
from pathlib import Path

from .alloys import compare_compositions
from .common import environment_versions, file_sha256, require_empty_directory, write_json
from .evaluate import load_evaluation_model
from .evaluation import autocast_context
from .train import choose_precision


def read_probes(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen = set()
    for row in rows:
        if row["id"] in seen:
            raise ValueError("Probe IDs must be unique.")
        seen.add(row["id"])
        if row["template"].count("{answer}") != 1:
            raise ValueError("Each probe needs exactly one {answer} placeholder.")
        if len(set(row["candidates"])) != len(row["candidates"]) or len(row["candidates"]) < 2:
            raise ValueError("Need at least two distinct candidates per probe.")
        if not set(row["expected"]).issubset(row["candidates"]) or not row["expected"]:
            raise ValueError("Expected answers must be included in the candidate set.")
        if "formula_a" in row:
            comparison = compare_compositions(row["formula_a"], row["formula_b"])
            expected = "same" if comparison["same_normalized_composition"] else "different"
            if row["expected"] != [expected]:
                raise ValueError(f"Formula annotations contradict the ratio checker: {row['id']}")
    if not rows:
        raise ValueError("No probes supplied.")
    return rows


def candidate_encoding(tokenizer, template, answer, max_length):
    prefix, suffix = template.split("{answer}")
    text = prefix + answer + suffix
    encoded = tokenizer(text, return_offsets_mapping=True, return_token_type_ids=False,
                        truncation=False, verbose=False)
    if len(encoded["input_ids"]) > max_length:
        raise ValueError("Probe exceeds context limit; shorten it instead of silently truncating.")
    start, end = len(prefix), len(prefix) + len(answer)
    positions = []
    for i, (left, right) in enumerate(encoded.pop("offset_mapping")):
        if right > start and left < end:
            # Byte-BPE may include the preceding space, but not neighboring context words.
            if ((left < start and text[left:start].strip())
                    or (right > end and text[end:right].strip())):
                raise ValueError("Answer shares a token with non-whitespace context; change the template boundary.")
            positions.append(i)
    if not positions or any(encoded["input_ids"][i] in tokenizer.all_special_ids for i in positions):
        raise ValueError("Candidate must contain ordinary, maskable text tokens.")
    labels = [-100] * len(encoded["input_ids"])
    for i in positions:
        labels[i] = encoded["input_ids"][i]
        encoded["input_ids"][i] = tokenizer.mask_token_id
    encoded["labels"] = labels
    return encoded, positions


def score_candidate(model, tokenizer, template, answer, device, precision, max_length):
    import torch
    import torch.nn.functional as functional

    encoded, positions = candidate_encoding(tokenizer, template, answer, max_length)
    batch = {key: torch.tensor([value], device=device) for key, value in encoded.items()}
    with torch.inference_mode(), autocast_context(device, precision):
        logits = model(**batch).logits
    target = batch["labels"][batch["labels"] != -100]
    log_probabilities = -functional.cross_entropy(logits.float(), target, reduction="none")
    return {"candidate": answer, "target_tokens": len(positions),
            "mean_log_probability": log_probabilities.mean().item(),
            "sum_log_probability": log_probabilities.sum().item()}


def open_mask_predictions(model, tokenizer, template, device, precision, max_length, k=5):
    import torch

    text = template.replace("{answer}", tokenizer.mask_token)
    encoded = tokenizer(text, return_tensors="pt", return_token_type_ids=False, verbose=False)
    positions = encoded["input_ids"] == tokenizer.mask_token_id
    if positions.sum().item() != 1 or encoded["input_ids"].shape[1] > max_length:
        raise ValueError("Open cloze needs exactly one mask within the context limit.")
    encoded["labels"] = torch.where(positions, encoded["input_ids"], -100)
    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.inference_mode(), autocast_context(device, precision):
        logits = model(**encoded).logits
    probabilities, ids = logits[0].float().softmax(-1).topk(min(k, logits.shape[-1]))
    return [{"token_id": token, "token": tokenizer.decode([token]), "probability": probability}
            for token, probability in zip(ids.tolist(), probabilities.tolist())]


def run_probe(model, tokenizer, row, device, precision, max_length):
    scored = [score_candidate(model, tokenizer, row["template"], candidate, device, precision, max_length)
              for candidate in row["candidates"]]
    scored.sort(key=lambda item: item["mean_log_probability"], reverse=True)
    tied = [item["candidate"] for item in scored
            if abs(item["mean_log_probability"] - scored[0]["mean_log_probability"]) < 1e-6]
    return {"ranking": scored, "top_candidate": scored[0]["candidate"], "tied_top_candidates": tied,
            "unique_expected_top": len(tied) == 1 and tied[0] in row["expected"],
            "open_single_subword_top5": open_mask_predictions(
                model, tokenizer, row["template"], device, precision, max_length)}


def write_markdown(path, rows, results):
    lines = ["# Original vs CPT: exploratory diagnostics", "",
             "These are hand-authored cloze probes, not validated scientific QA or a held-out benchmark.",
             "Candidate scores are mean log probabilities with the entire answer span masked. They are not calibrated answer probabilities.",
             "Different candidate token lengths change the mask pattern; inspect target_tokens in JSON. Open-cloze outputs are single subword tokens.", ""]
    for row in rows:
        item = results[row["id"]]
        lines.extend([f"## {row['id']} — {row['category']}", "", row["template"], "",
                      f"Expected: {', '.join(row['expected'])}", "", row["explanation"], "",
                      "| Model | Candidate | Mean log probability | Target tokens |",
                      "|---|---|---:|---:|"])
        for name in ("original", "cpt"):
            for score in item[name]["ranking"]:
                candidate = score["candidate"].replace("|", "\\|")
                lines.append(f"| {name} | {candidate} | {score['mean_log_probability']:.5f} | {score['target_tokens']} |")
        lines.append("")
        for name in ("original", "cpt"):
            predictions = ", ".join(f"{x['token']!r} ({x['probability']:.3f})"
                                    for x in item[name]["open_single_subword_top5"])
            lines.append(f"**{name} open-mask top 5:** {predictions}")
        if "composition_reference" in item:
            lines.extend(["", "Deterministic composition reference: " +
                          str(item["composition_reference"]["same_normalized_composition"]),
                          "Equal atomic ratios do not establish equal microstructure or properties."])
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-model", default="answerdotai/ModernBERT-base")
    parser.add_argument("--original-revision", default="main")
    parser.add_argument("--cpt-model", required=True)
    parser.add_argument("--tokenizer", default="artifacts/hea-512/tokenizer")
    parser.add_argument("--examples", default="examples/evaluation_probes.jsonl")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--precision", choices=("auto", "fp32", "bf16", "fp16"), default="auto")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    rows = read_probes(args.examples)
    import torch
    from transformers import AutoTokenizer

    precision = choose_precision(args.precision, args.cpu)
    device = torch.device("cpu" if args.cpu else "cuda:0")
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=args.offline)
    if not tokenizer.is_fast or args.max_length < 8 or args.max_length > tokenizer.model_max_length:
        raise ValueError("Need a fast tokenizer and a valid maximum context length.")
    output = require_empty_directory(args.output_dir)
    results = {row["id"]: {"example": row} for row in rows}
    for row in rows:
        if "formula_a" in row:
            results[row["id"]]["composition_reference"] = compare_compositions(row["formula_a"], row["formula_b"])
    metadata = {"arguments": vars(args), "versions": environment_versions(),
                "examples_sha256": file_sha256(args.examples), "precision": precision,
                "warning": "Exploratory cloze preferences; no calibrated scientific truth or reliable alloy-property reasoning."}
    write_json(output / "probe_config.json", metadata)
    for name, model_path in (("original", args.original_model), ("cpt", args.cpt_model)):
        model = load_evaluation_model(model_path, tokenizer,
                                      args.original_revision if name == "original" else None,
                                      args.offline, args.max_length).to(device).eval()
        metadata[f"{name}_resolved_commit"] = getattr(model.config, "_commit_hash", None)
        for row in rows:
            results[row["id"]][name] = run_probe(model, tokenizer, row, device, precision, args.max_length)
            print(f"{name}: {row['id']} -> {results[row['id']][name]['top_candidate']}")
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    summary = {}
    for category in sorted({row["category"] for row in rows}):
        category_rows = [row for row in rows if row["category"] == category]
        summary[category] = {"probes": len(category_rows), **{
            name + "_unique_expected_top": sum(results[row["id"]][name]["unique_expected_top"]
                                                for row in category_rows)
            for name in ("original", "cpt")}}
    write_json(output / "probe_config.json", metadata)
    write_json(output / "comparison.json", {"diagnostic_only": True, "summary": summary, "examples": results})
    write_markdown(output / "comparison.md", rows, results)
    print(f"Read side-by-side results: {output / 'comparison.md'}")


if __name__ == "__main__":
    main()
