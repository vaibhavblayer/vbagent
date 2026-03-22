"""Pydantic models for the Paper Orchestrator.

Covers syllabus, paper state, generation targets, coverage analysis,
QA results, hints, and generation reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Syllabus
# ---------------------------------------------------------------------------

VALID_SUBJECTS = {"physics", "chemistry", "mathematics", "biology"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}

# Default tone presets per subject — curated thinking styles that influence generation.
# Users can also pass free-form tone strings; these are just convenient shortcuts.
TONE_PRESETS: dict[str, dict[str, str]] = {
    "physics": {
        "symmetry-heavy": "Exploit symmetry arguments (Gauss's law, mirror symmetry, rotational invariance). Avoid brute-force coordinate integration when symmetry gives the answer directly.",
        "energy-methods": "Prefer energy, work-energy theorem, Lagrangian, or Hamiltonian approaches over direct force analysis. Frame problems where energy conservation or virtual work is the natural path.",
        "conceptual": "Qualitative reasoning with minimal calculation. 'What happens if...' style. Focus on physical intuition, limiting cases, and conceptual traps.",
        "calculus-first": "Rigorous derivation-heavy problems. Integration, differentiation, and differential equations are central to the solution path.",
        "geometric-intuition": "Visual and geometric reasoning — vector diagrams, graphical methods, phase-space plots. Problems where drawing the right picture is half the solution.",
        "dimensional-analysis": "Problems solvable or verifiable through dimensional arguments, scaling laws, and order-of-magnitude estimation.",
    },
    "chemistry": {
        "mechanistic": "Focus on reaction mechanisms, electron flow, arrow pushing, and intermediate stability. Problems that test understanding of 'why' a reaction proceeds.",
        "conceptual": "Qualitative reasoning about periodic trends, bonding, molecular geometry, and intermolecular forces. Minimal numerical computation.",
        "numerical": "Calculation-heavy — molarity, stoichiometry, equilibrium constants, pH, buffer calculations. Precision and unit handling matter.",
        "organic-reasoning": "Stereochemistry, functional group transformations, retrosynthetic analysis. Problems requiring multi-step organic thinking.",
        "thermodynamic": "ΔG, ΔH, entropy-driven reasoning, spontaneity, Hess's law, Born-Haber cycles. Frame problems around energy and feasibility.",
    },
    "mathematics": {
        "algebraic": "Manipulation-heavy — identities, substitutions, factoring tricks, algebraic transformations as the core technique.",
        "geometric": "Coordinate geometry, geometric proofs, transformation-based reasoning. Visual and spatial thinking central.",
        "calculus-first": "Limits, continuity, differentiation, integration as the primary tools. Problems where calculus is the natural language.",
        "proof-style": "Rigorous logical deduction, theorem application, proof by contradiction or induction. Mathematical maturity required.",
        "pattern-recognition": "Sequences, series, recurrence relations, spotting hidden structure. Problems that reward noticing patterns.",
        "competition-style": "Olympiad-flavored — elegant tricks, non-standard approaches, problems with surprising shortcuts.",
    },
}

# Flat set of all preset names for quick validation
ALL_TONE_PRESETS: set[str] = set()
for _presets in TONE_PRESETS.values():
    ALL_TONE_PRESETS.update(_presets.keys())


class SyllabusSubtopic(BaseModel):
    """A subtopic within a syllabus topic."""

    name: str
    concepts: list[str] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    current_count: int = 0

    @field_validator("difficulty_distribution")
    @classmethod
    def _validate_difficulty_keys(cls, v: dict[str, int]) -> dict[str, int]:
        for key in v:
            if key not in VALID_DIFFICULTIES:
                raise ValueError(f"Invalid difficulty key: {key}. Must be one of {VALID_DIFFICULTIES}")
        return v


class SyllabusTopic(BaseModel):
    """A top-level topic in the syllabus."""

    name: str
    subtopics: list[SyllabusSubtopic] = Field(default_factory=list)
    target_count: int = 0
    current_count: int = 0


class Syllabus(BaseModel):
    """Full syllabus tree for a paper."""

    subject: str
    topics: list[SyllabusTopic] = Field(default_factory=list)
    created_from: Literal["extracted", "manual"] = "extracted"
    total_target: int = 0

    @field_validator("subject")
    @classmethod
    def _validate_subject(cls, v: str) -> str:
        v = v.lower()
        if v not in VALID_SUBJECTS:
            raise ValueError(f"Invalid subject: {v}. Must be one of {VALID_SUBJECTS}")
        return v


# ---------------------------------------------------------------------------
# Paper State & Problem Entry
# ---------------------------------------------------------------------------

class ProblemEntry(BaseModel):
    """Tracks a single problem in the paper."""

    serial: int
    filename: str
    subject: str
    topic: str
    subtopic: str = ""
    difficulty: str = "medium"
    question_type: str = "subjective"
    concepts: list[str] = Field(default_factory=list)
    source: Literal["scanned", "generated", "seeded"] = "generated"
    seed_from: list[int] = Field(default_factory=list)
    qa_status: Literal["pending", "passed", "failed"] = "pending"
    solution_status: Literal["none", "inline", "generated", "pending"] = "none"
    hint_status: Literal["none", "generated"] = "none"
    diagram_status: Literal["none", "generated", "inline"] = "none"
    diagram_description: str = ""  # Text description of diagram needed
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("serial")
    @classmethod
    def _serial_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("serial must be >= 1")
        return v

    @field_validator("filename")
    @classmethod
    def _filename_tex(cls, v: str) -> str:
        if not v.endswith(".tex"):
            raise ValueError("filename must end with .tex")
        return v


class PaperState(BaseModel):
    """Persistent state for a paper, stored as manifest.json."""

    paper_id: str
    subject: str
    base_dir: str = "agentic"
    problems: list[ProblemEntry] = Field(default_factory=list)
    syllabus_path: str = "syllabus.json"
    serial_numbering: bool = True
    tone: str = ""  # Paper tone/thinking style — preset name or free-form text
    # Presets: see TONE_PRESETS in this module (e.g. "symmetry-heavy", "mechanistic", "competition-style")
    # Free-form: "focus on energy methods and symmetry arguments, avoid brute-force coordinate geometry"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self) -> None:
        self.updated_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Generation Target & Coverage
# ---------------------------------------------------------------------------

class GenerationTarget(BaseModel):
    """Specification for a problem to generate."""

    topic: str
    subtopic: str = ""
    difficulty: str = "medium"
    question_type: str = "subjective"
    concepts: list[str] = Field(default_factory=list)
    strategy: Literal["idea_generator", "cross_topic", "combiner"] = "idea_generator"
    seed_ideas: list[str] = Field(default_factory=list)


class TopicCoverage(BaseModel):
    """Coverage analysis for a single topic."""

    topic: str
    target: int
    current: int
    coverage_pct: float
    missing_difficulties: list[str] = Field(default_factory=list)
    missing_subtopics: list[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    """Full coverage analysis across all topics."""

    overall_coverage_pct: float
    topic_coverages: list[TopicCoverage] = Field(default_factory=list)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    recommended_targets: list[GenerationTarget] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Generation Results
# ---------------------------------------------------------------------------

class GeneratedProblemResult(BaseModel):
    """Output from ProblemGenerator for a single problem."""

    problem_tex: str
    solution_tex: str = ""
    combined_tex: str = ""
    target: GenerationTarget
    strategy_used: str
    diagram_description: str = ""  # From idea generator — text description of needed diagram


class GenerationReport(BaseModel):
    """Summary of a generation run (single or batch)."""

    total_requested: int
    total_generated: int
    total_passed_qa: int = 0
    problems: list[ProblemEntry] = Field(default_factory=list)
    coverage_before: float = 0.0
    coverage_after: float = 0.0


class SolutionReport(BaseModel):
    """Summary of an independent solution generation run."""

    total: int
    solved: int
    failed: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------

class QACheckResult(BaseModel):
    """Result from a single quality checker."""

    checker: str
    passed: bool
    issues: list[str] = Field(default_factory=list)
    auto_fixed: bool = False


class QAResult(BaseModel):
    """Aggregated QA result across all checkers."""

    passed: bool
    checks: list[QACheckResult] = Field(default_factory=list)
    fixed_tex: Optional[str] = None


# ---------------------------------------------------------------------------
# Hints
# ---------------------------------------------------------------------------

class HintResult(BaseModel):
    """Output from the hint generator agent."""

    hint_text: str
    hint_style: Literal["conceptual", "equation", "direction"] = "conceptual"
    key_concept: str = ""


class HintReport(BaseModel):
    """Summary of a hint generation run."""

    total: int
    generated: int
    failed: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Post-generation classification
# ---------------------------------------------------------------------------

class PostGenClassification(BaseModel):
    """Lightweight classification extracted from generated LaTeX (text-only, no images)."""

    subtopic: str = ""
    concepts: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    question_type: str = "subjective"
    brief_description: str = ""
