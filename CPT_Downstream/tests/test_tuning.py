import tempfile
import unittest
from pathlib import Path

from hea_cpt.common import write_json
from hea_cpt.tune import completed_result, make_job, stage_jobs


class TuningPlanTests(unittest.TestCase):
    def test_promotions_require_complete_results_and_restart_original_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            study = {
                "directory": directory, "screen_steps": 2000, "screen_validation_chunks": 1024,
                "config": {"model_name_or_path": "original", "seed": 42, "validation_seed": 42},
                "baseline_parameters": dict(learning_rate=5e-5, training_mlm_probability=.15,
                                            weight_decay=.01, warmup_ratio=.06),
            }
            baseline = study["baseline_parameters"]
            better = dict(baseline, learning_rate=2e-5)
            jobs = [make_job(study, "screen-01", baseline), make_job(study, "screen-02", better)]
            write_json(Path(directory) / "screen.json", {"jobs": jobs})

            def complete(job, loss):
                write_json(Path(job["config"]["output_dir"]) / "tuning_result.json",
                           {"job": job, "validation_loss": loss})

            complete(jobs[0], .9)
            with self.assertRaisesRegex(ValueError, "Finish all screen"):
                stage_jobs(study, "refine")
            complete(jobs[1], .8)
            refinement = stage_jobs(study, "refine")
            self.assertEqual(len(refinement), 4)
            self.assertTrue(all(j["parameters"]["learning_rate"] == 2e-5 for j in refinement))
            for i, job in enumerate(refinement):
                complete(job, .7 + i * .01)
            confirmation = stage_jobs(study, "confirm")
            self.assertEqual(len(confirmation), 3)
            self.assertEqual(confirmation[0]["parameters"], baseline)
            for job in confirmation:
                self.assertEqual(job["max_steps"], -1)
                self.assertEqual(job["config"]["model_name_or_path"], "original")
                self.assertIsNone(job["config"]["validation_max_samples"])
                complete(job, .6 if job == confirmation[1] else .65)
            repetitions = stage_jobs(study, "repeat")
            self.assertEqual(len(repetitions), 4)
            self.assertEqual({j["config"]["seed"] for j in repetitions}, {43, 44})
            self.assertEqual({j["config"]["validation_seed"] for j in repetitions}, {42})
            # Promotions are frozen once created, not silently recomputed.
            self.assertEqual(stage_jobs(study, "confirm"), confirmation)
            changed = dict(jobs[0], max_steps=3000)
            with self.assertRaisesRegex(ValueError, "Changed or invalid"):
                completed_result(changed)


class TokenWeightedValidationTests(unittest.TestCase):
    def test_validation_matches_token_mean_independent_of_batching(self):
        import torch
        from transformers import TrainingArguments

        from hea_cpt.token_trainer import TokenWeightedTrainer

        class ToyMLM(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.dummy = torch.nn.Parameter(torch.zeros(()))

            def forward(self, input_ids, labels):
                logits = torch.stack((input_ids.float(), torch.zeros_like(input_ids).float()), dim=-1)
                logits = logits + self.dummy
                loss = torch.nn.functional.cross_entropy(logits.reshape(-1, 2), labels.reshape(-1))
                return {"loss": loss, "logits": logits}

        rows = [{"input_ids": [4, 4, 4], "labels": [1, -100, -100]},
                {"input_ids": [0, 0, 0], "labels": [1, 1, 1]},
                {"input_ids": [1, 1, 1], "labels": [0, 0, -100]}]
        model = ToyMLM()
        expected = model(torch.tensor([r["input_ids"] for r in rows]),
                         torch.tensor([r["labels"] for r in rows]))["loss"].item()
        with tempfile.TemporaryDirectory() as directory:
            for size in (1, 2, 3):
                trainer = TokenWeightedTrainer(model=model, eval_dataset=rows, args=TrainingArguments(
                    output_dir=directory, use_cpu=True, per_device_eval_batch_size=size,
                    prediction_loss_only=True, report_to="none", disable_tqdm=True,
                ))
                trainer.model_accepts_loss_kwargs = False
                metrics = trainer.evaluate()
                self.assertAlmostEqual(metrics["eval_loss"], expected, places=6)
                self.assertEqual(metrics["eval_labelled_tokens"], 6)
                self.assertAlmostEqual(trainer.evaluate()["eval_loss"], expected, places=6)


if __name__ == "__main__":
    unittest.main()
