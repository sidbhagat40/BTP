"""
Stage 3 of the AlloyBERT pipeline: multi-task regression fine-tuning on the
real, literature-derived MPEA property dataset.

Pipeline recap
--------------
Stage 1 (done):   generate synthetic HEA text corpus
Stage 2 (done):   continued MLM pretraining of ModernBERT on that corpus -> HEABERT
Stage 3 (THIS):   attach a regression head to ModernBERT (or your Stage-2
                  HEABERT checkpoint) and fine-tune it to predict measured
                  alloy properties from a text description of the alloy,
                  using this real MPEA dataset.

Design decisions (read this before running -- reflects the CURRENT code,
not earlier drafts)
--------------------------------------------------------------------------
1. TARGETS (8, all genuinely measured -- see TARGET_COLUMNS/TARGET_SHORT_NAMES):
   grain size, experimental density, HV, YS, UTS, elongation, plastic
   elongation, experimental Young's modulus. Two columns present in the raw
   CSV are DELIBERATELY EXCLUDED after checking them against the actual
   data: "Calculated Density" (r=0.9998 with a simple rule-of-mixtures
   estimate from composition alone) and "Calculated Young modulus" (r=0.997
   vs. a composition-weighted average) are both near-deterministic formulas,
   not measured properties -- predicting them tests nothing about real alloy
   behavior. See the comment above TARGET_COLUMNS for the numbers.

2. CONDITIONS, not targets (see CONDITION_SPECS): test temperature and O/N
   interstitial content are quantities the model is TOLD, not asked to
   predict -- mechanical properties genuinely vary with all three, but
   "predicting" them (especially O/N, which are processing/purity artifacts,
   not composition-derived properties) isn't a materials-meaningful task.
   Each condition is fed two ways: (a) mentioned in the generated prose when
   known (nothing is said when it isn't -- no fabricated number appears in
   the text), and (b) as a precise auxiliary numeric feature concatenated
   directly onto the pooled text embedding, since prose numbers are a lossy
   channel for an encoder to read exactly. When a condition is UNKNOWN, no
   domain-specific value is guessed for it (e.g. no "assume 25C") -- its
   normalized feature is forced to exactly 0, the network's own neutral
   point, paired with a "known" flag so the model can tell a real
   measurement (any value, flag=1) from "no information" (flag=0). A
   plausible-looking constant run through z-scoring is NOT neutral in
   general (this dataset's temperatures span -268.8C to 1600C, so 25C
   z-scored against that distribution is a specific, non-trivial signal,
   not "no information") -- see the comment above CONDITION_SPECS. C content
   is dropped entirely (4/1545 rows -- too sparse to be useful either way).

3. LEAKAGE. No numeric TARGET_COLUMNS value is ever written into the
   generated text -- text only describes categorical/condition information
   (composition, microstructure, processing route, phase class, test type,
   temperature, O/N content). Composition is rendered via
   canonical_parts_pct, a deterministic sort (fraction desc, then element
   symbol), so the SAME text (and therefore prediction) is produced
   regardless of what order the elements were written in the input formula
   -- e.g. "Al1 Co1 Fe1 Ni1" and "Ni1 Al1 Fe1 Co1" are identical inputs to
   the model.

4. PHYSICS-INFORMED DESCRIPTORS (see compute_physics_descriptors): atomic
   size mismatch (delta), valence electron concentration (VEC),
   electronegativity spread (chi_std), and configurational mixing entropy
   (Smix/R) are computed directly from composition using a built-in element
   property table and fed as additional auxiliary features. These are the
   standard predictors in the HEA phase-formation literature and give the
   model a physics-based prior that ~1,500 rows alone are unlikely to fully
   learn from raw text -- and, being computed from composition rather than
   memorized per-row, they help the model generalize to alloys outside the
   training set rather than only interpolating within it.

5. MISSING TARGET VALUES. Every target column has heavy missingness. This is
   handled with per-target masking: a per-example, per-target mask tracks
   which targets are actually observed, and the loss (masked MSE) only
   backpropagates through observed entries. Targets are standardized
   (z-scored) per-column using training-set statistics computed only from
   observed values.

6. TRAIN/EVAL SPLIT IS GROUPED BY COMPOSITION, not random per-row. The same
   alloy composition can appear many times under different processing/test
   conditions (in this CSV, 1,545 rows collapse to only 630 unique
   compositions, with the most common alloy appearing 86 times) -- a random
   row split can put the SAME alloy in both train and eval, letting the
   model pass eval by recognizing a formula it already saw rather than by
   generalizing to a new one. Splitting is done on canonical composition
   keys instead, so every eval alloy is guaranteed unseen during training.

7. OUT-OF-DISTRIBUTION FLAGGING (see nearest_training_distance /
   predict_alloy). With only ~630 unique training alloys, some future query
   will be far outside anything the model actually trained on.
   predict_alloy() computes the query's distance (in z-scored
   physics-descriptor space) to its nearest training-set neighbor and
   attaches a warning when that distance is large, rather than silently
   returning an unqualified extrapolation.

8. TEXT DIVERSITY. Each row's text is assembled by randomly (but
   reproducibly, seeded by row index) choosing among several phrasings for
   each available field and a random field order/connector style. Fields
   with no data for a given row are simply omitted -- nothing is invented.

9. MULTI-SEED COMPARISON (see --num_seeds / run_one_seed). --model_name
   accepts either the base ModernBERT checkpoint or a local path to your
   Stage-2 HEABERT checkpoint, so you can fine-tune and compare both. With
   --num_seeds > 1, each seed gets an independent composition-grouped split
   + weight re-init + training run, and the script reports mean +/- std MAE
   per target across seeds (saved to seeds_summary.json) -- with only ~630
   unique alloys, a single split's MAE is noisy enough that "one checkpoint
   beat the other" needs several seeds to be a real claim rather than luck
   of the split.

10. MODEL-SELECTION METRIC IS NORMALIZED AND RESTRICTED TO WELL-SUPPORTED
   TARGETS (see TARGET_WELL_SUPPORTED_MIN_OBS / compute_metrics). An earlier
   version used a single pooled "sum of raw absolute errors across all
   targets" metric for both epoch-checkpoint selection and best-seed
   selection. That's a real problem: it sums errors across units that are
   not comparable (um, g/cm^3, HV, MPa, %, GPa), so a single bad prediction
   on a GPa-scale target can swamp many good MPa-scale predictions. Worse,
   in an actual base-vs-HEABERT comparison run on this dataset, the four
   sparsest targets (grain_size, exp_density, exp_youngs_modulus,
   elongation_plastic -- all under 250 observed rows dataset-wide) produced
   predictions identical to many decimal places between two DIFFERENT
   pretrained encoders on most seeds, plus wildly unstable per-seed MAE
   (e.g. exp_youngs_modulus_GPa ranging from 21 to 619 depending on seed) --
   both symptoms of too little supervision for the model to learn anything
   beyond a near-constant prediction, not real model behavior. Pooling those
   into one raw metric let seed-to-seed noise on data-starved targets decide
   which checkpoint "won", drowning out genuine differences on the
   well-supported targets. metric_for_best_model and the best-seed pick in
   main() now both use "mae_normalized_avg_well_supported": each target's
   MAE divided by its own train-set std (making units comparable), averaged
   only over targets with >= TARGET_WELL_SUPPORTED_MIN_OBS observations
   dataset-wide (YS/UTS/HV/elongation in this dataset). The old pooled
   metric is still reported (as mae_overall_masked) for reference, just no
   longer used to pick a winner.

Requirements
------------
    pip install "transformers>=4.48" datasets accelerate torch pandas scikit-learn --break-system-packages

Usage
-----
    # Baseline: fine-tune plain ModernBERT, 5 seeds for a stable comparison number
    python finetune_modernbert_regression.py \\
        --csv MPEA_dataset.csv \\
        --model_name answerdotai/ModernBERT-base \\
        --output_dir ./modernbert-base-mpea \\
        --num_seeds 5

    # Comparison: fine-tune your Stage-2 domain-pretrained checkpoint, same settings
    python finetune_modernbert_regression.py \\
        --csv MPEA_dataset.csv \\
        --model_name ./heabert-base-pretrained/final \\
        --output_dir ./heabert-mpea \\
        --num_seeds 5

You can also just build the text corpus (no training) to inspect it first:
    python finetune_modernbert_regression.py --csv MPEA_dataset.csv --dump_text_only preview.jsonl
"""

