import json
import random
import tempfile
import unittest
from pathlib import Path

from hea_cpt.audit import audit_corpus, clean_text, iter_documents
from hea_cpt.common import require_empty_directory
from hea_cpt.masking import mask_example


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        for split in ("train", "validation", "test"):
            self.write(split, f"Title: {split} paper\n\nAlCoCrFeNi at 900 °C; σ = 100 MPa.")

    def write(self, split, text):
        (self.root / f"{split}.jsonl").write_text(json.dumps({"text": text}) + "\n", encoding="utf-8")

    def test_valid_corpus_and_chemical_notation(self):
        report = audit_corpus(self.root)
        self.assertTrue(report["passed"])
        self.assertEqual(report["splits"]["train"]["documents"], 1)
        text = list(iter_documents(self.root / "train.jsonl"))[0][1]
        self.assertIn("AlCoCrFeNi", clean_text(text))
        self.assertIn("900 °C; σ", clean_text(text))

    def test_exact_leakage_fails(self):
        self.write("test", next(iter_documents(self.root / "train.jsonl"))[1].upper())
        report = audit_corpus(self.root)
        self.assertFalse(report["passed"])
        self.assertEqual(len(report["exact_duplicate_groups"]), 1)

    def test_title_leakage_with_different_bodies_fails(self):
        self.write("test", "Title: train paper\n\nDifferent abstract from the same paper.")
        self.assertEqual(len(audit_corpus(self.root)["cross_split_title_groups"]), 1)

    def test_empty_and_invalid_documents_fail(self):
        self.write("validation", "  ")
        self.assertFalse(audit_corpus(self.root)["passed"])
        (self.root / "test.jsonl").write_text("not json\n", encoding="utf-8")
        self.assertFalse(audit_corpus(self.root)["passed"])

    def test_output_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            require_empty_directory(self.root)


class MaskingTests(unittest.TestCase):
    def test_frozen_masking_is_repeatable(self):
        ids, special = [1] + list(range(5, 105)) + [2], [1] + [0] * 100 + [1]
        arguments = (ids, special, 4, list(range(5, 105)), 0.15)
        first = mask_example(*arguments, random.Random("fixed"))
        self.assertEqual(first, mask_example(*arguments, random.Random("fixed")))
        self.assertNotEqual(first, mask_example(*arguments, random.Random("other")))
        self.assertEqual(first[1][0], -100)
        self.assertEqual(first[1][-1], -100)
        self.assertEqual(ids[1], 5)  # The original sequence was not mutated.

    def test_tiny_chunks_have_a_target(self):
        masked, labels = mask_example([1, 5, 2], [1, 0, 1], 4, [5, 6], 0.00001, random.Random(42))
        self.assertEqual(labels, [-100, 5, -100])
        self.assertEqual(masked[0], 1)
        self.assertEqual(masked[-1], 2)

    def test_no_maskable_tokens_fails(self):
        with self.assertRaises(ValueError):
            mask_example([1, 2], [1, 1], 4, [5], 0.15, random.Random(42))


if __name__ == "__main__":
    unittest.main()
