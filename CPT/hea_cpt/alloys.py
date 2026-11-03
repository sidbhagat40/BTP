"""Exact composition-ratio comparison, NOT a phase or property predictor."""

import re
from fractions import Fraction

ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
               "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
               "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
               "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())
COMPONENT = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?|\.\d+)?")


def normalized_composition(formula):
    """Parse simple element/decimal ratios; implicit coefficients are one.

    Does not parse wt%, parentheses, ranges, aliases, processing state or phase identity.
    """
    coefficients, position = {}, 0
    for match in COMPONENT.finditer(formula):
        if match.start() != position or match[1] not in ELEMENTS:
            raise ValueError(f"Unsupported or invalid simple formula: {formula}")
        value = Fraction(match[2] or "1")
        if value <= 0:
            raise ValueError("All coefficients must be positive.")
        coefficients[match[1]] = coefficients.get(match[1], Fraction(0)) + value
        position = match.end()
    if not coefficients or position != len(formula):
        raise ValueError(f"Unsupported or invalid simple formula: {formula}")
    total = sum(coefficients.values())
    return {element: amount / total for element, amount in sorted(coefficients.items())}


def compare_compositions(first, second):
    a, b = normalized_composition(first), normalized_composition(second)
    return {"same_normalized_composition": a == b,
            "first_atomic_fractions": {element: str(value) for element, value in a.items()},
            "second_atomic_fractions": {element: str(value) for element, value in b.items()},
            "assumptions": "Coefficients are atomic ratios; omitted coefficients are one.",
            "limitation": "Equal composition does not imply equal processing, microstructure, phase or properties."}