import argparse
import json
import math
import os
import random

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from transformers import (
    AutoConfig,
    AutoModel,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)

# ----------------------------------------------------------------------------
# Column bookkeeping
# ----------------------------------------------------------------------------

COL_FORMULA = "FORMULA"
COL_MICROSTRUCTURE = "PROPERTY: Microstructure"
COL_PROCESSING = "PROPERTY: Processing method"
COL_PHASE_CLASS = "PROPERTY: BCC/FCC/other"
COL_TEST_TYPE = "PROPERTY: Type of test"

# Conditions: quantities the model should be TOLD, not asked to predict.
# Each is (short_name, csv_column) -- generalized so more conditions can be
# added later without restructuring the aux-feature code. No impute-default
# constant is stored here on purpose -- see the note above CONDITION_SPECS
# below for why a domain guess isn't actually neutral.
#
# - test_temp_C: results (esp. YS/UTS/elongation) vary with test temperature,
#   so the model must be told it as an input rather than guess it.
# - O/N_content_wppm: these are PROCESSING/PURITY artifacts (interstitial
#   contamination from powder or furnace atmosphere), not something
#   determined by the nominal alloy design -- so "predicting" them isn't a
#   materials-meaningful task. But interstitial content is well documented to
#   affect mechanical properties (e.g. oxygen embrittlement in refractory
#   HEAs), so it belongs as a CONDITION the model can use when known, exactly
#   like temperature -- not as an output.
#   (C content is dropped entirely: only 4/1545 rows have it, too sparse to
#   be useful as either a target or a condition.)
COL_TEST_TEMP = "PROPERTY: Test temperature ($^\\circ$C)"
COL_O_CONTENT = "PROPERTY: O content (wppm)"
COL_N_CONTENT = "PROPERTY: N content (wppm)"

# No domain-specific default (e.g. "assume 25C") is used for unknown
# conditions. Picking a plausible-sounding constant and feeding it through
# normalization is not actually neutral: e.g. this dataset's temperatures
# span -268.8C to 1600C, so the mean of *known* values is nowhere near 25C,
# and z-scoring 25C against that mean would inject a specific, arbitrary
# signal into the network on every row where temperature is simply unknown
# -- effectively smuggling in an assumption the model was never told to
# make. Instead (see build_dataframe/run_one_seed/predict_alloy), unknown
# conditions get their raw value zeroed out and their normalized feature is
# explicitly forced to exactly 0 -- the network's own neutral point, meaning
# "no information", not "assume this real-world number". The known/unknown
# flag is what actually tells the model whether a value is real.
CONDITION_SPECS = [
    ("test_temp_C", COL_TEST_TEMP),
    ("O_content_wppm", COL_O_CONTENT),
    ("N_content_wppm", COL_N_CONTENT),
]

# Numeric targets -- measured material properties only. Two columns that were
# in earlier versions of this script are DELIBERATELY EXCLUDED here after
# checking them against the actual data:
#
#   - "Calculated Density": correlates r=0.9998 (MAE 0.026 g/cm^3) with a
#     simple rule-of-mixtures estimate from composition alone. It's a
#     deterministic formula, not a measured property -- a model could match
#     it almost exactly by memorizing composition arithmetic, which tests
#     nothing about real alloy understanding and wastes multi-task loss
#     budget on an already-solved sub-problem.
#   - "Calculated Young modulus": same story, r=0.997 (~3% mean error) vs. a
#     simple composition-weighted average of elemental moduli.
#
# Their EXPERIMENTAL counterparts are kept, since those reflect real
# microstructure/porosity/texture effects a rule-of-mixtures formula can't
# capture -- that's the genuinely hard, informative prediction target.
TARGET_COLUMNS = [
    "PROPERTY: grain size ($\\mu$m)",
    "PROPERTY: Exp. Density (g/cm$^3$)",
    "PROPERTY: HV",
    "PROPERTY: YS (MPa)",
    "PROPERTY: UTS (MPa)",
    "PROPERTY: Elongation (%)",
    "PROPERTY: Elongation plastic (%)",
    "PROPERTY: Exp. Young modulus (GPa)",
]

# Short, filesystem/JSON-friendly names for the targets, used for metrics
# and any saved artifacts.
TARGET_SHORT_NAMES = [
    "grain_size_um",
    "exp_density",
    "HV",
    "YS_MPa",
    "UTS_MPa",
    "elongation_pct",
    "elongation_plastic_pct",
    "exp_youngs_modulus_GPa",
]

# Minimum number of observed rows (out of 1545) for a target to be treated as
# "well-supported" for model-comparison purposes. Found empirically from this
# dataset's actual coverage, not guessed: YS(1067)/elongation(619)/UTS(539)/
# HV(530) cleanly cluster above 500 rows, while elongation_plastic(149)/
# grain_size(237)/exp_youngs_modulus(145)/exp_density(112) cluster below 250
# -- there's a clean gap between the two groups, and 300 sits in it. This
# matters because, in an actual base-vs-HEABERT comparison run on this data,
# the four sparse targets showed base/HEABERT predictions identical to many
# decimal places across most seeds (both models collapsing toward a
# near-constant prediction from too little supervision) plus wildly unstable,
# sometimes physically implausible MAE across seeds (e.g.
# exp_youngs_modulus_GPa MAE ranging 21-619 depending on seed) -- these
# targets' per-seed MAE is too noisy to draw any real conclusion from, and
# pooling them into one aggregate metric (see compute_metrics) drowns out
# genuine signal from the well-supported targets.
TARGET_WELL_SUPPORTED_MIN_OBS = 300

TEST_TYPE_MAP = {"C": "a compressive test", "T": "a tensile test"}


