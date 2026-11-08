"""Sequential, resumable, validation-only CPT hyperparameter search."""

import argparse
import csv
import math
import os
import re
import statistics
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .common import file_sha256, read_json, require_empty_directory, write_json
from .train import CPTConfig

PARAMETERS = ("learning_rate", "training_mlm_probability", "weight_decay", "warmup_ratio")
STAGES = ("screen", "refine", "confirm", "repeat")


def original_identity(model, revision):
    """Fingerprint the original pretrained weights (local dir hashes or Hub commit SHA).

    Refuses CPT exports and Trainer checkpoints; a Hub path must be pinned
    to a 40-character revision for reproducible initialization.
    """
    path = Path(model)
    if path.is_dir():
        if (path.parent / "selection.json").exists() or (path / "trainer_state.json").exists():
            raise ValueError("Choose original pretrained weights, not a CPT export/checkpoint.")
        files = sorted(p for p in path.iterdir() if p.is_file() and
                       (p.suffix in (".json", ".safetensors", ".bin", ".txt", ".model")))
        if not (path / "config.json").is_file() or not any(p.suffix in (".safetensors", ".bin") for p in files):
            raise ValueError("Local original model needs config.json and model weights.")
        return {p.name: file_sha256(p) for p in files}
    if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
        raise ValueError("Pin Hub weights with --original-revision <40-character commit>, or use local original weights.")
    return {"model": model, "commit": revision}


def make_job(study, name, parameters, full=False, seed=None):
    """Build one trial job: frozen config with the stage budget and optional seed."""
    config = dict(study["config"])
    config.update({key: parameters[key] for key in PARAMETERS if key != "training_mlm_probability"})
    config["output_dir"] = str(Path(study["directory"]) / "runs" / name)
    config["validation_max_samples"] = None if full else study["screen_validation_chunks"]
    if seed is not None:
        config["seed"] = seed
    return {"id": name, "parameters": dict(parameters), "config": config,
            "max_steps": -1 if full else study["screen_steps"]}


def initialize(args):
    """Create the frozen study plan (screening grid, config, identities); no training."""
    config = CPTConfig(**read_json(args.config))
    config.model_name_or_path = args.original_model or config.model_name_or_path
    if Path(config.model_name_or_path).is_dir():
        config.model_name_or_path = str(Path(config.model_name_or_path).resolve())
    config.revision = args.original_revision or config.revision
    config.data_dir = str(Path(config.data_dir).resolve())
    config.per_device_train_batch_size = args.batch_size
    config.per_device_eval_batch_size = args.eval_batch_size
    if args.effective_batch_size % args.batch_size:
        raise ValueError("Effective batch size must be divisible by the microbatch size.")
    config.gradient_accumulation_steps = args.effective_batch_size // args.batch_size
    config.eval_steps = args.eval_steps
    config.num_train_epochs = args.epochs
    config.validation_seed = 42
    config.token_weighted_eval = True
    config.seed = args.seed
    config.validate()
    if args.screen_steps < args.eval_steps:
        raise ValueError("Screening budget must reach at least one scheduled validation.")
    rates = args.learning_rates or sorted(set([config.learning_rate / 2.5, config.learning_rate,
                                              config.learning_rate * 2]))
    if len(set(rates)) != len(rates) or any(not math.isfinite(x) or x <= 0 for x in rates):
        raise ValueError("Learning rates must be distinct, finite and positive.")
    if config.learning_rate not in rates:
        raise ValueError("Include the config's baseline learning rate in --learning-rates.")
    manifest = Path(config.data_dir) / "manifest.json"
    prepared = read_json(manifest)
    if prepared.get("format_version") != 1 or prepared["mlm_probability"] != .15:
        raise ValueError("This protocol requires format-1 data with frozen 15% validation masking.")
    identity = original_identity(config.model_name_or_path, config.revision)
    root = require_empty_directory(args.study).resolve()
    baseline = {"learning_rate": config.learning_rate, "training_mlm_probability": .15,
                "weight_decay": config.weight_decay, "warmup_ratio": config.warmup_ratio}
    study = {"format_version": 1, "directory": str(root), "config": asdict(config),
             "manifest_sha256": file_sha256(manifest), "original_identity": identity,
             "screen_steps": args.screen_steps, "screen_validation_chunks": args.validation_chunks,
             "baseline_parameters": baseline, "learning_rates": rates,
             "selection_metric": "token_weighted_validation_mlm_loss",
             "evaluation_mask_probability": .15,
             "note": "Validation-only search; test results already inspected before this study."}
    write_json(root / "study.json", study)
    jobs = []
    for rate in rates:
        for mask in (.15, .30):
            params = dict(baseline, learning_rate=rate, training_mlm_probability=mask)
            jobs.append(make_job(study, f"screen-{len(jobs) + 1:02d}", params))
    write_json(root / "screen.json", {"jobs": jobs})
    print(f"Created {root / 'study.json'}; {len(jobs)} screening trials. No training started.")


