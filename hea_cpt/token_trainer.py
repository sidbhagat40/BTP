"""Single-device Trainer with token-weighted frozen-mask validation loss."""

import math

from transformers import Trainer, TrainerCallback


class FinalEvaluationCallback(TrainerCallback):
    """Include the budget endpoint even when it is not a scheduled save step."""

    def on_step_end(self, args, state, control, **kwargs):
        """Force evaluation and checkpoint save at the final training step."""
        if state.global_step >= state.max_steps:
            control.should_evaluate = True
            control.should_save = True
        return control


class TokenWeightedTrainer(Trainer):
    """Weight each batch's mean MLM loss by its actual number of labels.

    ModernBERT's native loss is a mean over non-ignored labels. No logits are
    retained. Training loss and gradient accumulation behavior are unchanged.
    This accumulator deliberately supports only the pipeline's single device.
    """

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        """Accumulate loss × labelled-token count; refuse NaN/empty batches."""
        loss, logits, labels = super().prediction_step(
            model, inputs, prediction_loss_only, ignore_keys=ignore_keys,
        )
        count = int((inputs["labels"] != -100).sum().item())
        if loss is None or count == 0 or not math.isfinite(loss.item()):
            raise ValueError("Validation requires finite loss and at least one labelled token per batch.")
        self._validation_nll += loss.double().item() * count
        self._validation_targets += count
        return loss, logits, labels

    def evaluation_loop(self, dataloader, description, prediction_loss_only=None,
                        ignore_keys=None, metric_key_prefix="eval"):
        """Replace the per-batch mean with the exact token-weighted validation loss."""
        if self.args.world_size != 1:
            raise ValueError("TokenWeightedTrainer currently supports a single device only.")
        self._validation_nll, self._validation_targets = 0.0, 0
        output = super().evaluation_loop(
            dataloader, description, prediction_loss_only, ignore_keys, metric_key_prefix,
        )
        if not self._validation_targets:
            raise ValueError("No validation targets were evaluated.")
        output.metrics[f"{metric_key_prefix}_loss"] = self._validation_nll / self._validation_targets
        output.metrics[f"{metric_key_prefix}_labelled_tokens"] = self._validation_targets
        return output