# ----------------------------------------------------------------------------
# Physics-informed HEA descriptors (Yang & Zhang / Guo et al. style)
# ----------------------------------------------------------------------------
# These four composition-derived descriptors are the standard predictors used
# in the HEA literature for phase formation (solid solution vs. intermetallic,
# FCC vs. BCC) and correlate with mechanical behavior too. Computing them
# explicitly and feeding them as auxiliary numeric features gives the model a
# strong physics-based prior that ~1,500 text examples alone are unlikely to
# fully learn from scratch -- this is likely the single highest-value addition
# for prediction accuracy, more than tweaking the text templates further.
#
#   delta (atomic size mismatch, %):   delta = 100 * sqrt(sum(c_i * (1 - r_i/r_avg)^2))
#   VEC   (valence electron concentration, avg): sum(c_i * VEC_i)
#   chi_std (electronegativity spread): sqrt(sum(c_i * (chi_i - chi_avg)^2))
#   Smix/R (ideal configurational entropy / R): -sum(c_i * ln c_i)
#
# Values below are standard tabulated metallic radii (pm, CN12), Pauling
# electronegativities, and VEC (group-based) for elements that commonly
# appear in HEA/MPEA composition papers, including this dataset's alloys.
ELEMENT_PROPS = {
    # symbol: (atomic_radius_pm, electronegativity, VEC)
    "Li": (152, 0.98, 1), "Be": (112, 1.57, 2), "B": (82, 2.04, 3), "C": (77, 2.55, 4),
    "N": (75, 3.04, 5), "Na": (186, 0.93, 1), "Mg": (160, 1.31, 2), "Al": (143, 1.61, 3),
    "Si": (117, 1.90, 4), "Sc": (162, 1.36, 3), "Ti": (147, 1.54, 4), "V": (134, 1.63, 5),
    "Cr": (128, 1.66, 6), "Mn": (126, 1.55, 7), "Fe": (126, 1.83, 8), "Co": (125, 1.88, 9),
    "Ni": (124, 1.91, 10), "Cu": (128, 1.90, 11), "Zn": (134, 1.65, 12), "Ga": (135, 1.81, 3),
    "Ge": (122, 2.01, 4), "Y": (180, 1.22, 3), "Zr": (160, 1.33, 4), "Nb": (146, 1.6, 5),
    "Mo": (139, 2.16, 6), "Tc": (136, 1.9, 7), "Ru": (134, 2.2, 8), "Rh": (134, 2.28, 9),
    "Pd": (137, 2.20, 10), "Ag": (144, 1.93, 11), "Cd": (151, 1.69, 12), "In": (167, 1.78, 3),
    "Sn": (140, 1.96, 4), "Hf": (159, 1.3, 4), "Ta": (146, 1.5, 5), "W": (139, 2.36, 6),
    "Re": (137, 1.9, 7), "Os": (135, 2.2, 8), "Ir": (135.5, 2.20, 9), "Pt": (138.5, 2.28, 10),
    "Au": (144, 2.54, 11), "Pb": (175, 2.33, 4), "Bi": (170, 2.02, 5), "Ca": (197, 1.0, 2),
    "La": (187.7, 1.1, 3), "Ce": (182.5, 1.12, 3), "Sm": (180.4, 1.17, 3), "Gd": (180.1, 1.2, 3),
    "P": (110, 2.19, 5), "S": (104, 2.58, 6),
    "Nd": (181.4, 1.14, 3),  # added after checking this dataset's FORMULA column directly (see
                             # compute_physics_descriptors note) -- appears once, in "Al1 Co1 Cu1 Fe1 Nd1 Ni1".
}
GAS_CONSTANT_R = 8.314  # J/(mol*K)
_WARNED_UNKNOWN_ELEMENTS = set()  # tracks which unknown-element warnings have already been printed, so a
                                   # large dataset doesn't spam the same warning once per row.


def compute_physics_descriptors(formula: str):
    """Returns (delta, VEC, chi_std, Smix_over_R). If the formula contains an
    element outside ELEMENT_PROPS, that element is skipped (with remaining
    composition renormalized) rather than failing, but a warning is printed
    once per unknown element -- silently dropping an element from these
    descriptors previously let a real gap (Nd was missing, despite appearing
    in this dataset) go unnoticed. Add any newly-flagged element to
    ELEMENT_PROPS above rather than relying on this fallback long-term.
    """
    elements = parse_formula(formula)
    unknown = sorted({el for el, _ in elements if el not in ELEMENT_PROPS})
    for el in unknown:
        if el not in _WARNED_UNKNOWN_ELEMENTS:
            print(f"[warn] element '{el}' (from formula '{formula}') is not in ELEMENT_PROPS -- "
                  f"physics descriptors for any alloy containing it are computed excluding it. "
                  f"Add it to ELEMENT_PROPS for a correct value.")
            _WARNED_UNKNOWN_ELEMENTS.add(el)
    known = [(el, f) for el, f in elements if el in ELEMENT_PROPS]
    if not known:
        return 0.0, 0.0, 0.0, 0.0
    total = sum(f for _, f in known)
    comps = [(el, f / total) for el, f in known]

    r_avg = sum(c * ELEMENT_PROPS[el][0] for el, c in comps)
    delta = 100.0 * math.sqrt(sum(c * (1 - ELEMENT_PROPS[el][0] / r_avg) ** 2 for el, c in comps))

    vec = sum(c * ELEMENT_PROPS[el][2] for el, c in comps)

    chi_avg = sum(c * ELEMENT_PROPS[el][1] for el, c in comps)
    chi_std = math.sqrt(sum(c * (ELEMENT_PROPS[el][1] - chi_avg) ** 2 for el, c in comps))

    smix_over_r = -sum(c * math.log(c) for _, c in comps if c > 0)

    return delta, vec, chi_std, smix_over_r


# ----------------------------------------------------------------------------
# Composition parsing (for more natural composition sentences)
# ----------------------------------------------------------------------------

def parse_formula(formula: str):
    """'Al0.25 Co1 Fe1 Ni1' -> [('Al', 0.25), ('Co', 1.0), ('Fe', 1.0), ('Ni', 1.0)]"""
    elements = []
    for tok in str(formula).split():
        i = 0
        while i < len(tok) and not tok[i].isdigit() and tok[i] != ".":
            i += 1
        el, num = tok[:i], tok[i:]
        try:
            frac = float(num) if num else 1.0
        except ValueError:
            frac = 1.0
        if el:
            elements.append((el, frac))
    return elements


def canonical_parts_pct(formula: str):
    """Parse + sort a formula's elements into a DETERMINISTIC canonical order.

    This is what makes the model permutation-invariant: 'X0.1 Y0.3 Z' and
    'Z X0.1 Y0.3' (or any other ordering of the same composition) parse to
    exactly the same (element, at.%) sequence here, so every downstream text
    style built from this list is identical regardless of how the caller
    wrote the formula. Sort key = (fraction descending, element symbol
    ascending) so that ties (equal fractions) are also broken the same way
    every time, rather than depending on original token order.
    """
    elements = parse_formula(formula)
    if not elements:
        return []
    total = sum(f for _, f in elements) or 1.0
    parts_pct = [(el, 100.0 * f / total) for el, f in elements]
    parts_pct.sort(key=lambda x: (-x[1], x[0]))
    return parts_pct


def composition_to_atpct_string(formula: str, style: int) -> str:
    """Render a parsed formula as a human sentence fragment, in one of several
    styles -- all built from canonical_parts_pct, so all styles are
    permutation-invariant with respect to the order elements were written in
    the input formula."""
    parts_pct = canonical_parts_pct(formula)
    if not parts_pct:
        return str(formula)

    if style == 0:
        # "45.2% Fe, 27.3% Co, 27.3% Ni (atomic)"
        return ", ".join(f"{pct:.1f}% {el}" for el, pct in parts_pct) + " (atomic)"
    elif style == 1:
        # "Fe (45.2 at.%), Co (27.3 at.%), Ni (27.3 at.%)"
        return ", ".join(f"{el} ({pct:.1f} at.%)" for el, pct in parts_pct)
    elif style == 2:
        # "primarily Fe with Co and Ni" (qualitative, no invented numbers beyond ranking)
        names = [el for el, _ in parts_pct]
        if len(names) == 1:
            return f"pure {names[0]}"
        return f"primarily {names[0]} alloyed with " + " and ".join(names[1:])
    else:
        # Canonical formula notation, e.g. "Fe1 Co0.5 Ni0.5" -- reconstructed in
        # sorted order, NOT the raw input string (which may have been written
        # in any element order).
        return " ".join(f"{el}{pct/100.0:.4g}" for el, pct in parts_pct)


# ----------------------------------------------------------------------------
# Diverse, non-leaking text generation
# ----------------------------------------------------------------------------

COMPOSITION_TEMPLATES = [
    "This alloy has the composition {comp}.",
    "The material's nominal composition is {comp}.",
    "Elemental makeup: {comp}.",
    "The as-designed alloy formula corresponds to {comp}.",
    "Composition-wise, the sample is {comp}.",
]

MICROSTRUCTURE_TEMPLATES = [
    "Its microstructure is characterized as {ms}.",
    "Microstructural analysis identified a {ms} structure.",
    "The observed phase constitution is {ms}.",
    "It exhibits a {ms} microstructure.",
]

