"""Validate JSONL documents and check exact-text/title split leakage.

Run without any third-party packages: python -m hea_cpt.audit --data-dir .
"""

import argparse
import hashlib
import json
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

from .common import file_sha256, write_json

SPLITS = ("train", "validation", "test")


def clean_text(text):
    """Normalize Unicode and line endings while preserving formulas, case and units."""
    # Preserve chemical formulas, case, Unicode symbols, units and section boundaries.
    return unicodedata.normalize("NFC", text).replace("\x00", "").replace("\r\n", "\n").strip()


def text_digest(text):
    """SHA-256 of the whitespace/case-normalized text, for exact-duplicate checks."""
    normalized = " ".join(clean_text(text).split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def title_key(text):
    """Extract a normalized title key from a leading `title:` line, or None."""
    first = text.strip().splitlines()[0]
    if not first.casefold().startswith("title:"):
        return None
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", first[6:]).casefold()).strip() or None


def iter_documents(path):
    """Yield (line_number, cleaned_text) for each JSONL row, validating as we go."""
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from error
            if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                raise ValueError(f"{path}:{line_number}: expected an object with a string 'text'")
            text = clean_text(row["text"])
            if not text:
                raise ValueError(f"{path}:{line_number}: empty document")
            yield line_number, text


def audit_corpus(data_dir):
    """Audit all three splits and fail on duplicates or cross-split title leakage.

    Returns a report dict with per-split statistics and SHA-256 hashes, exact
    duplicate groups, cross-split title groups, and an overall `passed` flag.
    """
    texts, titles = defaultdict(list), defaultdict(list)
    report = {"splits": {}, "errors": [], "warnings": []}
    for split in SPLITS:
        path = Path(data_dir) / f"{split}.jsonl"
        lengths, missing_titles = [], 0
        if not path.is_file():
            report["errors"].append(f"Missing file: {path}")
            continue
        try:
            for line_number, text in iter_documents(path):
                lengths.append(len(text))
                location = {"split": split, "line": line_number}
                texts[text_digest(text)].append(location)
                title = title_key(text)
                if title:
                    titles[title].append(location)
                else:
                    missing_titles += 1
        except ValueError as error:
            report["errors"].append(str(error))
        report["splits"][split] = {
            "file": str(path), "sha256": file_sha256(path),
            "documents": len(lengths), "characters": sum(lengths),
            "min_characters": min(lengths, default=0),
            "median_characters": statistics.median(lengths) if lengths else 0,
            "max_characters": max(lengths, default=0),
            "documents_without_title": missing_titles,
        }
        if not lengths:
            report["errors"].append(f"{split}: no nonempty documents")

    exact_duplicates = [locations for locations in texts.values() if len(locations) > 1]
    cross_titles = [
        {"title": title, "locations": locations}
        for title, locations in titles.items()
        if len({location["split"] for location in locations}) > 1
    ]
    report["exact_duplicate_groups"] = exact_duplicates
    report["cross_split_title_groups"] = cross_titles
    if exact_duplicates:
        report["errors"].append(
            f"Found {len(exact_duplicates)} exact duplicate groups; deduplicate at document level first."
        )
    if cross_titles:
        report["errors"].append(
            f"Found {len(cross_titles)} titles shared across splits; inspect and group by paper first."
        )
    report["warnings"].append(
        "Exact text and title checks do not detect all near duplicates, preprint/publisher versions, "
        "or overlap with the original ModernBERT pretraining corpus."
    )
    report["passed"] = not report["errors"]
    return report


def main():
    """CLI entry point: write the audit report, exit 0 only if it passed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=".")
    parser.add_argument("--output", default="reports/corpus_audit.json")
    args = parser.parse_args()
    report = audit_corpus(args.data_dir)
    write_json(args.output, report)
    for split, summary in report["splits"].items():
        print(f"{split}: {summary['documents']:,} documents; {summary['characters']:,} characters")
    print(f"Audit: {'PASS' if report['passed'] else 'FAIL'}. Report: {args.output}")
    for error in report["errors"]:
        print(f"ERROR: {error}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
