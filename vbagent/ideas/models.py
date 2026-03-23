"""Data models for the Idea Store system.

Defines the Idea, CombinationRecord, and IdeaStore schema,
plus all taxonomy constants (lenses, topic codes, difficulty scale).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Math Lenses — the mathematical tools that can frame a problem
# ---------------------------------------------------------------------------

MATH_LENSES: list[str] = [
    "algebra",          # quadratic, inequalities, logarithms, sequences
    "trigonometry",     # identities, inverse trig, parametric
    "vectors",          # dot/cross product, unit vectors, projections
    "calculus",         # integration, differentiation, limits, series
    "matrix",           # determinants, eigenvalues, system of equations
    "probability",      # conditional, Bayes, distributions, expectation
    "combinatorics",    # PnC, binomial, counting arguments
    "coordinate",       # coordinate geometry, transformations, locus
]


# ---------------------------------------------------------------------------
# Subject & Topic codes for systematic IDs
# ---------------------------------------------------------------------------

SUBJECT_CODES: dict[str, str] = {
    "physics": "PHY",
    "chemistry": "CHM",
    "mathematics": "MAT",
}

TOPIC_CODES: dict[str, str] = {
    # Physics
    "mechanics": "MEC",
    "gravitation": "GRV",
    "fluids": "FLD",
    "thermodynamics": "THR",
    "waves": "WAV",
    "optics": "OPT",
    "electrostatics": "ELS",
    "current-electricity": "CUR",
    "magnetism": "MAG",
    "electromagnetic-induction": "EMI",
    "alternating-current": "ALC",
    "modern-physics": "MOD",
    "semiconductors": "SEM",
    "units-dimensions": "UND",
    "shm": "SHM",
    "rotational-motion": "ROT",
    "work-energy-power": "WEP",
    "center-of-mass": "COM",
    "kinetic-theory": "KTG",
    "heat-transfer": "HTR",
    "ray-optics": "ROP",
    "wave-optics": "WOP",
    "nuclear-physics": "NUC",
    "communication": "CMN",
    # Chemistry
    "organic": "ORG",
    "inorganic": "INO",
    "physical-chemistry": "PCH",
    "electrochemistry": "ECH",
    "kinetics": "KIN",
    "equilibrium": "EQB",
    "thermochemistry": "TCH",
    "solutions": "SOL",
    "solid-state": "SLD",
    "surface-chemistry": "SFC",
    "coordination": "CRD",
    "periodic-table": "PRT",
    "chemical-bonding": "CBN",
    "atomic-structure": "ATS",
    "redox": "RDX",
    "polymers": "PLY",
    "biomolecules": "BIO",
    # Mathematics
    "calculus": "CAL",
    "algebra": "ALG",
    "coordinate-geometry": "COG",
    "probability": "PRB",
    "vectors-3d": "V3D",
    "matrices": "MTX",
    "complex-numbers": "CPN",
    "sequences-series": "SQS",
    "trigonometry": "TRG",
    "differential-equations": "DEQ",
    "statistics": "STA",
    "permutations-combinations": "PNC",
    "binomial-theorem": "BNM",
    "limits-continuity": "LMC",
    "definite-integrals": "DIN",
    "indefinite-integrals": "IIN",
    "area-under-curves": "AUC",
    "3d-geometry": "3DG",
    "conic-sections": "CON",
    "straight-lines": "STL",
    "circles": "CIR",
    "sets-relations": "SET",
    "mathematical-reasoning": "MRS",
}


# ---------------------------------------------------------------------------
# Difficulty scale: 1–10 with exam-anchored descriptions
# ---------------------------------------------------------------------------

DIFFICULTY_ANCHORS: dict[int, str] = {
    1:  "Direct recall / definition",
    2:  "Single formula, plug values",
    3:  "One concept, one small twist (NCERT back-exercise)",
    4:  "Two concepts chained, algebraic manipulation (NEET level)",
    5:  "Multi-step, careful setup (easy JEE Main)",
    6:  "Choose right approach from multiple options (standard JEE Main)",
    7:  "Combines 2-3 concepts, mathematical fluency (hard JEE Main / easy JEE Adv)",
    8:  "Non-obvious approach, multi-concept, calculus/matrix (standard JEE Advanced)",
    9:  "Deep insight, elegant trick, heavy math (hard JEE Advanced)",
    10: "Olympiad-adjacent, creative problem-solving, non-standard techniques",
}

DIFFICULTY_MAP: dict[str, int] = {
    "easy": 3,
    "medium": 5,
    "hard": 8,
    "very-hard": 9,
    "olympiad": 10,
}


# Difficulty ↔ Lens guidance (not hard rules — agent can override)
DIFFICULTY_LENS_GUIDANCE: dict[str, list[str]] = {
    "1-3":  ["algebra", "trigonometry"],
    "4-5":  ["algebra", "trigonometry", "vectors", "calculus", "coordinate"],
    "6-7":  ["calculus", "vectors", "coordinate", "probability"],
    "8-9":  ["matrix", "probability", "combinatorics", "calculus", "vectors"],
    "10":   ["matrix", "probability", "combinatorics", "calculus", "vectors", "coordinate"],
}


def parse_difficulty(value: str | int) -> int | tuple[int, int]:
    """Parse difficulty from CLI input.

    Accepts:
        - int 1-10
        - string "easy", "medium", "hard", "very-hard", "olympiad"
        - range string "4-7"

    Returns:
        int for single value, tuple (lo, hi) for range.
    """
    if isinstance(value, int):
        return max(1, min(10, value))

    value = str(value).strip().lower()

    # Named difficulty
    if value in DIFFICULTY_MAP:
        return DIFFICULTY_MAP[value]

    # Range like "4-7"
    if "-" in value:
        parts = value.split("-", 1)
        try:
            lo, hi = int(parts[0]), int(parts[1])
            return (max(1, min(10, lo)), max(1, min(10, hi)))
        except ValueError:
            pass

    # Plain int
    try:
        return max(1, min(10, int(value)))
    except ValueError:
        return DIFFICULTY_MAP.get(value, 5)


def difficulty_label(level: int) -> str:
    """Human-readable label for a difficulty level."""
    return DIFFICULTY_ANCHORS.get(level, f"Level {level}")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Idea(BaseModel):
    """A single unique idea in the store."""

    id: str = ""                                    # e.g. PHY-MAG-001
    text: str                                       # human-readable description
    formulas: list[str] = Field(default_factory=list)
    topic: str = ""                                 # e.g. "magnetism"
    subtopic: str = ""                              # e.g. "biot-savart"
    subject: str = "physics"
    natural_lenses: list[str] = Field(default_factory=list)
    compatible_lenses: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)  # filenames that contributed this idea
    idea_latex: str = ""                            # raw LaTeX from \begin{idea}...\end{idea}
    added_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def signature(self) -> str:
        """Normalized signature for deduplication.

        Uses synonym normalization and keyword extraction to catch
        semantically equivalent ideas like:
          "Magnetic field at centre of circular loop"
          "B at center of current loop"
        Both normalize to the same signature.
        """
        import re

        text = self.text

        # 1. Strip LaTeX commands and symbols
        clean = re.sub(r"\\[a-zA-Z]+\{?", "", text)
        clean = re.sub(r"[{}\\\$_^]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip().lower()

        # 2. Synonym normalization — map common physics phrasings
        for pattern, replacement in _SYNONYMS:
            clean = re.sub(pattern, replacement, clean)

        # 3. Remove filler words
        words = clean.split()
        words = [w for w in words if w not in _STOPWORDS]

        # 4. Sort words for order-independence
        #    "field magnetic circular loop" == "circular loop magnetic field"
        normalized = " ".join(sorted(words))

        return f"{self.subject}:{self.topic}:{normalized}"


# Synonym pairs: (regex_pattern, replacement)
# Applied in order to normalize common physics/chem/math phrasings
_SYNONYMS: list[tuple[str, str]] = [
    # Spelling variants
    (r"\bcentre\b", "center"),
    (r"\bcentre\b", "center"),
    (r"\bcolour\b", "color"),
    (r"\banalogue\b", "analog"),
    # Physics concept synonyms
    (r"\bemf\b", "electromotive force"),
    (r"\bemi\b", "electromagnetic induction"),
    (r"\bshm\b", "simple harmonic motion"),
    (r"\bcurrent[- ]carrying\b", "current"),
    (r"\bcurrent[- ]loop\b", "current loop"),
    (r"\bfield at center\b", "field center"),
    (r"\bfield at the center\b", "field center"),
    (r"\bat the center\b", "center"),
    (r"\bat center\b", "center"),
    (r"\bat the centre\b", "center"),
    (r"\bat centre\b", "center"),
    (r"\binduced emf\b", "induced electromotive force"),
    (r"\bfaradays law\b", "faraday law"),
    (r"\bfaraday's law\b", "faraday law"),
    (r"\bnewtons\b", "newton"),
    (r"\bnewton's\b", "newton"),
    (r"\bcoulombs\b", "coulomb"),
    (r"\bcoulomb's\b", "coulomb"),
    (r"\bgauss's\b", "gauss"),
    (r"\bgauss'\b", "gauss"),
    (r"\bamperes\b", "ampere"),
    (r"\bampere's\b", "ampere"),
    (r"\blenzs\b", "lenz"),
    (r"\blenz's\b", "lenz"),
    (r"\bbiot[- ]savart\b", "biot savart"),
    (r"\bkirchhoffs\b", "kirchhoff"),
    (r"\bkirchoff\b", "kirchhoff"),
    (r"\bkirchoff's\b", "kirchhoff"),
    (r"\bkirchhoff's\b", "kirchhoff"),
    (r"\bohms\b", "ohm"),
    (r"\bohm's\b", "ohm"),
    # Abbreviations
    (r"\bke\b", "kinetic energy"),
    (r"\bpe\b", "potential energy"),
    (r"\bcm\b", "center mass"),
    (r"\bcom\b", "center mass"),
    (r"\bfbd\b", "free body diagram"),
    (r"\bwep\b", "work energy power"),
    # Math
    (r"\bdifferentiation\b", "derivative"),
    (r"\bintegration\b", "integral"),
    # Remove articles and prepositions
    (r"\bof a\b", ""),
    (r"\bof the\b", ""),
    (r"\bdue to\b", ""),
    (r"\bin a\b", ""),
    (r"\bin the\b", ""),
    (r"\bon a\b", ""),
    (r"\bon the\b", ""),
    (r"\bfor a\b", ""),
    (r"\bfor the\b", ""),
    (r"\bby a\b", ""),
    (r"\bby the\b", ""),
    (r"\bwith a\b", ""),
    (r"\bwith the\b", ""),
]

_STOPWORDS: set[str] = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "by",
    "with", "from", "and", "or", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "shall", "should", "may", "might",
    "can", "could", "its", "it", "this", "that", "these", "those",
    "their", "them", "they", "we", "our", "us", "you", "your",
    "he", "she", "his", "her", "him", "when", "where", "which",
    "what", "who", "whom", "how", "why", "if", "then", "than",
    "so", "as", "but", "not", "no", "nor", "only", "also",
    "very", "just", "about", "between", "through", "during",
    "before", "after", "above", "below", "up", "down",
}


class CombinationRecord(BaseModel):
    """Tracks a generated combination to prevent duplicates."""

    combo_id: str = ""                              # e.g. VBP-PHY-MAG-001
    idea_ids: list[str] = Field(default_factory=list)
    lenses_used: list[str] = Field(default_factory=list)
    difficulty: int = 5
    question_type: str = "mcq_sc"
    output_file: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class IdeaStore(BaseModel):
    """The master idea store schema."""

    version: str = "1.0"
    subject: str = "physics"
    stats: dict[str, Any] = Field(default_factory=dict)
    ideas: list[Idea] = Field(default_factory=list)
    combinations: list[CombinationRecord] = Field(default_factory=list)
    counters: dict[str, int] = Field(default_factory=dict)  # topic_code -> next number