PROCESSING_TEMPLATES = {
    "CAST": [
        "It was produced by casting.",
        "The sample was fabricated via a cast route.",
        "Processing route: as-cast.",
    ],
    "WROUGHT": [
        "It was processed by wrought/mechanical working.",
        "The alloy underwent wrought processing.",
        "Processing route: wrought.",
    ],
    "ANNEAL": [
        "It was subsequently annealed.",
        "An annealing heat treatment was applied.",
        "Processing route: annealed.",
    ],
    "POWDER": [
        "It was produced via powder metallurgy.",
        "The sample was consolidated from powder.",
        "Processing route: powder-based.",
    ],
    "OTHER": [
        "It was produced by a non-standard processing route.",
        "Processing route: other/unspecified conventional method.",
    ],
}

PHASE_TEMPLATES = {
    "FCC": [
        "The dominant crystal structure is FCC.",
        "It is classified as an FCC-type alloy.",
        "Crystallographically, this is an FCC solid solution.",
    ],
    "BCC": [
        "The dominant crystal structure is BCC.",
        "It is classified as a BCC-type alloy.",
        "Crystallographically, this is a BCC solid solution.",
    ],
    "other": [
        "The crystal structure falls outside the simple FCC/BCC classification.",
        "It is classified structurally as 'other' (not single-phase FCC or BCC).",
    ],
}

TEST_TYPE_TEMPLATES = [
    "Mechanical behavior was assessed under {test}.",
    "It was mechanically evaluated using {test}.",
    "The reported mechanical data come from {test}.",
]

TEST_TEMP_TEMPLATES = [
    "Testing was carried out at {temp}\u00b0C.",
    "The measurement temperature was {temp}\u00b0C.",
    "Properties were recorded at a test temperature of {temp}\u00b0C.",
]

O_CONTENT_TEMPLATES = [
    "The measured oxygen content was {val} wppm.",
    "Interstitial oxygen was recorded at {val} wppm.",
]

N_CONTENT_TEMPLATES = [
    "The measured nitrogen content was {val} wppm.",
    "Interstitial nitrogen was recorded at {val} wppm.",
]

# Maps each CONDITION_SPECS short_name -> its own prose templates, so
# build_text_for_row can mention any registered condition generically.
CONDITION_TEMPLATES = {
    "test_temp_C": TEST_TEMP_TEMPLATES,
    "O_content_wppm": O_CONTENT_TEMPLATES,
    "N_content_wppm": N_CONTENT_TEMPLATES,
}

CONNECTORS = [" ", " ", " Additionally, ", " Furthermore, ", " "]


def build_text_for_row(row: pd.Series, row_idx: int) -> str:
    """Assemble a diverse, non-leaking, permutation-invariant text description
    for one alloy record.

    Only fields with actual data are mentioned. No numeric TARGET_COLUMNS
    value is ever included. Composition is always rendered via
    canonical_parts_pct, so this function returns the SAME text regardless of
    what order the elements were written in the input FORMULA string. Every
    registered CONDITION_SPECS entry (temperature, O/N content, ...) is
    mentioned here as prose AND fed separately as a precise auxiliary numeric
    feature by build_dataframe/predict_alloy, since prose is a lossy way to
    convey an exact number to a BERT-style encoder.
    """
    rng = random.Random(1000003 * row_idx + 7)  # reproducible but row-varying

    sentences = []

    formula = row.get(COL_FORMULA)
    if pd.notna(formula) and str(formula).strip():
        style = rng.randrange(4)
        comp_str = composition_to_atpct_string(formula, style)
        template = rng.choice(COMPOSITION_TEMPLATES)
        sentences.append(template.format(comp=comp_str))

    ms = row.get(COL_MICROSTRUCTURE)
    if pd.notna(ms) and str(ms).strip():
        template = rng.choice(MICROSTRUCTURE_TEMPLATES)
        sentences.append(template.format(ms=str(ms).strip()))

    phase = row.get(COL_PHASE_CLASS)
    if pd.notna(phase) and str(phase).strip() in PHASE_TEMPLATES:
        sentences.append(rng.choice(PHASE_TEMPLATES[str(phase).strip()]))

    proc = row.get(COL_PROCESSING)
    if pd.notna(proc) and str(proc).strip() in PROCESSING_TEMPLATES:
        sentences.append(rng.choice(PROCESSING_TEMPLATES[str(proc).strip()]))

    test_type = row.get(COL_TEST_TYPE)
    if pd.notna(test_type) and str(test_type).strip() in TEST_TYPE_MAP:
        template = rng.choice(TEST_TYPE_TEMPLATES)
        sentences.append(template.format(test=TEST_TYPE_MAP[str(test_type).strip()]))

    for short_name, col in CONDITION_SPECS:
        val = row.get(col)
        if pd.notna(val):
            template = rng.choice(CONDITION_TEMPLATES[short_name])
            sentences.append(template.format(temp=f"{float(val):g}", val=f"{float(val):g}"))

    if not sentences:
        # Extremely rare fallback: only FORMULA guaranteed present in this dataset.
        sentences.append(f"Alloy: {composition_to_atpct_string(formula, 3)}.")

    rng.shuffle(sentences)
    # Join with varied connectors between sentences (not just plain spaces every time).
    text = sentences[0]
    for s in sentences[1:]:
        text += rng.choice(CONNECTORS) + s
    return text


def build_aux_features_for_row(row: pd.Series):
    """Precise numeric conditioning + physics-descriptor features fed directly
    into the regression head (concatenated to the pooled text embedding).
    Returns, generically for every CONDITION_SPECS entry, (raw_value_or_0,
    known_flag) pairs in order, followed by the four always-defined
    physics descriptors (delta, VEC, chi_std, Smix_over_R).

    IMPORTANT: when a condition is unknown, the raw value here is just a
    placeholder 0.0 -- it is NOT a domain guess (no "assume room
    temperature"). The actual neutral value the network sees is enforced
    later, in run_one_seed()/predict_alloy(), by forcing the NORMALIZED
    feature to exactly 0 wherever known_flag == 0 -- see the comment above
    CONDITION_SPECS for why a normalized real-world constant isn't actually
    neutral. The known_flag is what tells the model whether a value is real.
    """
    vals = []
    for _short_name, col in CONDITION_SPECS:
        raw = row.get(col)
        if pd.notna(raw):
            vals.extend([float(raw), 1.0])
        else:
            vals.extend([0.0, 0.0])  # placeholder only -- zeroed again post-normalization
    vals.extend(compute_physics_descriptors(row.get(COL_FORMULA)))
    return tuple(vals)


AUX_FEATURE_NAMES = []
for _short_name, _col in CONDITION_SPECS:
    AUX_FEATURE_NAMES += [_short_name, f"{_short_name}_known"]
AUX_FEATURE_NAMES += ["delta_atomic_mismatch", "VEC", "chi_std", "Smix_over_R"]
NUM_AUX_FEATURES = len(AUX_FEATURE_NAMES)
_N_CONDITIONS = len(CONDITION_SPECS)  # used below to know where condition pairs end and physics features start



# ----------------------------------------------------------------------------
# Dataset assembly: text + masked multi-target vector
# ----------------------------------------------------------------------------