def load_study(directory):
    """Load a study and verify manifest/original-model identity are unchanged since init."""
    root = Path(directory).resolve()
    study = read_json(root / "study.json")
    if study.get("format_version") != 1 or study["directory"] != str(root):
        raise ValueError("Unsupported or moved study; create the study in its final server location.")
    config = study["config"]
    if file_sha256(Path(config["data_dir"]) / "manifest.json") != study["manifest_sha256"]:
        raise ValueError("Prepared-data manifest changed since study initialization.")
    if original_identity(config["model_name_or_path"], config["revision"]) != study["original_identity"]:
        raise ValueError("Original model files changed since study initialization.")
    return study


def completed_result(job):
    """Return the stored tuning_result.json for a finished trial, or None."""
    path = Path(job["config"]["output_dir"]) / "tuning_result.json"
    if not path.exists():
        return None
    result = read_json(path)
    if result["job"] != job or not math.isfinite(result["validation_loss"]):
        raise ValueError(f"Changed or invalid completed trial: {job['id']}")
    return result


def stage_results(study, stage, required=False):
    """Sorted (best-first) completed results for a stage; optionally enforce completion."""
    path = Path(study["directory"]) / f"{stage}.json"
    if not path.exists():
        if required:
            raise ValueError(f"Run the {stage} stage first.")
        return []
    jobs = read_json(path)["jobs"]
    results = [result for job in jobs if (result := completed_result(job)) is not None]
    if required and len(results) != len(jobs):
        raise ValueError(f"Finish all {stage} trials before promotion ({len(results)}/{len(jobs)} complete).")
    return sorted(results, key=lambda item: (item["validation_loss"], item["job"]["id"]))


def stage_jobs(study, stage):
    """Plan (first call) and return the trial jobs of one search stage.

    Refine holds decay/warmup around the screening anchor; confirm promotes
    the top-2 learners plus the baseline to full-length runs; repeat re-runs
    the confirm winner and baseline under two further training seeds.
    """
    root = Path(study["directory"])
    path = root / f"{stage}.json"
    if path.exists():
        return read_json(path)["jobs"]
    screen = stage_results(study, "screen", required=True)
    if stage == "refine":
        anchor = screen[0]["job"]["parameters"]
        candidates = [dict(anchor, weight_decay=decay, warmup_ratio=warmup)
                      for decay in (0.0, .1) for warmup in (.02, .10)]
        jobs = [make_job(study, f"refine-{i:02d}", params) for i, params in enumerate(candidates, 1)]
        sources = [screen[0]]
    elif stage == "confirm":
        refined = stage_results(study, "refine", required=True)
        sources = sorted(screen + refined, key=lambda row: (row["validation_loss"], row["job"]["id"]))
        # Always include a fresh, comparably selected baseline in full confirmation.
        candidates = [study["baseline_parameters"]]
        for row in sources[:2]:
            if row["job"]["parameters"] not in candidates:
                candidates.append(row["job"]["parameters"])
        jobs = [make_job(study, f"confirm-{i:02d}", params, full=True)
                for i, params in enumerate(candidates, 1)]
    elif stage == "repeat":
        sources = stage_results(study, "confirm", required=True)
        candidates = [study["baseline_parameters"]]
        if sources[0]["job"]["parameters"] not in candidates:
            candidates.append(sources[0]["job"]["parameters"])
        jobs = [make_job(study, f"repeat-{i:02d}-seed{seed}", params, full=True, seed=seed)
                for i, params in enumerate(candidates, 1)
                for seed in (study["config"]["seed"] + 1, study["config"]["seed"] + 2)]
    else:
        raise ValueError("Missing screening plan; initialize a new study.")
    write_json(path, {"jobs": jobs, "promotion_evidence": sources})
    return jobs


