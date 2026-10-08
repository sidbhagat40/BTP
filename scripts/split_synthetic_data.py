"""
Split data/data.json (JSONL) into train / val / probe_pool by record id.

Default fractions: 80% train, 10% val, 10% probe_pool.
Stratifies by `kind` (single vs comparative) so each split keeps a similar mix.
Probe_pool ids are never used for MLM; they are reserved for later T/F, MCQ, cloze.

Usage (from repo root):
  python scripts/split_synthetic_data.py
  python scripts/split_synthetic_data.py --seed 42 --train 0.8 --val 0.1 --probe 0.1
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "data.json"
DEFAULT_OUT = REPO_ROOT / "data" / "splits"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "id" not in obj or "text" not in obj:
                raise ValueError(f"{path}:{line_no} missing id or text")
            rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stratified_split(
    rows: list[dict],
    train_frac: float,
    val_frac: float,
    probe_frac: float,
    seed: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    total = train_frac + val_frac + probe_frac
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"fractions must sum to 1.0, got {total}")

    by_kind: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_kind[str(row.get("kind", "unknown"))].append(row)

    rng = random.Random(seed)
    train, val, probe = [], [], []

    for kind, group in sorted(by_kind.items()):
        group = list(group)
        rng.shuffle(group)
        n = len(group)
        n_train = int(round(n * train_frac))
        n_val = int(round(n * val_frac))
        # remainder goes to probe so counts add up
        if n_train + n_val > n:
            n_val = max(0, n - n_train)
        n_probe = n - n_train - n_val
        train.extend(group[:n_train])
        val.extend(group[n_train : n_train + n_val])
        probe.extend(group[n_train + n_val : n_train + n_val + n_probe])
        print(f"  kind={kind!r}: n={n} -> train={n_train} val={n_val} probe={n_probe}")

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(probe)
    return train, val, probe


def summarize(name: str, rows: list[dict]) -> dict:
    kinds: dict[str, int] = defaultdict(int)
    for r in rows:
        kinds[str(r.get("kind", "unknown"))] += 1
    return {
        "name": name,
        "n": len(rows),
        "kinds": dict(kinds),
        "ids": [r["id"] for r in rows],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split synthetic HEA corpus")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--train", type=float, default=0.8)
    p.add_argument("--val", type=float, default=0.1)
    p.add_argument("--probe", type=float, default=0.1)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ids in input; refuse to split")

    print(f"Loaded {len(rows)} records from {args.input}")
    print(f"Seed={args.seed} fractions train/val/probe="
          f"{args.train}/{args.val}/{args.probe}")

    train, val, probe = stratified_split(
        rows, args.train, args.val, args.probe, args.seed
    )

    out = args.out_dir
    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "val.jsonl", val)
    write_jsonl(out / "probe_pool.jsonl", probe)

    manifest = {
        "source": str(args.input.as_posix()),
        "seed": args.seed,
        "fractions": {
            "train": args.train,
            "val": args.val,
            "probe_pool": args.probe,
        },
        "stratify_by": "kind",
        "splits": {
            "train": summarize("train", train),
            "val": summarize("val", val),
            "probe_pool": summarize("probe_pool", probe),
        },
        "notes": [
            "MLM training must use only train.jsonl (and val.jsonl for eval loss).",
            "probe_pool.jsonl must NEVER be used for MLM; reserved for later question generation.",
        ],
    }
    # compact manifest without dumping all ids twice in a huge file — keep ids
    # for leakage checks
    manifest_path = out / "split_manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # id-only lists for easy membership tests
    for name, part in [("train", train), ("val", val), ("probe_pool", probe)]:
        id_path = out / f"{name}_ids.txt"
        id_path.write_text("\n".join(r["id"] for r in part) + "\n", encoding="utf-8")

    print()
    print(f"Wrote {out / 'train.jsonl'} ({len(train)})")
    print(f"Wrote {out / 'val.jsonl'} ({len(val)})")
    print(f"Wrote {out / 'probe_pool.jsonl'} ({len(probe)})")
    print(f"Wrote {manifest_path}")
    # leakage check
    s_train, s_val, s_probe = (
        {r["id"] for r in train},
        {r["id"] for r in val},
        {r["id"] for r in probe},
    )
    assert s_train.isdisjoint(s_val)
    assert s_train.isdisjoint(s_probe)
    assert s_val.isdisjoint(s_probe)
    assert s_train | s_val | s_probe == set(ids)
    print("Leakage check: OK (disjoint ids, full coverage)")


if __name__ == "__main__":
    main()