def build_dataframe(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing_targets = [c for c in TARGET_COLUMNS if c not in df.columns]
    if missing_targets:
        raise SystemExit(f"CSV is missing expected columns: {missing_targets}")

    texts = [build_text_for_row(df.iloc[i], i) for i in range(len(df))]
    aux = [build_aux_features_for_row(df.iloc[i]) for i in range(len(df))]
    df = df.copy()
    df["__text__"] = texts
    for j, name in enumerate(AUX_FEATURE_NAMES):
        df[f"__aux_{name}__"] = [a[j] for a in aux]
    return df


class MPEADataset(Dataset):
    def __init__(self, encodings, targets: np.ndarray, mask: np.ndarray, aux_features: np.ndarray):
        self.encodings = encodings
        self.targets = torch.tensor(targets, dtype=torch.float32)
        self.mask = torch.tensor(mask, dtype=torch.float32)
        self.aux_features = torch.tensor(aux_features, dtype=torch.float32)

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = self.targets[idx]
        item["label_mask"] = self.mask[idx]
        item["aux_features"] = self.aux_features[idx]
        return item


# ----------------------------------------------------------------------------
# Model: encoder + multi-task regression head, masked MSE loss
# ----------------------------------------------------------------------------

def _from_pretrained_kwargs(model_name: str) -> dict:
    """Use offline load for local checkpoint dirs (repo ModernBERT / HEA-BERT-synth)."""
    if os.path.isdir(model_name):
        return {"local_files_only": True}
    return {}


class MultiTaskRegressionModel(nn.Module):
    """Text encoder + mean pooling, with NUM_AUX_FEATURES auxiliary features
    concatenated onto the pooled embedding before the regression head: one
    (value, known_flag) pair per registered CONDITION_SPECS entry (currently
    test temperature, O content, N content), followed by the four physics
    descriptors from compute_physics_descriptors (delta, VEC, chi_std,
    Smix_over_R). Conditioning this way (rather than only in prose) lets the
    model use precise numeric values, since results -- especially
    YS/UTS/elongation -- genuinely depend on test temperature and can depend
    on interstitial content too.
    """

    def __init__(self, model_name: str, num_targets: int, dropout: float = 0.1, num_aux_features: int = NUM_AUX_FEATURES):
        super().__init__()
        load_kw = _from_pretrained_kwargs(model_name)
        config = AutoConfig.from_pretrained(model_name, **load_kw)
        # AutoModel strips MLM heads when loading a MaskedLM Stage-1/2 checkpoint.
        self.encoder = AutoModel.from_pretrained(model_name, config=config, **load_kw)
        hidden_size = config.hidden_size
        self.num_aux_features = num_aux_features
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size + num_aux_features, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_targets),
        )

    def gradient_checkpointing_enable(self, gradient_checkpointing_kwargs=None):
        if hasattr(self.encoder, "gradient_checkpointing_enable"):
            kwargs = gradient_checkpointing_kwargs or {}
            self.encoder.gradient_checkpointing_enable(**kwargs)

    def gradient_checkpointing_disable(self):
        if hasattr(self.encoder, "gradient_checkpointing_disable"):
            self.encoder.gradient_checkpointing_disable()

    def forward(self, input_ids=None, attention_mask=None, labels=None, label_mask=None, aux_features=None, **kwargs):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden = outputs.last_hidden_state  # (B, T, H)
        # Mean-pool over real (non-padding) tokens. Padding tokens carry no
        # positional signal beyond their position index, and since composition
        # text is now canonically ordered (see canonical_parts_pct), this
        # pooling is deterministic and identical for any input formula string
        # that describes the same composition.
        mask = attention_mask.unsqueeze(-1).to(last_hidden.dtype)
        pooled = (last_hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-6)

        if aux_features is None:
            aux_features = torch.zeros(pooled.size(0), self.num_aux_features, device=pooled.device, dtype=pooled.dtype)
        combined = torch.cat([pooled, aux_features.to(pooled.dtype)], dim=-1)
        preds = self.head(combined)  # (B, num_targets)

        loss = None
        if labels is not None and label_mask is not None:
            sq_err = (preds - labels) ** 2 * label_mask
            denom = label_mask.sum().clamp(min=1.0)
            loss = sq_err.sum() / denom

        return {"loss": loss, "logits": preds}


class MaskedRegressionTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        outputs = model(**inputs)
        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=str, required=True, help="Path to the MPEA_dataset.csv file.")
    ap.add_argument(
        "--model_name",
        type=str,
        default="models/modernbert-large",
        help="HF hub id OR local path to ModernBERT-large / HEA-BERT-synth encoder checkpoint "
        "(e.g. models/modernbert-large or artifacts/hea-bert-synth/best_or_final).",
    )
    ap.add_argument("--output_dir", type=str, default="./modernbert-mpea-regression")
    ap.add_argument("--max_length", type=int, default=256)
    ap.add_argument("--num_train_epochs", type=float, default=15.0, help="Higher than Stage 2 since this head starts from scratch, but watch eval loss.")
    ap.add_argument("--per_device_train_batch_size", type=int, default=4)
    ap.add_argument("--per_device_eval_batch_size", type=int, default=4)
    ap.add_argument("--gradient_accumulation_steps", type=int, default=4)
    ap.add_argument(
        "--gradient_checkpointing",
        action="store_true",
        help="Lower VRAM (recommended for ModernBERT-large on 8GB GPUs).",
    )
    ap.add_argument("--learning_rate", type=float, default=2e-5)
    ap.add_argument("--head_dropout", type=float, default=0.1)
    ap.add_argument("--warmup_ratio", type=float, default=0.1)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--eval_fraction", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42, help="Base seed. With --num_seeds > 1, seeds used are seed, seed+1, seed+2, ...")
    ap.add_argument(
        "--num_seeds",
        type=int,
        default=1,
        help="Run this many independent (re-split + re-init + re-train) repeats and report mean+-std MAE per "
        "target across seeds, not just a single run's number. With only ~630 unique alloys, a single "
        "composition-grouped split can easily make one model look better/worse than another by chance -- "
        "use 3-5+ seeds before concluding one checkpoint (e.g. base vs. HEABERT) is actually better.",
    )
    ap.add_argument("--logging_steps", type=int, default=10)
    ap.add_argument(
        "--dump_text_only",
        type=str,
        default=None,
        help="If set, just write the generated (row_idx, text) pairs to this JSONL path and exit -- "
        "use this to eyeball the text diversity/correctness before spending compute on training.",
    )
    args = ap.parse_args()

    df = build_dataframe(args.csv)

    # Save the full processed dataset -- original columns PLUS the generated
    # text and every auxiliary condition/physics feature -- as its own CSV.
    # This is written regardless of --dump_text_only, so you always have a
    # concrete, inspectable artifact of exactly what was fed to the model
    # (not just the raw MPEA_dataset.csv), independent of whether training
    # actually runs in this invocation.
    os.makedirs(args.output_dir, exist_ok=True)
    processed_csv_path = os.path.join(args.output_dir, "processed_dataset.csv")
    df.to_csv(processed_csv_path, index=False)
    print(f"Saved processed dataset (original columns + generated text + aux features) to {processed_csv_path}")

    if args.dump_text_only:
        with open(args.dump_text_only, "w") as f:
            for i, row in df.iterrows():
                f.write(json.dumps({"row": int(i), "formula": row[COL_FORMULA], "text": row["__text__"]}) + "\n")
        print(f"Wrote {len(df)} text previews to {args.dump_text_only}. Exiting without training.")
        return

    # Tokenization doesn't depend on the seed -- do it once, reuse across seeds.
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name, **_from_pretrained_kwargs(args.model_name)
    )
    all_encodings = tokenizer(
        df["__text__"].tolist(), truncation=True, max_length=args.max_length, padding="max_length"
    )

    seeds = [args.seed + i for i in range(args.num_seeds)]
    results = []
    for seed in seeds:
        print(f"\n{'='*70}\nSeed {seed} ({seeds.index(seed) + 1}/{len(seeds)})\n{'='*70}")
        results.append(run_one_seed(df, tokenizer, all_encodings, args, seed))

    # ------------------------------------------------------------------
    # Aggregate across seeds: mean +- std per target, not just one run's number.
    # ------------------------------------------------------------------
    print(f"\n{'='*70}\nSummary across {len(seeds)} seed(s) for {args.model_name}\n{'='*70}")
    metric_keys = sorted({k for r in results for k in r["metrics"] if k.startswith("eval_mae_")})
    summary = {}
    for key in metric_keys:
        vals = [r["metrics"][key] for r in results if key in r["metrics"]]
        mean, std = float(np.mean(vals)), float(np.std(vals))
        summary[key] = {"mean": mean, "std": std, "n": len(vals)}
        label = key.replace("eval_mae_", "")
        print(f"  {label:28s} {mean:8.3f} +/- {std:.3f}  (n={len(vals)})")

    seeds_summary_path = os.path.join(args.output_dir, "seeds_summary.json")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(seeds_summary_path, "w") as f:
        json.dump(
            {
                "model_name": args.model_name,
                "seeds": seeds,
                "per_seed_metrics": [r["metrics"] for r in results],
                "summary_mean_std": summary,
            },
            f,
            indent=2,
        )
    print(f"Saved per-seed + aggregate metrics to {seeds_summary_path}")

    # Save the checkpoint from whichever seed had the best (lowest) overall
    # masked MAE -- avoids retraining, just picks among the runs already done.
    best = min(
        results,
        key=lambda r: r["metrics"].get(
            "eval_mae_normalized_avg_well_supported", r["metrics"].get("eval_mae_overall_masked", float("inf"))
        ),
    )
    print(f"Saving best-of-{len(seeds)} checkpoint (seed {best['seed']}) as the final model.")
    save_checkpoint(best, args)