def run_job(study, job, cpu=False):
    """Run one trial to completion (resume-safe) and record frozen tuning_result.json."""
    output = Path(job["config"]["output_dir"])
    done = completed_result(job)
    if done is not None:
        print(f"Skipping completed {job['id']}: validation loss {done['validation_loss']:.6f}", flush=True)
        return
    config_path = Path(study["directory"]) / "trial_configs" / f"{job['id']}.json"
    if config_path.exists() and read_json(config_path) != job["config"]:
        raise ValueError(f"Trial config changed: {config_path}")
    write_json(config_path, job["config"])
    command = [sys.executable, "-m", "hea_cpt.train", "--config", str(config_path),
               "--max-steps", str(job["max_steps"]), "--train-mlm-probability",
               str(job["parameters"]["training_mlm_probability"])]
    if cpu:
        command.append("--cpu")
    if output.exists() and any(output.iterdir()):
        previous = read_json(output / "run_config.json")
        if (previous["config"] != job["config"] or previous["max_steps"] != job["max_steps"]
                or previous["training_mlm_probability"] != job["parameters"]["training_mlm_probability"]
                or previous["manifest_sha256"] != study["manifest_sha256"]
                or previous["max_train_samples"] is not None or previous["max_eval_samples"] is not None):
            raise ValueError(f"Existing training run does not match frozen trial: {output}")
        # selection.json is written after the model and tokenizer export completes.
        exported = (output / "selection.json").is_file() and (output / "final" / "config.json").is_file()
        if not exported:
            checkpoints = [p for p in output.glob("checkpoint-*") if (p / "trainer_state.json").is_file()]
            if not checkpoints:
                raise ValueError(f"Interrupted before first checkpoint: move {output} aside, then rerun the stage.")
            command.extend(["--resume-from-checkpoint", "latest"])
    else:
        exported = False
    if not exported:
        print(f"\nStarting {job['id']}: {job['parameters']}", flush=True)
        subprocess.run(command, check=True)
    selection = read_json(output / "selection.json")
    metrics = read_json(output / "cpt_validation_results.json")
    state = read_json(output / "trainer_state.json")
    if (selection.get("loss_weighting") != "labelled_tokens" or not selection["final_is_best_checkpoint"]
            or state["global_step"] < state["max_steps"]):
        raise ValueError(f"Incomplete trial or incompatible checkpoint selection: {output}")
    loss = metrics["cpt_validation_loss"]
    if not math.isfinite(loss):
        raise ValueError(f"Non-finite validation loss: {output}")
    write_json(output / "tuning_result.json", {
        "job": job, "validation_loss": loss, "selection": selection,
        "model_path": str(output / "final"), "optimizer_steps": state["global_step"],
        "train_metrics": read_json(output / "train_results.json"),
    })


