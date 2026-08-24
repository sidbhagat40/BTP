"""
Hands-on playground for ModernBERT-large.

ModernBERT is an *encoder* (masked LM), not ChatGPT. It does not freely
generate answers. This script shows the three ways you will actually use it:

  1. Fill-mask / cloze     — put [MASK] in a sentence, read top tokens
  2. Score candidates      — rank MCQ / T-F options by model likelihood
  3. Embeddings            — cosine similarity between question and passages

Usage (from repo root):
  python scripts/tinker_modernbert.py
  python scripts/tinker_modernbert.py --base          # smaller, if large OOM
  python scripts/tinker_modernbert.py --demo          # run examples and exit
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Sequence

import torch
from transformers import AutoModel, AutoModelForMaskedLM, AutoTokenizer, pipeline


HUB_LARGE = "answerdotai/ModernBERT-large"
HUB_BASE = "answerdotai/ModernBERT-base"
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_LARGE = REPO_ROOT / "models" / "modernbert-large"
LOCAL_BASE = REPO_ROOT / "models" / "modernbert-base"


def local_dir_is_complete(path: Path) -> bool:
    return (path / "config.json").exists() and (
        (path / "model.safetensors").exists() or (path / "pytorch_model.bin").exists()
    )


def resolve_model(prefer_base: bool, override: str | None, allow_hub: bool) -> str:
    if override:
        return override
    local = LOCAL_BASE if prefer_base else LOCAL_LARGE
    if local_dir_is_complete(local):
        print(f"Using repo weights: {local}")
        return str(local)
    if allow_hub:
        hub = HUB_BASE if prefer_base else HUB_LARGE
        print(f"Using Hugging Face id (cache): {hub}")
        return hub
    raise FileNotFoundError(
        f"Repo model not found at {local}. Run: python scripts/download_modernbert.py"
        + (" --base" if prefer_base else "")
    )


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_dtype(device: str) -> torch.dtype:
    if device == "cuda" and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if device in {"cuda", "mps"}:
        return torch.float16
    return torch.float32


class ModernBertPlayground:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.device = pick_device()
        self.dtype = pick_dtype(self.device)
        print(f"Loading {model_id}")
        print(f"  device={self.device}  dtype={self.dtype}")
        from_local = Path(model_id).exists()
        if from_local:
            print("  source: repo folder (offline, not Hugging Face cache)")
        else:
            print("  source: Hugging Face Hub / cache")

        load_kw = {"local_files_only": True} if from_local else {}
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, **load_kw)
        self.mlm = AutoModelForMaskedLM.from_pretrained(
            model_id,
            dtype=self.dtype,
            **load_kw,
        ).to(self.device)
        self.mlm.eval()

        # Encoder without MLM head — for embeddings
        self.encoder = AutoModel.from_pretrained(
            model_id,
            dtype=self.dtype,
            **load_kw,
        ).to(self.device)
        self.encoder.eval()

        device_index = 0 if self.device == "cuda" else -1
        self.fill = pipeline(
            "fill-mask",
            model=self.mlm,
            tokenizer=self.tokenizer,
            device=device_index,
            dtype=self.dtype,
        )

        n_params = sum(p.numel() for p in self.mlm.parameters())
        print(f"  parameters: {n_params / 1e6:.1f}M")
        print(f"  mask token: {self.tokenizer.mask_token}")
        print(f"  max position embeddings: {self.mlm.config.max_position_embeddings}")
        print()

    def fill_mask(self, text: str, top_k: int = 8) -> None:
        if self.tokenizer.mask_token not in text:
            print(f"Put {self.tokenizer.mask_token} somewhere in the sentence.")
            return
        hits = self.fill(text, top_k=top_k)
        if isinstance(hits[0], list):
            # multiple masks → list per mask
            for i, group in enumerate(hits, start=1):
                print(f"  mask {i}:")
                for h in group:
                    print(f"    {h['score']:.4f}  {h['token_str']!r}  ->  {h['sequence']}")
        else:
            for h in hits:
                print(f"  {h['score']:.4f}  {h['token_str']!r}  ->  {h['sequence']}")

    @torch.no_grad()
    def sequence_nll(self, text: str) -> float:
        """Mean token NLL via batched MLM pseudo-likelihood (one mask per content token)."""
        enc = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        input_ids = enc["input_ids"].to(self.device)
        attn = enc["attention_mask"].to(self.device)
        ids = input_ids[0]
        special = set(self.tokenizer.all_special_ids)
        positions = [
            i
            for i, tok in enumerate(ids.tolist())
            if tok not in special and attn[0, i] == 1
        ]
        if not positions:
            return float("inf")

        b = len(positions)
        masked = input_ids.repeat(b, 1)
        attn_b = attn.repeat(b, 1)
        for row, pos in enumerate(positions):
            masked[row, pos] = self.tokenizer.mask_token_id
        logits = self.mlm(input_ids=masked, attention_mask=attn_b).logits
        losses = []
        for row, pos in enumerate(positions):
            logp = torch.log_softmax(logits[row, pos].float(), dim=-1)
            losses.append(-logp[ids[pos]].item())
        return sum(losses) / len(losses)

    def rank_options(self, stem: str, options: Sequence[str]) -> None:
        """Lower NLL = model likes that full sentence more."""
        scored = []
        for opt in options:
            sentence = f"{stem.rstrip()} {opt}".strip()
            nll = self.sequence_nll(sentence)
            scored.append((nll, math.exp(-nll), opt, sentence))
        scored.sort(key=lambda x: x[0])
        print("  ranked (best first; lower NLL is better):")
        for nll, lik, opt, _ in scored:
            print(f"    nll={nll:.3f}  ~p/token={lik:.4f}  {opt}")

    def true_false(self, statement: str, negation: str | None = None) -> None:
        nll_t = self.sequence_nll(statement)
        print(f"  statement NLL: {nll_t:.3f}  ({statement})")
        if negation:
            nll_f = self.sequence_nll(negation)
            print(f"  negation  NLL: {nll_f:.3f}  ({negation})")
            pick = "TRUE-leaning" if nll_t < nll_f else "FALSE-leaning"
            print(f"  model prefers: {pick}")
        else:
            print("  (pass a negated sentence to compare)")

    @torch.no_grad()
    def embed(self, text: str) -> torch.Tensor:
        enc = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        enc = {k: v.to(self.device) for k, v in enc.items()}
        hidden = self.encoder(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return torch.nn.functional.normalize(pooled.float(), dim=-1)[0]

    def similarity(self, query: str, passages: Sequence[str]) -> None:
        q = self.embed(query)
        rows = []
        for p in passages:
            s = torch.dot(q, self.embed(p)).item()
            rows.append((s, p))
        rows.sort(reverse=True)
        print("  cosine similarity (query vs passage):")
        for s, p in rows:
            preview = p if len(p) < 90 else p[:87] + "..."
            print(f"    {s:.4f}  {preview}")


def run_demo(pg: ModernBertPlayground) -> None:
    print("=" * 60)
    print("DEMO 1 — fill-mask (general language)")
    print("=" * 60)
    pg.fill_mask("The capital of France is [MASK].")

    print()
    print("=" * 60)
    print("DEMO 2 — fill-mask (refractory HEA jargon)")
    print("=" * 60)
    pg.fill_mask(
        "In refractory high-entropy alloys, yield strength often increases as grain size [MASK]."
    )
    print()
    pg.fill_mask(
        "Spark plasma [MASK] is a common powder-metallurgy route for consolidating HEAs."
    )

    print()
    print("=" * 60)
    print("DEMO 3 — MCQ-style ranking (not free-form generation)")
    print("=" * 60)
    pg.rank_options(
        "According to Hall-Petch-type reasoning, finer grains typically",
        [
            "increase yield strength and hardness.",
            "decrease yield strength and hardness.",
            "have no effect on mechanical strength.",
            "always increase ductility and toughness together.",
        ],
    )

    print()
    print("=" * 60)
    print("DEMO 4 — True / False via statement vs negation")
    print("=" * 60)
    pg.true_false(
        "Coarser grains generally lower yield strength but can improve strain to failure.",
        "Coarser grains generally raise yield strength and always reduce strain to failure.",
    )

    print()
    print("=" * 60)
    print("DEMO 5 — retrieval: question vs short passages")
    print("=" * 60)
    pg.similarity(
        "How does grain size affect hardness in spark plasma sintered NbTiTa?",
        [
            "Finer equiaxed grains after SPS raise hardness via a Hall-Petch-type effect.",
            "Directed energy deposition of MoHfZrWTi produces columnar grains and residual stress.",
            "The capital of France is Paris and it has a temperate climate.",
        ],
    )
    print()


def repl(pg: ModernBertPlayground) -> None:
    mask = pg.tokenizer.mask_token
    print("Interactive mode. Commands:")
    print(f"  mask   <sentence with {mask}>")
    print("  mcq    (then stem, then options, empty line to score)")
    print("  tf     <statement>")
    print("  tf2    (statement, then negation)")
    print("  sim    (query, then passages, empty line to score)")
    print("  demo")
    print("  quit")
    print()
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        cmd, *rest = line.split(maxsplit=1)
        cmd = cmd.lower()
        arg = rest[0] if rest else ""

        if cmd in {"quit", "exit", "q"}:
            break
        if cmd == "demo":
            run_demo(pg)
        elif cmd == "mask":
            pg.fill_mask(arg or input("sentence: "))
        elif cmd == "mcq":
            stem = input("stem / question: ").strip()
            opts = []
            print("options (empty line to finish):")
            while True:
                o = input("  - ").strip()
                if not o:
                    break
                opts.append(o)
            if stem and len(opts) >= 2:
                pg.rank_options(stem, opts)
        elif cmd == "tf":
            pg.true_false(arg or input("statement: "))
        elif cmd == "tf2":
            pg.true_false(input("statement: ").strip(), input("negation: ").strip())
        elif cmd == "sim":
            q = input("question: ").strip()
            passages = []
            print("passages (empty line to finish):")
            while True:
                p = input("  - ").strip()
                if not p:
                    break
                passages.append(p)
            if q and passages:
                pg.similarity(q, passages)
        else:
            # convenience: if they pasted a [MASK] sentence, treat as fill-mask
            if pg.tokenizer.mask_token in line:
                pg.fill_mask(line)
            else:
                print("unknown command; try mask / mcq / tf / sim / demo / quit")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tinker with ModernBERT")
    p.add_argument("--base", action="store_true", help="use ModernBERT-base instead of large")
    p.add_argument("--demo", action="store_true", help="run demos and exit")
    p.add_argument("--model", type=str, default=None, help="override path or Hugging Face id")
    p.add_argument(
        "--hub",
        action="store_true",
        help="allow Hugging Face cache if the repo models/ folder is missing",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    model_id = resolve_model(
        prefer_base=args.base,
        override=args.model,
        allow_hub=args.hub,
    )
    pg = ModernBertPlayground(model_id)
    if args.demo:
        run_demo(pg)
        return 0
    run_demo(pg)
    repl(pg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