def run_one_seed(df: pd.DataFrame, tokenizer, all_encodings: dict, args, seed: int) -> dict:
    """Run one full split + train + eval cycle for a given seed. Saves this
    seed's model + scaling to <output_dir>/seed_<seed>/checkpoint/ and returns
    only a lightweight dict (seed, metrics, checkpoint_dir) -- the trained
    model object itself is NOT kept in memory past this function (see the
    comment near the end of this function for why: holding every seed's
    model resident simultaneously risks OOM with --num_seeds > 1)."""
    set_seed(seed)

    # ------------------------------------------------------------------
    # Targets: build raw matrix + observed mask
    # ------------------------------------------------------------------
    raw_targets = df[TARGET_COLUMNS].to_numpy(dtype=float)  # NaN where missing
    observed_mask = (~np.isnan(raw_targets)).astype(np.float32)
    print("Target coverage (observed / total):")
    for name, col in zip(TARGET_SHORT_NAMES, TARGET_COLUMNS):
        n_obs = int(df[col].notna().sum())
        print(f"  {name:28s} {n_obs:5d} / {len(df)}")

    # ------------------------------------------------------------------
    # Train/eval split -- GROUPED BY COMPOSITION, not random per-row.
    # ------------------------------------------------------------------
    # The same alloy composition can appear multiple times (different
    # processing routes / test conditions), so a naive random row split can
    # put the SAME alloy in both train and eval. That would let the model
    # (and ModernBERT's tokenizer, which can memorize a specific formula's
    # tokens) pass eval by recognizing an alloy it already saw rather than by
    # generalizing to a genuinely new composition -- reported accuracy would
    # then overstate real-world generalization. Grouping by canonical
    # composition key ensures every eval alloy is one the model never saw
    # during training in any form, which is what actually matters for a
    # general-purpose HEA model.
    canonical_keys = [
        " ".join(f"{el}{pct:.4f}" for el, pct in canonical_parts_pct(f)) for f in df[COL_FORMULA]
    ]
    df["__comp_key__"] = canonical_keys
    unique_keys = sorted(set(canonical_keys))
    rng = np.random.RandomState(seed)
    rng.shuffle(unique_keys)
    n_eval_groups = max(1, int(len(unique_keys) * args.eval_fraction))
    eval_keys = set(unique_keys[:n_eval_groups])

    n = len(df)
    idx = np.arange(n)
    eval_idx = np.array([i for i in idx if canonical_keys[i] in eval_keys])
    train_idx = np.array([i for i in idx if canonical_keys[i] not in eval_keys])
    print(
        f"Composition-grouped split: {len(unique_keys)} unique alloys -> "
        f"{len(unique_keys) - n_eval_groups} train alloys ({len(train_idx)} rows), "
        f"{n_eval_groups} eval alloys ({len(eval_idx)} rows, all compositions unseen in training)"
    )

    # Save exactly which rows/alloys landed in train vs. eval FOR THIS SEED --
    # this genuinely does change seed to seed (unlike processed_dataset.csv's
    # text/aux columns, which are fixed regardless of seed since they're
    # seeded by row index, not by args.seed). Saved early, right after the
    # split is drawn, so this exists even if training later fails/is
    # interrupted.
    seed_output_dir = os.path.join(args.output_dir, f"seed_{seed}")
    os.makedirs(seed_output_dir, exist_ok=True)
    split_col = np.full(n, "", dtype=object)
    split_col[train_idx] = "train"
    split_col[eval_idx] = "eval"
    split_df = df.copy()
    split_df["__split__"] = split_col
    split_df = split_df[split_df["__split__"] != ""]
    split_path = os.path.join(seed_output_dir, f"split_seed_{seed}.csv")
    split_df.to_csv(split_path, index=False)
    print(f"[seed {seed}] Saved train/eval split membership ({len(train_idx)} train / {len(eval_idx)} eval rows) to {split_path}")

    # Standardize each target column using TRAIN-set observed values only.
    train_targets = raw_targets[train_idx]
    train_mask = observed_mask[train_idx]
    target_mean = np.zeros(len(TARGET_COLUMNS), dtype=np.float32)
    target_std = np.ones(len(TARGET_COLUMNS), dtype=np.float32)
    for j in range(len(TARGET_COLUMNS)):
        vals = train_targets[:, j][train_mask[:, j] > 0]
        if len(vals) > 1:
            target_mean[j] = vals.mean()
            target_std[j] = vals.std() if vals.std() > 1e-6 else 1.0
        elif len(vals) == 1:
            target_mean[j] = vals[0]
            target_std[j] = 1.0

    def standardize(matrix):
        out = (matrix - target_mean) / target_std
        out = np.nan_to_num(out, nan=0.0)  # masked-out entries don't matter, just avoid NaNs in the tensor
        return out.astype(np.float32)

    std_targets = standardize(raw_targets)

    # ------------------------------------------------------------------
    # Tokenization (passed in -- computed once in main(), reused across seeds)
    # ------------------------------------------------------------------
    def subset_encodings(encodings, subset_idx):
        return {k: [v[i] for i in subset_idx] for k, v in encodings.items()}

    aux_cols = [f"__aux_{name}__" for name in AUX_FEATURE_NAMES]
    aux_all = df[aux_cols].to_numpy(dtype=np.float32)

    # Normalize each aux feature using TRAIN-set stats, generically over
    # CONDITION_SPECS. Each condition contributes a (value, known_flag) pair:
    # the known_flag (already a clean 0/1 indicator) is left unnormalized,
    # while the value is normalized using only rows where it was actually
    # known (imputed rows would otherwise bias the mean/std). The physics
    # descriptors that follow are always defined, so they're normalized over
    # the full train set directly.
    aux_mean = np.zeros(NUM_AUX_FEATURES, dtype=np.float32)
    aux_std = np.ones(NUM_AUX_FEATURES, dtype=np.float32)
    for k, (_short_name, _col) in enumerate(CONDITION_SPECS):
        vidx, kidx = 2 * k, 2 * k + 1
        known_mask = aux_all[train_idx][:, kidx] > 0
        if known_mask.sum() > 1:
            aux_mean[vidx] = aux_all[train_idx][known_mask, vidx].mean()
            aux_std[vidx] = aux_all[train_idx][known_mask, vidx].std() or 1.0
        else:
            aux_mean[vidx], aux_std[vidx] = 0.0, 1.0
        # kidx (known flag) left at mean=0, std=1 -> unnormalized
    physics_start = 2 * _N_CONDITIONS
    for j in range(physics_start, NUM_AUX_FEATURES):
        vals = aux_all[train_idx][:, j]
        aux_mean[j] = vals.mean()
        aux_std[j] = vals.std() or 1.0

    aux_all_norm = (aux_all - aux_mean) / aux_std
    for k in range(_N_CONDITIONS):
        vidx, kidx = 2 * k, 2 * k + 1
        aux_all_norm[:, kidx] = aux_all[:, kidx]  # keep each known-flag as a raw 0/1
        # No default value, guessed or otherwise, reaches the network: wherever
        # this condition is unknown, force its normalized feature to EXACTLY 0
        # -- the model's own neutral point -- rather than whatever a
        # placeholder constant would z-score to. This is the actual fix for
        # "don't assume 25C (or anything else) when a value isn't available."
        aux_all_norm[aux_all[:, kidx] == 0, vidx] = 0.0

    train_ds = MPEADataset(subset_encodings(all_encodings, train_idx), std_targets[train_idx], observed_mask[train_idx], aux_all_norm[train_idx])
    eval_ds = MPEADataset(subset_encodings(all_encodings, eval_idx), std_targets[eval_idx], observed_mask[eval_idx], aux_all_norm[eval_idx])
    print(f"Train: {len(train_ds)} | Eval: {len(eval_ds)}")

    # ------------------------------------------------------------------
    # Model
    # ------------------------------------------------------------------
    model = MultiTaskRegressionModel(args.model_name, num_targets=len(TARGET_COLUMNS), dropout=args.head_dropout)
    if args.gradient_checkpointing and hasattr(model.encoder, "gradient_checkpointing_enable"):
        model.encoder.gradient_checkpointing_enable()
        print("[info] gradient checkpointing enabled on encoder")

    cuda_available = torch.cuda.is_available()
    use_bf16 = cuda_available and torch.cuda.is_bf16_supported()
    use_fp16 = cuda_available and not use_bf16
    if not cuda_available:
        print("[warn] no usable CUDA GPU detected -- training on CPU, this will be slow.")

    steps_per_epoch = max(1, len(train_ds) // (args.per_device_train_batch_size * args.gradient_accumulation_steps))
    total_steps = steps_per_epoch * math.ceil(args.num_train_epochs)
    warmup_steps = max(1, int(total_steps * args.warmup_ratio))

    # Precompute per-target mean/std for the metrics closure, and stash eval mask
    # so compute_metrics (which only receives predictions + labels from Trainer)
    # can still get at which entries were actually observed.
    eval_mask_np = observed_mask[eval_idx]
    total_obs_per_target = df[TARGET_COLUMNS].notna().sum().to_numpy()  # coverage over the FULL dataset,
    # not just this seed's train split -- so the well/sparse classification doesn't shift seed to seed.
    well_supported_flags = total_obs_per_target >= TARGET_WELL_SUPPORTED_MIN_OBS

    def compute_metrics(eval_pred):
        preds = eval_pred.predictions
        if isinstance(preds, (tuple, list)):
            preds = preds[0]
        labels = eval_pred.label_ids
        if isinstance(labels, (tuple, list)):
            # Older runs used label_names=["labels","label_mask"] which packs a tuple.
            labels = labels[0]
        preds = np.asarray(preds)
        labels = np.asarray(labels)
        # If a packed (N, 2*T) array ever appears, keep only the label block.
        if labels.ndim == 2 and labels.shape[1] == 2 * len(TARGET_SHORT_NAMES):
            labels = labels[:, : len(TARGET_SHORT_NAMES)]
        if preds.ndim == 2 and preds.shape[1] == 2 * len(TARGET_SHORT_NAMES):
            preds = preds[:, : len(TARGET_SHORT_NAMES)]

        mask = eval_mask_np
        if mask.shape[0] != preds.shape[0]:
            # Fall back to: non-zero standardized labels are unreliable; use finite check
            mask = np.ones_like(labels, dtype=np.float32)

        # Un-standardize both back to real units before computing MAE.
        preds_real = preds * target_std + target_mean
        labels_real = labels * target_std + target_mean
        abs_err = np.abs(preds_real - labels_real) * mask
        metrics = {}
        normalized_per_target = []  # (name, normalized_mae, is_well_supported) for targets with eval coverage
        for j, name in enumerate(TARGET_SHORT_NAMES):
            denom = mask[:, j].sum()
            if denom > 0:
                raw_mae = float(abs_err[:, j].sum() / denom)
                metrics[f"mae_{name}"] = raw_mae
                # Unit-free version: raw MAE (in the target's own real units, e.g.
                # GPa or %) divided by that target's TRAIN-set std. This is what
                # makes targets on wildly different scales (um, g/cm^3, HV, MPa,
                # %, GPa) comparable/poolable at all -- summing raw absolute
                # errors across those units (the old "mae_overall_masked") lets
                # whichever target happens to have the largest scale (or a noisy
                # outlier on a sparse target) dominate the aggregate regardless
                # of how good the model actually is on everything else.
                normalized = raw_mae / target_std[j] if target_std[j] > 1e-8 else raw_mae
                normalized_per_target.append((name, normalized, bool(well_supported_flags[j])))

        if normalized_per_target:
            metrics["mae_normalized_avg"] = float(np.mean([n for _, n, _ in normalized_per_target]))

        well_supported_vals = [n for _, n, is_ws in normalized_per_target if is_ws]
        if well_supported_vals:
            # This is the metric actually used for model selection (see
            # metric_for_best_model below and the best-seed pick in main()):
            # restricted to targets with >= TARGET_WELL_SUPPORTED_MIN_OBS
            # observations dataset-wide, so a handful of noisy/near-constant
            # predictions on a data-starved target can't decide which
            # checkpoint "wins".
            metrics["mae_normalized_avg_well_supported"] = float(np.mean(well_supported_vals))
        elif "mae_normalized_avg" in metrics:
            # Defensive fallback only -- with 4 well-supported targets each
            # having 500+ rows dataset-wide, an eval split with literally zero
            # of them represented shouldn't happen in practice, but
            # Trainer's load_best_model_at_end requires this key to exist at
            # every evaluation once it's set as metric_for_best_model.
            metrics["mae_normalized_avg_well_supported"] = metrics["mae_normalized_avg"]

        overall_denom = mask.sum()
        if overall_denom > 0:
            # Kept for reference/comparability with earlier runs, but NOT used
            # for model selection -- see the docstring note above
            # TARGET_WELL_SUPPORTED_MIN_OBS for why this unnormalized pooled
            # metric is misleading on its own.
            metrics["mae_overall_masked"] = float(abs_err.sum() / overall_denom)
        return metrics

    seed_output_dir = os.path.join(args.output_dir, f"seed_{seed}")
    training_args = TrainingArguments(
        output_dir=seed_output_dir,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=args.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="mae_normalized_avg_well_supported",
        greater_is_better=False,
        logging_steps=args.logging_steps,
        report_to="none",
        use_cpu=not cuda_available,
        bf16=use_bf16,
        fp16=use_fp16,
        gradient_checkpointing=bool(args.gradient_checkpointing),
        label_names=["labels"],
        seed=seed,
    )

    trainer = MaskedRegressionTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    final_metrics = trainer.evaluate()
    print(f"[seed {seed}] Final per-target masked MAE (original units):")
    for j, name in enumerate(TARGET_SHORT_NAMES):
        key = f"eval_mae_{name}"
        if key in final_metrics:
            tag = "well-supported" if well_supported_flags[j] else "SPARSE, unstable"
            print(f"  {name:28s} {final_metrics[key]:10.3f}   ({tag}, n={int(total_obs_per_target[j])})")
    print("  ---")
    if "eval_mae_normalized_avg_well_supported" in final_metrics:
        print(f"  {'normalized avg (well-supported only, used for model selection)':66s} {final_metrics['eval_mae_normalized_avg_well_supported']:.4f}")
    if "eval_mae_normalized_avg" in final_metrics:
        print(f"  {'normalized avg (all targets)':66s} {final_metrics['eval_mae_normalized_avg']:.4f}")
    if "eval_mae_overall_masked" in final_metrics:
        print(f"  {'raw pooled MAE (old metric -- units-mixed, not for comparison)':66s} {final_metrics['eval_mae_overall_masked']:.3f}")

    # Training-set physics descriptors, saved so predict_alloy() can flag when a
    # query composition is far outside anything the model actually trained on
    # (see nearest_training_distance / OOD_WARNING_THRESHOLD below). Stored per
    # UNIQUE alloy (not per row) to keep the file small and avoid bias toward
    # alloys that happened to have many test rows.
    train_unique_keys = sorted(set(canonical_keys[i] for i in train_idx))
    train_descriptor_lookup = {}
    for i in train_idx:
        key = canonical_keys[i]
        if key not in train_descriptor_lookup:
            train_descriptor_lookup[key] = compute_physics_descriptors(df.iloc[i][COL_FORMULA])
    train_descriptors = [list(train_descriptor_lookup[k]) for k in train_unique_keys]

    # Save this seed's model + scaling to disk IMMEDIATELY, then drop it from
    # memory, rather than returning the model object to be held onto until
    # every other seed has also finished. With --num_seeds > 1, keeping every
    # seed's full model resident in RAM/VRAM simultaneously (only picking the
    # best one at the very end) risks OOM for no benefit -- main() only ever
    # needs the WINNING seed's weights, which it gets by copying this
    # directory's files, not by holding the model object in Python memory.
    checkpoint_dir = os.path.join(seed_output_dir, "checkpoint")
    os.makedirs(checkpoint_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(checkpoint_dir, "model.pt"))
    tokenizer.save_pretrained(checkpoint_dir)
    with open(os.path.join(checkpoint_dir, "target_scaling.json"), "w") as f:
        json.dump(
            {
                "target_names": TARGET_SHORT_NAMES,
                "target_columns": TARGET_COLUMNS,
                "mean": target_mean.tolist(),
                "std": target_std.tolist(),
                "base_model_name": args.model_name,
                "aux_feature_names": AUX_FEATURE_NAMES,
                "aux_mean": aux_mean.tolist(),
                "aux_std": aux_std.tolist(),
                "train_descriptors": train_descriptors,
                "seed": seed,
            },
            f,
            indent=2,
        )
    del model, trainer
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        "seed": seed,
        "metrics": final_metrics,
        "checkpoint_dir": checkpoint_dir,
    }