def report(study):
    """Write report.md/results.csv from every completed stage and seed-summary tables."""
    root = Path(study["directory"])
    rows, lines = [], ["# CPT tuning: validation-only results", "",
                      "Loss is weighted by labelled tokens, using frozen 15% validation corruption.",
                      "Screen/refine use the fixed validation subset; confirm/repeat use full validation.",
                      "Compare scores within those budgets, not between short and full training.", ""]
    for stage in STAGES:
        results = stage_results(study, stage)
        if not results:
            continue
        lines.extend([f"## {stage}", "", "| Trial | LR | Train mask | Decay | Warmup | Seed | Validation loss |",
                      "|---|---:|---:|---:|---:|---:|---:|"])
        for result in results:
            job = result["job"]
            row = {"stage": stage, "trial": job["id"], **job["parameters"],
                   "seed": job["config"]["seed"], "validation_loss": result["validation_loss"],
                   "model_path": result["model_path"]}
            rows.append(row)
            lines.append(f"| {job['id']} | {row['learning_rate']:g} | {row['training_mlm_probability']:g} | "
                         f"{row['weight_decay']:g} | {row['warmup_ratio']:g} | {row['seed']} | "
                         f"{row['validation_loss']:.6f} |")
        lines.append("")
    groups = {}
    for row in rows:
        if row["stage"] in ("confirm", "repeat"):
            key = tuple(row[p] for p in PARAMETERS)
            groups.setdefault(key, []).append(row)
    seeds = [{"parameters": dict(zip(PARAMETERS, key)), "training_seeds": [r["seed"] for r in group],
              "mean_validation_loss": statistics.mean(r["validation_loss"] for r in group),
              "std_across_training_seeds": (statistics.stdev(r["validation_loss"] for r in group)
                                            if len(group) > 1 else None)}
             for key, group in groups.items()]
    write_json(root / "training_seed_summary.json", seeds)
    write_json(root / "results.json", rows)
    if rows:
        with (root / "results.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    lines.extend(["See training_seed_summary.json for full-run seed means/SD; a single seed has no SD.",
                  "Search results do not establish a global optimum or downstream-task improvement.",
                  "Previously inspected test data are not used for promotion or checkpoint selection."])
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Results: {root / 'report.md'}", flush=True)


def positive_int(value):
    """argparse type: accept only positive integers."""
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("Must be positive.")
    return value


def main():
    """CLI: `init` freezes the plan, `run` executes a stage with a lock file, `report` summarizes."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init", help="Freeze a search plan; does not train.")
    init.add_argument("--config", required=True)
    init.add_argument("--study", required=True)
    init.add_argument("--original-model")
    init.add_argument("--original-revision")
    init.add_argument("--learning-rates", nargs="+", type=float)
    init.add_argument("--batch-size", type=positive_int, default=1)
    init.add_argument("--eval-batch-size", type=positive_int, default=1)
    init.add_argument("--effective-batch-size", type=positive_int, default=32)
    init.add_argument("--screen-steps", type=positive_int, default=2000)
    init.add_argument("--eval-steps", type=positive_int, default=500)
    init.add_argument("--validation-chunks", type=positive_int, default=1024)
    init.add_argument("--epochs", type=positive_int, default=3)
    init.add_argument("--seed", type=int, default=42)
    run = commands.add_parser("run", help="Run one stage sequentially; rerun the same command to resume.")
    run.add_argument("--study", required=True)
    run.add_argument("--stage", choices=STAGES, required=True)
    run.add_argument("--trial", help="Run just this planned trial (for inspection/smoke testing).")
    run.add_argument("--cpu", action="store_true", help="Tiny-model smoke tests only.")
    summary = commands.add_parser("report")
    summary.add_argument("--study", required=True)
    args = parser.parse_args()
    if args.action == "init":
        initialize(args)
        return
    study = load_study(args.study)
    if args.action == "run":
        lock = Path(study["directory"]) / "running.lock"
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write(f"pid={os.getpid()}\n")
        except FileExistsError:
            parser.error(f"Study is already running, or has a stale lock: {lock}. See TUNING.md.")
        try:
            jobs = stage_jobs(study, args.stage)
            if args.trial:
                jobs = [job for job in jobs if job["id"] == args.trial]
                if not jobs:
                    parser.error("Trial is not in this stage.")
            for job in jobs:
                run_job(study, job, args.cpu)
                report(study)
        finally:
            lock.unlink()
    else:
        report(study)


if __name__ == "__main__":
    main()
