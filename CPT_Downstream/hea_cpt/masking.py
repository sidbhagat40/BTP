"""80/10/10 token masking, with frozen evaluation and dynamic training masks."""

import random


def replacement_vocabulary(tokenizer):
    special = set(tokenizer.all_special_ids)
    return sorted(set(tokenizer.get_vocab().values()) - special)


def mask_example(input_ids, special_tokens_mask, mask_token_id, vocabulary, probability, rng):
    if not 0 < probability < 1:
        raise ValueError("Masking probability must be between 0 and 1.")
    eligible = [i for i, special in enumerate(special_tokens_mask) if not special]
    if not eligible:
        raise ValueError("A chunk has no maskable text tokens.")
    selected = [i for i in eligible if rng.random() < probability]
    # A tiny final chunk must not create an all-ignored loss (NaN).
    if not selected:
        selected = [rng.choice(eligible)]
    masked, labels = list(input_ids), [-100] * len(input_ids)
    for index in selected:
        labels[index] = input_ids[index]
        choice = rng.random()
        if choice < 0.8:
            masked[index] = mask_token_id
        elif choice < 0.9:
            masked[index] = rng.choice(vocabulary)
        # Remaining 10% retain the original token, but still contribute to the loss.
    return masked, labels


class MLMCollator:
    """Use saved labels for evaluation; draw new masks for unlabelled training rows."""

    def __init__(self, tokenizer, probability):
        self.tokenizer = tokenizer
        self.probability = probability
        self.vocabulary = replacement_vocabulary(tokenizer)

    def __call__(self, features):
        import torch

        inputs, labels = [], []
        for feature in features:
            if "labels" in feature:
                ids, target = feature["input_ids"], feature["labels"]
            else:
                ids, target = mask_example(
                    feature["input_ids"], feature["special_tokens_mask"],
                    self.tokenizer.mask_token_id, self.vocabulary, self.probability, random,
                )
            inputs.append({"input_ids": ids, "attention_mask": feature["attention_mask"]})
            labels.append(target)
        batch = self.tokenizer.pad(inputs, padding=True, pad_to_multiple_of=8, return_tensors="pt")
        targets = torch.full_like(batch["input_ids"], -100)
        for index, target in enumerate(labels):
            start = 0 if self.tokenizer.padding_side == "right" else targets.shape[1] - len(target)
            targets[index, start:start + len(target)] = torch.tensor(target, dtype=torch.long)
        batch["labels"] = targets
        return batch
