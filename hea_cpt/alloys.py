"""Exact composition-ratio comparison, NOT a phase or property predictor."""

import re
from fractions import Fraction

ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
               "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
               "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
               "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())
COMPONENT = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?|\.\d+)?")
COEFFICIENT = re.compile(r"\d+(?:\.\d+)?|\.\d+")


def _components(formula, position):
    """Consume components until the end of the formula or an unmatched closing parenthesis."""
    coefficients = {}
    while position < len(formula) and formula[position] != ")":
        if formula[position] == "(":
            inner, position = _components(formula, position + 1)
            if not inner or position >= len(formula) or formula[position] != ")":
                raise ValueError(f"Unsupported or invalid formula: {formula}")
            position += 1
            multiplier_match = COEFFICIENT.match(formula, position)
            multiplier = Fraction(multiplier_match.group()) if multiplier_match else Fraction(1)
            if multiplier_match is not None:
                position = multiplier_match.end()
            if multiplier <= 0:
                raise ValueError("All coefficients must be positive.")
            for element, amount in inner.items():
                coefficients[element] = coefficients.get(element, Fraction(0)) + amount * multiplier
        else:
            match = COMPONENT.match(formula, position)
            if match is None or match[1] not in ELEMENTS:
                raise ValueError(f"Unsupported or invalid formula: {formula}")
            value = Fraction(match[2] or "1")
            if value <= 0:
                raise ValueError("All coefficients must be positive.")
            coefficients[match[1]] = coefficients.get(match[1], Fraction(0)) + value
            position = match.end()
    return coefficients, position


def normalized_composition(formula):
    """Parse element/decimal ratios and parenthesized group algebra; implicit coefficients are one.

    A parenthesized group multiplies every inner coefficient by the outer group coefficient,
    e.g. (MnCo0.2)0.1 contributes Mn 0.1 and Co 0.02. wt%, at% annotations, ranges, aliases,
    processing state and phase identity are not parsed.
    """
    coefficients, position = _components(formula, 0)
    if not coefficients or position != len(formula):
        raise ValueError(f"Unsupported or invalid formula: {formula}")
    total = sum(coefficients.values())
    return {element: amount / total for element, amount in sorted(coefficients.items())}


def compare_compositions(first, second):
    """Compare two formulas for identical normalized atomic composition.

    Returns a dict with the boolean verdict, each side's atomic fractions as
    exact-arithmetic strings, and the stated assumptions and limitation.
    """
    a, b = normalized_composition(first), normalized_composition(second)
    return {"same_normalized_composition": a == b,
            "first_atomic_fractions": {element: str(value) for element, value in a.items()},
            "second_atomic_fractions": {element: str(value) for element, value in b.items()},
            "assumptions": "Coefficients are atomic ratios; omitted coefficients are one; "
                           "parenthesized groups multiply every inner coefficient.",
            "limitation": "Equal composition does not imply equal processing, microstructure, phase or properties."}