def save_checkpoint(result: dict, args):
    """Copy one run_one_seed() result's on-disk checkpoint to <output_dir>/final,
    in the format predict_alloy() expects. Operates on files, not an in-memory
    model object -- see the comment in run_one_seed for why."""
    import shutil

    final_dir = os.path.join(args.output_dir, "final")
    if os.path.exists(final_dir):
        shutil.rmtree(final_dir)
    shutil.copytree(result["checkpoint_dir"], final_dir)
    print(f"Saved fine-tuned regression model + target scaling to {final_dir}")
    print("Use predict_alloy() in this file (pass model_dir=final_dir) to query it, e.g.:")
    print('    predict_alloy(final_dir, "Al1 Co1 Fe1 Ni1", test_temp_C=25)')


# ----------------------------------------------------------------------------
# Inference: "ask a question, get an answer" convenience wrapper
# ----------------------------------------------------------------------------

OOD_DISTANCE_THRESHOLD = 3.0  # in z-scored physics-descriptor space; see nearest_training_distance


def nearest_training_distance(formula: str, scaling: dict) -> float:
    """Euclidean distance (in the training set's own z-scored physics-descriptor
    space) from this composition to its nearest neighbor among the alloys the
    model actually trained on. Large distance = the model is extrapolating
    into composition space it has no real support for, and any prediction
    there should be treated with much less confidence than an interpolation.
    """
    train_desc = np.array(scaling["train_descriptors"], dtype=np.float32)  # (N, 4): delta, VEC, chi_std, Smix/R
    d_mean, d_std = train_desc.mean(axis=0), train_desc.std(axis=0)
    d_std[d_std < 1e-6] = 1.0
    query = np.array(compute_physics_descriptors(formula), dtype=np.float32)
    train_z = (train_desc - d_mean) / d_std
    query_z = (query - d_mean) / d_std
    dists = np.linalg.norm(train_z - query_z, axis=1)
    return float(dists.min())


