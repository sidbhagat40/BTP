"""Offline integration tests using a randomly initialized tiny ModernBERT, not Hub weights."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEPENDENCIES = all(importlib.util.find_spec(name) is not None
                   for name in ("torch", "transformers", "datasets", "accelerate"))


@unittest.skipUnless(DEPENDENCIES, "Install requirements.txt for the tiny-model integration test.")
class PipelineTests(unittest.TestCase):
    def test_chunking_training_evaluation_and_resume(self):
        import torch
        from datasets import load_from_disk
        from tokenizers import Tokenizer
        from tokenizers.models import WordLevel
        from tokenizers.pre_tokenizers import Whitespace
        from tokenizers.processors import TemplateProcessing
        from transformers import ModernBertConfig, ModernBertForMaskedLM, PreTrainedTokenizerFast

        from hea_cpt.common import read_json, write_json
        from hea_cpt.masking import MLMCollator
        from hea_cpt.prepare import prepare_dataset

        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_dir, raw, prepared = root / "tiny-model", root / "raw", root / "prepared"
            model_dir.mkdir()
            raw.mkdir()
            tokens = ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]", "Title", ":", "train",
                      "validation", "test", "alloy", "strength", "AlCoCrFeNi", "MPa", "end"]
            backend = Tokenizer(WordLevel({token: index for index, token in enumerate(tokens)}, unk_token="[UNK]"))
            backend.pre_tokenizer = Whitespace()
            backend.post_processor = TemplateProcessing(
                single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)],
            )
            tokenizer = PreTrainedTokenizerFast(
                tokenizer_object=backend, unk_token="[UNK]", cls_token="[CLS]", sep_token="[SEP]",
                pad_token="[PAD]", mask_token="[MASK]", model_max_length=128,
            )
            tokenizer.save_pretrained(model_dir)
            model = ModernBertForMaskedLM(ModernBertConfig(
                vocab_size=len(tokens), hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                num_attention_heads=4, max_position_embeddings=128, local_attention=16,
                pad_token_id=3, cls_token_id=1, sep_token_id=2, bos_token_id=1, eos_token_id=2,
                reference_compile=False,
            ))
            model.save_pretrained(model_dir)
            original = {}
            for split in ("train", "validation", "test"):
                text = f"Title: {split}\n" + "AlCoCrFeNi alloy strength MPa " * 40 + "end"
                original[split] = tokenizer(text, add_special_tokens=False, verbose=False)["input_ids"]
                (raw / f"{split}.jsonl").write_text(json.dumps({"text": text}) + "\n", encoding="utf-8")
            prepare_dataset(raw, prepared, str(model_dir), max_length=32)
            data = load_from_disk(str(prepared / "dataset"))
            reconstructed = [token for row in data["train"]
                             for token, special in zip(row["input_ids"], row["special_tokens_mask"]) if not special]
            self.assertEqual(reconstructed, original["train"])  # No truncated paper tail or dropped remainder.
            self.assertLess(len(data["train"][-1]["input_ids"]), 32)
            for row in data["train"]:
                self.assertEqual(row["input_ids"][0], 1)
                self.assertEqual(row["input_ids"][-1], 2)
            collator = MLMCollator(tokenizer, 0.15)
            rows = [data["validation"][0], data["validation"][-1]]
            first, second = collator(rows), collator(rows)
            self.assertTrue(torch.equal(first["input_ids"], second["input_ids"]))
            self.assertTrue(torch.equal(first["labels"], second["labels"]))
            self.assertTrue(torch.all(first["labels"][first["attention_mask"] == 0] == -100))
            self.assertTrue(torch.isfinite(model(**first).loss))

            config = {
                "model_name_or_path": str(model_dir), "data_dir": str(prepared),
                "output_dir": str(root / "training"), "per_device_train_batch_size": 2,
                "per_device_eval_batch_size": 2, "gradient_accumulation_steps": 2,
                "eval_steps": 1, "logging_steps": 1, "gradient_checkpointing": True,
                "validation_max_samples": None,
            }
            config_path = root / "config.json"
            write_json(config_path, config)
            env = dict(os.environ, OMP_NUM_THREADS="1", TOKENIZERS_PARALLELISM="false",
                       HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")

            def run(*extra):
                result = subprocess.run(
                    [sys.executable, "-m", "hea_cpt.train", "--config", str(config_path), "--cpu", *extra],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)

            run("--max-steps", "2")
            output = root / "training"
            self.assertTrue((output / "final" / "model.safetensors").is_file())
            self.assertIsNotNone(read_json(output / "selection.json")["best_checkpoint"])
            self.assertTrue((output / "baseline_validation_results.json").is_file())
            run("--max-steps", "3", "--resume-from-checkpoint", "latest")
            self.assertEqual(read_json(output / "trainer_state.json")["global_step"], 3)
            self.assertIn("checkpoint-", read_json(output / "resume_config.json")["model_loaded"])
            run("--eval-only", "--eval-split", "test", "--model-path", str(output / "final"),
                "--output-dir", str(root / "test-results"))
            self.assertIn("test_loss", read_json(root / "test-results" / "test_results.json"))
            run("--max-steps", "1", "--train-mlm-probability", ".30",
                "--output-dir", str(root / "mask-ablation"))
            ablation = read_json(root / "mask-ablation" / "run_config.json")
            self.assertEqual(ablation["training_mlm_probability"], .30)
            self.assertEqual(ablation["prepared_data"]["mlm_probability"], .15)
            self.assertTrue((root / "mask-ablation" / "cpt_validation_results.json").is_file())

            # Exercise the actual tuning subprocess path, its endpoint checkpoint,
            # and safe reruns on tiny offline original weights.
            study = root / "tuning"

            def tune(*extra):
                result = subprocess.run(
                    [sys.executable, "-m", "hea_cpt.tune", *extra], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", env=env, timeout=180,
                )
                self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
                return result.stdout

            tune("init", "--config", str(config_path), "--study", str(study),
                 "--screen-steps", "3", "--eval-steps", "2", "--effective-batch-size", "2")
            tune("run", "--study", str(study), "--stage", "screen", "--trial", "screen-01", "--cpu")
            trial = study / "runs" / "screen-01"
            result = read_json(trial / "tuning_result.json")
            self.assertEqual(result["optimizer_steps"], 3)
            self.assertEqual(result["selection"]["loss_weighting"], "labelled_tokens")
            self.assertTrue((trial / "checkpoint-3" / "trainer_state.json").is_file())
            self.assertIn("Skipping completed", tune("run", "--study", str(study), "--stage", "screen",
                                                     "--trial", "screen-01", "--cpu"))
            # Simulate interruption during the first evaluation, before any update.
            pending = read_json(study / "screen.json")["jobs"][1]
            interrupted = Path(pending["config"]["output_dir"])
            interrupted.mkdir(parents=True)
            previous = read_json(trial / "run_config.json")
            previous["config"] = pending["config"]
            previous["training_mlm_probability"] = .30
            write_json(interrupted / "run_config.json", previous)
            failed = subprocess.run(
                [sys.executable, "-m", "hea_cpt.tune", "run", "--study", str(study),
                 "--stage", "screen", "--trial", "screen-02", "--cpu"],
                capture_output=True, text=True, env=env, timeout=30,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Interrupted before first checkpoint", failed.stderr)


if __name__ == "__main__":
    unittest.main()
