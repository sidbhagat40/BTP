import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hea_cpt.alloys import compare_compositions, normalized_composition
from hea_cpt.evaluation import metrics_from_papers
from hea_cpt.probes import read_probes

ROOT = Path(__file__).resolve().parents[1]
HAS_DEPENDENCIES = all(importlib.util.find_spec(name) for name in ("torch", "transformers", "datasets", "numpy"))


class ReferenceTests(unittest.TestCase):
    def test_composition_equivalence_and_limits(self):
        for a, b in (("CoCrFeMnNi", "NiMnFeCrCo"), ("Fe50Ni50", "FeNi"),
                     ("Al0.5CoCrFeNi", "AlCo2Cr2Fe2Ni2")):
            self.assertTrue(compare_compositions(a, b)["same_normalized_composition"])
        self.assertFalse(compare_compositions("AlCoCrFeNi", "Al0.5CoCrFeNi")["same_normalized_composition"])
        for invalid in ("XYZ", "Fe(NiCo)", "Fe50wt%Ni50", "Fe0Ni", "", "feNi"):
            with self.assertRaises(ValueError):
                normalized_composition(invalid)

    def test_all_probe_annotations_are_valid(self):
        rows = read_probes(ROOT / "examples/evaluation_probes.jsonl")
        self.assertGreaterEqual(len(rows), 30)
        self.assertTrue(any(row["category"] == "General English" for row in rows))

    def test_token_weighting_is_not_chunk_or_paper_weighting(self):
        rows = [
            dict(nll_sum=4., targets=1, top1_correct=1, top5_correct=1,
                 mask_token_targets=1, mask_token_correct=1, content_tokens=10, chunks=1),
            dict(nll_sum=3., targets=3, top1_correct=2, top5_correct=3,
                 mask_token_targets=2, mask_token_correct=1, content_tokens=20, chunks=2),
        ]
        metrics = metrics_from_papers(rows)
        self.assertEqual(metrics["token_weighted_mlm_loss"], 1.75)
        self.assertEqual(metrics["paper_macro_mlm_loss"], 2.5)
        self.assertEqual(metrics["masked_token_accuracy"], .75)
        self.assertEqual(metrics["masked_token_top5_accuracy"], 1.)
        self.assertAlmostEqual(metrics["mask_replaced_top1_accuracy"], 2 / 3)