def predict_alloy(
    model_dir: str,
    formula: str,
    microstructure: str = None,
    processing: str = None,
    phase_class: str = None,
    test_type: str = None,
    test_temp_C: float = None,
    O_content_wppm: float = None,
    N_content_wppm: float = None,
):
    """Load a fine-tuned checkpoint (saved by main() into <output_dir>/final)
    and predict all target properties for a given alloy + conditions.

    This is the practical answer to "what is the yield strength of alloy X":
    there's no separate natural-language Q&A step -- you call this with the
    formula (any element order -- composition is canonicalized internally, so
    permutations of the same alloy always give the identical prediction) and
    whatever conditions you know (test_temp_C, and O/N interstitial content
    if measured -- all three genuinely affect mechanical properties), and
    read off preds["YS_MPa"], etc.

    Example:
        predict_alloy("./heabert-mpea-regression/final", "Al1 Co1 Fe1 Ni1", test_temp_C=25)
        predict_alloy("./heabert-mpea-regression/final", "Fe1 Co1 Al1 Ni1", test_temp_C=25)  # same alloy, different element order -> identical result
    """
    with open(os.path.join(model_dir, "target_scaling.json")) as f:
        scaling = json.load(f)

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = MultiTaskRegressionModel(scaling["base_model_name"], num_targets=len(scaling["target_names"]))
    state_dict = torch.load(os.path.join(model_dir, "model.pt"), map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    fake_row = pd.Series(
        {
            COL_FORMULA: formula,
            COL_MICROSTRUCTURE: microstructure,
            COL_PROCESSING: processing,
            COL_PHASE_CLASS: phase_class,
            COL_TEST_TYPE: test_type,
            COL_TEST_TEMP: test_temp_C,
            COL_O_CONTENT: O_content_wppm,
            COL_N_CONTENT: N_content_wppm,
        }
    )
    text = build_text_for_row(fake_row, row_idx=0)
    aux_raw = np.array(build_aux_features_for_row(fake_row), dtype=np.float32)
    aux_mean = np.array(scaling["aux_mean"])
    aux_std = np.array(scaling["aux_std"])
    aux_norm = (aux_raw - aux_mean) / aux_std
    for k in range(_N_CONDITIONS):
        vidx, kidx = 2 * k, 2 * k + 1
        aux_norm[kidx] = aux_raw[kidx]  # each known-flag stays a raw 0/1, matching training
        if aux_raw[kidx] == 0:
            aux_norm[vidx] = 0.0  # unknown condition -> exactly neutral, no guessed value, matching training

    enc = tokenizer([text], truncation=True, max_length=256, padding="max_length", return_tensors="pt")
    aux = torch.tensor([aux_norm], dtype=torch.float32)

    with torch.no_grad():
        out = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"], aux_features=aux)
    preds_std = out["logits"].numpy()[0]
    mean = np.array(scaling["mean"])
    std = np.array(scaling["std"])
    preds_real = preds_std * std + mean

    result = dict(zip(scaling["target_names"], preds_real.tolist()))
    result["__text_used__"] = text

    warnings = []
    if test_temp_C is None:
        warnings.append(
            "No test_temp_C given -- the model was told 'temperature unknown' rather than "
            "assuming any specific value (e.g. room temperature), so this prediction reflects "
            "no temperature information at all. Since results genuinely vary with test "
            "temperature, give the real value if you have it for a more reliable prediction."
        )
    if "train_descriptors" in scaling and scaling["train_descriptors"]:
        ood_dist = nearest_training_distance(formula, scaling)
        result["__ood_distance__"] = ood_dist
        if ood_dist > OOD_DISTANCE_THRESHOLD:
            warnings.append(
                f"This composition is far from anything in the training data "
                f"(z-score distance {ood_dist:.1f} to the nearest training alloy's "
                f"composition descriptors). Treat this prediction as a rough "
                f"extrapolation, not a reliable estimate -- the model has little "
                f"real support for alloys this different from what it trained on."
            )
    if warnings:
        result["__warning__"] = " ".join(warnings)
    return result


if __name__ == "__main__":
    main()
