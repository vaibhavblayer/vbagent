"""Auto-tagger for math lenses on ideas.

Rule-based: parses formulas for math keywords and uses topic→lens
affinity tables. No LLM calls needed.
"""

from __future__ import annotations

import re

from vbagent.ideas.models import Idea, MATH_LENSES


# ---------------------------------------------------------------------------
# Formula → lens detection patterns
# ---------------------------------------------------------------------------

_FORMULA_PATTERNS: dict[str, list[str]] = {
    "calculus": [
        r"\\int", r"\\frac\{d", r"\\partial", r"\\lim",
        r"\\sum_", r"\\prod_", r"\\infty", r"dx", r"dt", r"d\\theta",
        r"\\nabla", r"\\divergence", r"\\curl",
    ],
    "vectors": [
        r"\\vec\{", r"\\hat\{", r"\\cdot", r"\\times",
        r"\\cross", r"\\mathbf\{", r"\\boldsymbol",
        r"\\hat\{i\}", r"\\hat\{j\}", r"\\hat\{k\}",
    ],
    "matrix": [
        r"\\det", r"\\begin\{[pbvBV]?matrix\}", r"\\eigenvalue",
        r"\\text\{rank\}", r"\\text\{trace\}", r"\\text\{adj\}",
        r"\\begin\{vmatrix\}",
    ],
    "probability": [
        r"P\(", r"P\\left\(", r"\\binom", r"E\[", r"E\\left\[",
        r"\\text\{Var\}", r"\\sigma", r"\\mu",
        r"Bayes", r"\\text\{Bernoulli\}",
    ],
    "combinatorics": [
        r"\\binom", r"\\perm", r"C_", r"P_", r"n!",
        r"\\text\{nCr\}", r"\\text\{nPr\}",
        r"\\factorial",
    ],
    "trigonometry": [
        r"\\sin", r"\\cos", r"\\tan", r"\\cot", r"\\sec", r"\\csc",
        r"\\arcsin", r"\\arccos", r"\\arctan",
        r"\\sin\^{-1}", r"\\cos\^{-1}", r"\\tan\^{-1}",
    ],
    "coordinate": [
        r"\\text\{slope\}", r"\\text\{distance\}",
        r"\\text\{midpoint\}", r"\\text\{locus\}",
        r"y = mx", r"ax\^2",
    ],
    "algebra": [
        r"\\sqrt", r"\\frac", r"\\log", r"\\ln",
        r"\\text\{roots\}", r"\\text\{quadratic\}",
    ],
}


# ---------------------------------------------------------------------------
# Topic → natural lens affinity
# ---------------------------------------------------------------------------

_TOPIC_NATURAL: dict[str, list[str]] = {
    # Physics
    "mechanics": ["algebra", "vectors", "calculus"],
    "gravitation": ["algebra", "calculus"],
    "fluids": ["algebra", "calculus"],
    "thermodynamics": ["algebra", "calculus"],
    "waves": ["trigonometry", "calculus"],
    "optics": ["trigonometry", "algebra"],
    "electrostatics": ["calculus", "vectors", "algebra"],
    "current-electricity": ["algebra", "matrix"],
    "magnetism": ["vectors", "calculus"],
    "electromagnetic-induction": ["calculus", "vectors"],
    "alternating-current": ["trigonometry", "algebra", "calculus"],
    "modern-physics": ["algebra"],
    "shm": ["trigonometry", "calculus"],
    "rotational-motion": ["vectors", "calculus", "algebra"],
    "work-energy-power": ["calculus", "algebra"],
    "center-of-mass": ["algebra", "calculus"],
    "kinetic-theory": ["probability", "algebra"],
    # Chemistry
    "physical-chemistry": ["algebra", "calculus"],
    "electrochemistry": ["algebra"],
    "kinetics": ["calculus", "algebra"],
    "equilibrium": ["algebra"],
    "thermochemistry": ["algebra"],
    # Mathematics (natural = the topic itself)
    "calculus": ["calculus"],
    "algebra": ["algebra"],
    "coordinate-geometry": ["coordinate", "algebra"],
    "probability": ["probability", "combinatorics"],
    "vectors-3d": ["vectors"],
    "matrices": ["matrix"],
    "trigonometry": ["trigonometry"],
}

# Topic → compatible lenses (what the idea *could* be reframed into)
_TOPIC_COMPATIBLE: dict[str, list[str]] = {
    "mechanics": ["matrix", "probability", "combinatorics", "coordinate"],
    "gravitation": ["vectors", "coordinate"],
    "fluids": ["vectors"],
    "thermodynamics": ["probability", "combinatorics"],
    "waves": ["algebra", "vectors", "probability"],
    "optics": ["coordinate", "matrix", "vectors"],
    "electrostatics": ["coordinate", "matrix", "probability"],
    "current-electricity": ["calculus", "probability"],
    "magnetism": ["matrix", "probability", "combinatorics", "trigonometry"],
    "electromagnetic-induction": ["algebra", "trigonometry", "matrix"],
    "alternating-current": ["vectors", "matrix"],
    "modern-physics": ["probability", "calculus"],
    "shm": ["vectors", "algebra", "coordinate"],
    "rotational-motion": ["matrix", "coordinate"],
    "work-energy-power": ["vectors", "coordinate"],
    "center-of-mass": ["vectors", "coordinate"],
    "kinetic-theory": ["calculus", "combinatorics"],
    "physical-chemistry": ["probability", "matrix"],
    "electrochemistry": ["calculus"],
    "kinetics": ["probability"],
    "equilibrium": ["calculus", "matrix"],
}


def _detect_formula_lenses(formulas: list[str], idea_latex: str) -> set[str]:
    """Detect lenses from formula content."""
    combined = " ".join(formulas) + " " + idea_latex
    found: set[str] = set()
    for lens, patterns in _FORMULA_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, combined):
                found.add(lens)
                break
    return found


def tag_lenses(idea: Idea) -> Idea:
    """Auto-tag natural_lenses and compatible_lenses on an Idea.

    Combines formula detection + topic affinity. Modifies in place and returns.
    """
    topic = idea.topic.lower().strip()

    # Natural lenses: from formulas + topic affinity
    natural: set[str] = set()

    # Formula-based detection
    natural |= _detect_formula_lenses(idea.formulas, idea.idea_latex)

    # Topic affinity
    topic_natural = _TOPIC_NATURAL.get(topic, [])
    natural |= set(topic_natural)

    # If nothing detected, default to algebra
    if not natural:
        natural.add("algebra")

    # Compatible lenses: everything the topic supports minus what's already natural
    compatible: set[str] = set()
    topic_compat = _TOPIC_COMPATIBLE.get(topic, [])
    compatible |= set(topic_compat)
    compatible -= natural  # don't duplicate

    # Ensure all lenses are valid
    idea.natural_lenses = sorted(l for l in natural if l in MATH_LENSES)
    idea.compatible_lenses = sorted(l for l in compatible if l in MATH_LENSES)

    return idea