@unittest.skipUnless(HAS_DEPENDENCIES, "Install requirements.txt for evaluation integration tests.")
class EvaluationIntegrationTests(unittest.TestCase):
    def test_exact_metrics_and_all_probes_offline(self):
        import torch
        from tokenizers import Tokenizer
        from tokenizers.models import WordLevel
        from tokenizers.pre_tokenizers import Whitespace
        from tokenizers.processors import TemplateProcessing
        from transformers import ModernBertConfig, ModernBertForMaskedLM, PreTrainedTokenizerFast

        from hea_cpt.common import file_sha256, read_json, write_json
        from hea_cpt.evaluate import load_evaluation_model
        from hea_cpt.evaluation import EvaluationCollator, original_chunks, paired_bootstrap
        from hea_cpt.probes import candidate_encoding

        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_dir, prepared, raw = root / "model", root / "prepared", root / "raw"
            raw.mkdir()
            prepared.mkdir()
            probes = read_probes(ROOT / "examples/evaluation_probes.jsonl")
            text = "Title: sample alloy strength nickel material end "
            examples = [row["template"].replace("{answer}", candidate)
                        for row in probes for candidate in row["candidates"]] + [text]
            pretokenizer = Whitespace()
            special = ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"]
            vocabulary = special + sorted({word for example in examples
                                            for word, _ in pretokenizer.pre_tokenize_str(example)} - set(special))
            backend = Tokenizer(WordLevel({word: i for i, word in enumerate(vocabulary)}, unk_token="[UNK]"))
            backend.pre_tokenizer = pretokenizer
            backend.post_processor = TemplateProcessing(single="[CLS] $A [SEP]",
                                                         special_tokens=[("[CLS]", 1), ("[SEP]", 2)])
            tokenizer = PreTrainedTokenizerFast(tokenizer_object=backend, unk_token="[UNK]", cls_token="[CLS]",
                                                sep_token="[SEP]", pad_token="[PAD]", mask_token="[MASK]",
                                                model_max_length=128)
            tokenizer.save_pretrained(model_dir)
            tokenizer.save_pretrained(prepared / "tokenizer")
            config = ModernBertConfig(vocab_size=len(vocabulary), hidden_size=32, intermediate_size=64,
                                      num_hidden_layers=2, num_attention_heads=4, local_attention=16,
                                      max_position_embeddings=128, pad_token_id=3, cls_token_id=1,
                                      sep_token_id=2, bos_token_id=1, eos_token_id=2, reference_compile=False)
            ModernBertForMaskedLM(config).save_pretrained(model_dir)
            source = raw / "validation.jsonl"
            source.write_text("\n".join(json.dumps({"text": text * repeat}) for repeat in (12, 2)) + "\n",
                              encoding="utf-8")
            write_json(prepared / "manifest.json", {"max_length": 32,
                       "source_files": {"validation": {"sha256": file_sha256(source)}}})
            chunks = list(original_chunks(source, tokenizer, 32, file_sha256(source)))
            reconstructed = [token for row in chunks if row["paper_id"] == 0
                             for token, flag in zip(row["input_ids"], row["special_tokens_mask"]) if not flag]
            self.assertEqual(reconstructed, tokenizer(text * 12, add_special_tokens=False, verbose=False)["input_ids"])
            # Verify seed 42 at 15% matches existing preparation's exact corruption policy.
            from hea_cpt.prepare import generate_chunks
            frozen = list(generate_chunks(source, tokenizer, 32, "validation", 42, .15, file_sha256(source)))
            batch, metadata = EvaluationCollator(tokenizer, .15, 42, "validation")([chunks[0]])
            self.assertEqual(batch["input_ids"][0, :len(frozen[0]["input_ids"])].tolist(), frozen[0]["input_ids"])
            self.assertEqual(batch["labels"][0, :len(frozen[0]["labels"])].tolist(), frozen[0]["labels"])
            self.assertEqual(metadata[0]["paper_id"], 0)
            # Candidate masking hides all answer subwords and leaves context unlabelled.
            encoded, positions = candidate_encoding(tokenizer, "The element is {answer}.", "nickel", 128)
            self.assertTrue(all(encoded["input_ids"][i] == 4 for i in positions))
            self.assertEqual(sum(label != -100 for label in encoded["labels"]), len(positions))
            with self.assertRaises(ValueError):
                candidate_encoding(tokenizer, "{answer} " + text * 20, "nickel", 8)

            env = dict(os.environ, OMP_NUM_THREADS="1", TOKENIZERS_PARALLELISM="false",
                       HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")

            def run(module, *arguments, success=True):
                result = subprocess.run([sys.executable, "-m", module, *map(str, arguments)], cwd=ROOT,
                                        env=env, capture_output=True, text=True, encoding="utf-8",
                                        errors="replace", timeout=180)
                if success:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                return result

            evaluation_dir = root / "evaluation"
            run("hea_cpt.evaluate", "--original-model", model_dir, "--cpt-model", model_dir,
                "--prepared-dir", prepared, "--raw-dir", raw, "--split", "validation",
                "--probabilities", ".1", ".15", "--seeds", "42", "43", "--cpu", "--offline",
                "--bootstrap-iterations", "100", "--output-dir", evaluation_dir)
            summary = read_json(evaluation_dir / "summary.json")
            self.assertEqual(len(summary["comparisons"]), 2)
            for item in summary["comparisons"]:
                self.assertEqual(item["mean_loss_reduction"], 0.)
                self.assertEqual(item["paired_paper_bootstrap"]["loss_reduction_95ci"], [0., 0.])
            a = read_json(evaluation_dir / "original_p0.15_seed42.json")
            b = read_json(evaluation_dir / "original_p0.15_seed43.json")
            self.assertNotEqual(a["corruption_sha256"], b["corruption_sha256"])
            self.assertEqual(a["metrics"]["papers"], 2)
            self.assertEqual(a["metrics"]["chunks"], len(chunks))
            self.assertTrue((evaluation_dir / "report.md").is_file())
            with self.assertRaises(ValueError):
                paired_bootstrap([a], [b], 100)
            result = run("hea_cpt.evaluate", "--cpt-model", model_dir, "--split", "test",
                         "--probabilities", ".1", ".3", "--output-dir", root / "forbidden", success=False)
            self.assertIn("sweeps on validation", result.stderr)

            probe_dir = root / "probes"
            run("hea_cpt.probes", "--original-model", model_dir, "--cpt-model", model_dir,
                "--tokenizer", prepared / "tokenizer", "--max-length", "128", "--cpu", "--offline",
                "--output-dir", probe_dir)
            comparison = read_json(probe_dir / "comparison.json")
            self.assertEqual(len(comparison["examples"]), len(probes))
            for row in comparison["examples"].values():
                self.assertEqual(row["original"], row["cpt"])
                for score in row["original"]["ranking"]:
                    self.assertGreater(score["target_tokens"], 0)
                    self.assertLessEqual(score["mean_log_probability"], 0)
            self.assertTrue((probe_dir / "comparison.md").is_file())


if __name__ == "__main__":
    unittest.main()
