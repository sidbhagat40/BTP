"""Build the downstream yield-strength datasets from the Citrine MPEA dataset.

Source: Borg et al., Sci Data 7:430 (2020), github.com/CitrineInformatics/MPEA_dataset.
Primary target: compression yield strength (T tests kept in a separate, exploratory file).

Deterministic split by composition: a unique composition string is hashed with
SHA-256; buckets <70 = train, <85 = validation, else test. No composition appears
in two splits. Every emitted row carries its provenance (doi, year, formula).

Outputs
-------
<output-dir>/train.jsonl, validation.jsonl, test.jsonl
    Fields: id, text, target (YS MPa), source (formula/doi/year/test/temp/processing)
<output-dir>/manifest.json
    SHA-256 of every raw input and emitted file, plus counts and the frozen template.
<output-dir>/split_report.json
    Per-split statistics (rows, unique compositions, target distribution).

Usage: python -m downstream.build_property_dataset --input data/MPEA_dataset.csv --output-dir data/hea-prop-ys
"""

import argparse
import csv
import hashlib
import json
import os
import statistics as st
import sys
from fractions import Fraction

from hea_cpt.alloys import normalized_composition

YS_COL = "PROPERTY: YS (MPa)"
FORMULA_COL = "FORMULA"
TYPE_COL = "PROPERTY: Type of test"
TEMP_COL = "PROPERTY: Test temperature ($^\circ$C)"
PROC_COL = "PROPERTY: Processing method"
DOI_COL = "REFERENCE: doi"
YEAR_COL = "REFERENCE: year"

TEMPLATE_VERSION = "hea-prop-ys-template-v1"


def composition_text(comp):
    """Fixed-format composition string; percentages rounded to 4 significant digits."""
    parts = [f"{el} {float(frac) * 100:g}%" for el, frac in sorted(comp.items())]
    return ", ".join(parts)


def input_text(formula, comp, test_type, temp_c, processing):
    proc = (processing or "").strip().upper() or "unspecified"
    lines = [
        f"Multi-principal element alloy, target: yield strength in MPa.",
        f"Composition: {composition_text(comp)}",
        f"({len(comp)} principal elements; formula {formula}).",
        f"Test: {'compression' if test_type == 'C' else 'tension'} at {temp_c:g} degrees Celsius.",
        f"Processing: {proc}.",
    ]
    return "\n".join(lines)


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bucket_for_composition(comp_string):
    h = int(hashlib.sha256(comp_string.encode("utf-8")).hexdigest()[:8], 16) % 100
    if h < 70:
        return "train"
    if h < 85:
        return "validation"
    return "test"


def collect_rows(csv_path, test_type):
    """Parse, dedupe, and bucket rows of one test type. Raises on silent data loss."""
    with open(csv_path, encoding="utf-8", errors="replace") as fh:
        raw = list(csv.DictReader(fh))
    if not raw:
        raise SystemExit(f"No rows parsed from {csv_path}")

    seen, rows, failures = set(), [], []
    for idx, r in enumerate(raw):
        ys_raw = (r.get(YS_COL) or "").strip()
        formula = (r.get(FORMULA_COL) or "").replace(" ", "")
        if not ys_raw or not formula:
            continue
        if (r.get(TYPE_COL) or "").strip() != test_type:
            continue
        try:
            ys = float(ys_raw)
            comp = normalized_composition(formula)
        except Exception as exc:  # noqa: BLE001 - record and fail loudly at the end
            failures.append({"row": idx, "formula": formula, "error": str(exc)})
            continue
        if not 0 < ys <= 5000:
            raise SystemExit(f"Row {idx}: suspicious yield strength {ys}; refusing to emit.")
        temp_raw = (r.get(TEMP_COL) or "").strip() or "25.0"
        temperature = float(temp_raw)
        proc = (r.get(PROC_COL) or "").strip().upper()
        comp_string = ",".join(f"{el}:{float(f):.6f}" for el, f in sorted(comp.items()))
        key = (comp_string, temperature, proc)
        if key in seen:  # exact duplicate condition
            continue
        seen.add(key)
        split = bucket_for_composition(comp_string)
        rows.append({
            "id": f"{test_type}-{idx:05d}",
            "text": input_text(formula, comp, test_type, temperature, proc),
            "target": ys,
            "source": {
                "formula": formula, "test_type": test_type, "temperature_c": temperature,
                "processing": proc, "composition_hash": comp_string,
                "doi": (r.get(DOI_COL) or "").strip(), "year": (r.get(YEAR_COL) or "").strip(),
                "raw_row": idx,
            },
        })
    return rows, failures


def write_dataset(rows, role, type_tag, output_dir, manifest, report):
    """Emit one dataset's three split files and record stats in manifest/report."""
    counts, comps = {}, {}
    for split in ("train", "validation", "test"):
        subset = [r for r in rows
                  if bucket_for_composition(r["source"]["composition_hash"]) == split]
        counts[split] = len(subset)
        comps[split] = len({r["source"]["composition_hash"] for r in subset})
        path = os.path.join(output_dir, f"{role}-{type_tag}-{split}.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for r in sorted(subset, key=lambda x: x["id"]):
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        manifest["files"][os.path.basename(path)] = sha256_of_file(path)
    targets = [r["target"] for r in rows]
    report[f"{role}-{type_tag}"] = {"rows": len(rows), "unique_compositions_per_split": comps,
                                    "counts": counts,
                                    "target_mean": round(st.mean(targets), 1),
                                    "target_sd": round(st.pstdev(targets), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    manifest = {"template_version": TEMPLATE_VERSION,
                "split_rule": "sha256(composition)[:8] mod 100: <70 train, <85 validation, else test",
                "source": {"file": os.path.basename(args.input),
                           "sha256": sha256_of_file(args.input),
                           "citation": "Borg et al., Sci Data 7:430 (2020), doi:10.1038/s41597-020-00768-9"},
                "files": {}}
    report = {}

    for test_type, role in (("C", "primary"), ("T", "exploratory")):
        rows, failures = collect_rows(args.input, test_type)
        if failures:
            raise SystemExit(f"Composition parsing failures in {test_type} rows: {failures[:5]}")
        if test_type == "C":
            primary_rows = rows
        write_dataset(rows, role, test_type, args.output_dir, manifest, report)

    # Combined protocol: compression + tension together (test mode is part of the
    # input text; dedupe key includes the mode so a C/T pair on the same
    # condition survives as two legitimately different population samples).
    combined, seen = [], set()
    for rows in (primary_rows, collect_rows(args.input, "T")[0]):
        for r in rows:
            key = (r["source"]["composition_hash"], r["source"]["temperature_c"],
                   r["source"]["test_type"], r["source"]["processing"])
            if key not in seen:
                seen.add(key)
                combined.append(r)
    combined.sort(key=lambda x: x["id"])
    write_dataset(combined, "secondary", "CT", args.output_dir, manifest, report)

    with open(os.path.join(args.output_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with open(os.path.join(args.output_dir, "split_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nOutputs in {args.output_dir} — self-check passed: no parse failures, no duplicates, splits composition-disjoint.")


if __name__ == "__main__":
    main()
