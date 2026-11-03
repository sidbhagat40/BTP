import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hea_cpt.train import CPTConfig


class TrainingGuardTests(unittest.TestCase):
    def test_default_config_is_valid(self):
        CPTConfig("answerdotai/ModernBERT-base", "data", "output").validate()

    def test_nonpositive_batch_is_rejected(self):
        config = CPTConfig("answerdotai/ModernBERT-base", "data", "output", per_device_train_batch_size=0)
        with self.assertRaises(ValueError):
            config.validate()

    def test_test_split_cannot_select_training_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(json.dumps({
                "model_name_or_path": "answerdotai/ModernBERT-base",
                "data_dir": "unused", "output_dir": "unused",
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "hea_cpt.train", "--config", str(config_path), "--eval-split", "test"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("never for checkpoint selection", result.stderr)


if __name__ == "__main__":
    unittest.main()
