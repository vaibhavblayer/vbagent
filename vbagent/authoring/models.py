"""Typed contracts for syllabus-driven problem authoring."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Subject = Literal["physics", "chemistry", "mathematics", "biology"]


class QuestionType(str, Enum):
    """Question types supported by generation and solution workflows."""

    MCQ_SINGLE = "mcq_sc"
    MCQ_MULTIPLE = "mcq_mc"
    SUBJECTIVE = "subjective"
    INTEGER = "integer"
    ASSERTION_REASON = "assertion_reason"
    PASSAGE = "passage"
    MATCH = "match"


class CognitiveLevel(str, Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class Representation(str, Enum):
    SYMBOLIC = "symbolic"
    NUMERICAL = "numerical"
    GRAPHICAL = "graphical"
    DIAGRAMMATIC = "diagrammatic"
    EXPERIMENTAL = "experimental"
    CONTEXTUAL = "contextual"


class DiagramPolicy(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    FORBIDDEN = "forbidden"


class SourceKind(str, Enum):
    ORIGINAL = "original"
    VARIANT = "variant"
    COMPLETION = "completion"


class VariantFamily(str, Enum):
    """Existing variant agents that satisfy the canonical MCQ contract."""

    NUMERICAL = "numerical"
    CONTEXT = "context"
    CONCEPTUAL = "conceptual"
    CALCULUS = "calculus"


class AcceptancePolicy(BaseModel):
    """Quality gates an item must satisfy before it counts as coverage."""

    model_config = ConfigDict(extra="forbid")

    require_structure_check: Literal[True] = True
    require_independent_solution: Literal[True] = True
    require_answer_agreement: Literal[True] = True
    require_syllabus_check: Literal[True] = True
    require_difficulty_check: Literal[True] = True
    difficulty_tolerance: int = Field(default=2, ge=0, le=5)
    require_compile: Literal[True] = True
    require_review: Literal[True] = True
    require_novelty_check: Literal[True] = True
    novelty_threshold: float = Field(default=0.88, ge=0.0, le=1.0)
    human_review_required: bool = False


class CatalogTopic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    aliases: tuple[str, ...] = ()
    description: str = ""


class CatalogChapter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    description: str = ""
    topics: tuple[CatalogTopic, ...]


class SyllabusCatalog(BaseModel):
    """A versioned syllabus snapshot with stable chapter and topic IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exam: str
    subject: Subject
    version: str
    source: str
    source_url: str = ""
    official_source_sha256: str = ""
    verified_at: str = ""
    allowed_question_types: tuple[QuestionType, ...] = tuple(QuestionType)
    exam_pattern_description: str = ""
    exam_pattern_source_url: str = ""
    exam_pattern_source_sha256: str = ""
    exam_pattern_verified_at: str = ""
    source_sha256: str
    chapters: tuple[CatalogChapter, ...]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "SyllabusCatalog":
        chapter_ids = [chapter.id for chapter in self.chapters]
        if len(chapter_ids) != len(set(chapter_ids)):
            raise ValueError("syllabus chapter IDs must be unique")
        topic_ids = [topic.id for chapter in self.chapters for topic in chapter.topics]
        if len(topic_ids) != len(set(topic_ids)):
            raise ValueError("syllabus topic IDs must be unique")
        if not self.chapters:
            raise ValueError("syllabus must contain at least one chapter")
        if any(not chapter.topics for chapter in self.chapters):
            raise ValueError("every syllabus chapter must contain at least one topic")
        if not self.allowed_question_types:
            raise ValueError("syllabus catalog must allow at least one question type")
        if len(self.allowed_question_types) != len(set(self.allowed_question_types)):
            raise ValueError("allowed question types must be unique")
        return self


def _default_question_types() -> dict[str, float]:
    return {QuestionType.MCQ_SINGLE.value: 1.0}


def _default_difficulties() -> dict[int, float]:
    return {5: 1.0}


def _default_cognitive_levels() -> dict[str, float]:
    return {
        CognitiveLevel.APPLY.value: 2.0,
        CognitiveLevel.ANALYZE.value: 1.0,
    }


def _default_representations() -> dict[str, float]:
    return {
        Representation.SYMBOLIC.value: 1.0,
        Representation.NUMERICAL.value: 1.0,
        Representation.CONTEXTUAL.value: 1.0,
    }


class AuthoringRequest(BaseModel):
    """User intent for a complete, inspectable authoring run."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exam: str = Field(min_length=1)
    subject: Subject
    count: int = Field(default=1, ge=1, le=100_000)
    chapter: str | None = None
    topics: list[str] = Field(default_factory=list)
    syllabus_path: str | None = None
    expected_syllabus_version: str | None = None

    question_types: dict[str, float] = Field(default_factory=_default_question_types)
    difficulties: dict[int, float] = Field(default_factory=_default_difficulties)
    cognitive_levels: dict[str, float] = Field(default_factory=_default_cognitive_levels)
    representations: dict[str, float] = Field(default_factory=_default_representations)
    reasoning_lenses: dict[str, float] = Field(default_factory=dict)
    construction_families: dict[str, float] = Field(default_factory=dict)
    diagram_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    passage_question_count: int = Field(default=3, ge=2, le=10)

    required_concepts: list[str] = Field(default_factory=list)
    forbidden_concepts: list[str] = Field(default_factory=list)
    seed_ideas: list[str] = Field(default_factory=list)
    tone: str = ""
    seed: int = 0
    existing_accepted_counts: dict[str, int] = Field(default_factory=dict)
    acceptance: AcceptancePolicy = Field(default_factory=AcceptancePolicy)
    include_solution: bool = True
    include_idea: bool = True
    completion_parent_spec_ids: list[str] = Field(default_factory=list)

    # Controlled accepted-parent variants. These fields are normally populated
    # by ``execute_variants`` rather than entered directly by users.
    variant_parent_spec_id: str | None = None
    variant_parent_latex: str = ""
    variant_parent_artifact_sha256: str = ""
    variant_lineage_root_spec_id: str | None = None
    variant_parent_depth: int = Field(default=0, ge=0, le=10)
    variant_families: dict[str, float] = Field(default_factory=dict)
    max_lineage_depth: int = Field(default=2, ge=1, le=5)
    max_variants_per_parent: int = Field(default=12, ge=1, le=1000)

    @field_validator("exam")
    @classmethod
    def normalize_exam(cls, value: str) -> str:
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized:
            raise ValueError("exam cannot be empty")
        return normalized

    @field_validator("topics", "required_concepts", "forbidden_concepts", "seed_ideas")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            clean = value.strip()
            key = clean.casefold()
            if clean and key not in seen:
                seen.add(key)
                result.append(clean)
        return result

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, values: dict[str, float]) -> dict[str, float]:
        allowed = {item.value for item in QuestionType}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"unsupported question types: {', '.join(unknown)}")
        return _validate_weights(values, "question_types")

    @field_validator("difficulties")
    @classmethod
    def validate_difficulties(cls, values: dict[int, float]) -> dict[int, float]:
        normalized = {int(key): value for key, value in values.items()}
        invalid = sorted(key for key in normalized if key < 1 or key > 10)
        if invalid:
            raise ValueError(f"difficulty levels must be 1-10: {invalid}")
        return _validate_weights(normalized, "difficulties")

    @field_validator("cognitive_levels")
    @classmethod
    def validate_cognitive_levels(cls, values: dict[str, float]) -> dict[str, float]:
        allowed = {item.value for item in CognitiveLevel}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"unsupported cognitive levels: {', '.join(unknown)}")
        return _validate_weights(values, "cognitive_levels")

    @field_validator("representations")
    @classmethod
    def validate_representations(cls, values: dict[str, float]) -> dict[str, float]:
        allowed = {item.value for item in Representation}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"unsupported representations: {', '.join(unknown)}")
        return _validate_weights(values, "representations")

    @field_validator("reasoning_lenses", "construction_families")
    @classmethod
    def validate_named_weights(cls, values: dict[str, float]) -> dict[str, float]:
        cleaned = {key.strip(): value for key, value in values.items() if key.strip()}
        return _validate_weights(cleaned, "weighted choices") if cleaned else {}

    @field_validator("variant_families")
    @classmethod
    def validate_variant_families(cls, values: dict[str, float]) -> dict[str, float]:
        if not values:
            return {}
        allowed = {item.value for item in VariantFamily}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"unsupported variant families: {', '.join(unknown)}")
        return _validate_weights(values, "variant_families")

    @field_validator("existing_accepted_counts")
    @classmethod
    def validate_existing_counts(cls, values: dict[str, int]) -> dict[str, int]:
        if any(value < 0 for value in values.values()):
            raise ValueError("existing accepted counts cannot be negative")
        return values

    @model_validator(mode="after")
    def validate_variant_contract(self) -> "AuthoringRequest":
        is_variant = self.variant_parent_spec_id is not None
        variant_payload_present = bool(
            self.variant_parent_latex
            or self.variant_parent_artifact_sha256
            or self.variant_lineage_root_spec_id
            or self.variant_families
            or self.variant_parent_depth
        )
        if not is_variant and variant_payload_present:
            raise ValueError("variant metadata requires variant_parent_spec_id")
        if not is_variant:
            return self
        if self.subject != "physics":
            raise ValueError("canonical variants currently support physics only")
        if set(self.question_types) != {QuestionType.MCQ_SINGLE.value}:
            raise ValueError("canonical variants currently require question_type mcq_sc")
        if not self.variant_parent_latex.strip():
            raise ValueError("variant_parent_latex is required")
        if not self.variant_parent_artifact_sha256:
            raise ValueError("variant_parent_artifact_sha256 is required")
        if not self.variant_lineage_root_spec_id:
            raise ValueError("variant_lineage_root_spec_id is required")
        if not self.variant_families:
            raise ValueError("variant_families cannot be empty for a variant run")
        if self.variant_parent_depth >= self.max_lineage_depth:
            raise ValueError(
                f"variant parent depth {self.variant_parent_depth} reaches the lineage cap "
                f"of {self.max_lineage_depth}"
            )
        return self


def _validate_weights(values: dict[Any, float], name: str) -> dict[Any, float]:
    if not values:
        raise ValueError(f"{name} cannot be empty")
    normalized = {key: float(value) for key, value in values.items()}
    if any(value < 0 for value in normalized.values()):
        raise ValueError(f"{name} weights cannot be negative")
    if sum(normalized.values()) <= 0:
        raise ValueError(f"{name} must contain a positive weight")
    return normalized


class GenerationSpec(BaseModel):
    """Immutable blueprint for exactly one authored problem."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    spec_id: str
    ordinal: int = Field(ge=1)
    exam: str
    subject: Subject
    syllabus_version: str
    syllabus_source_sha256: str
    syllabus_source_url: str = ""
    syllabus_official_source_sha256: str = ""
    exam_pattern_description: str = ""
    exam_pattern_source_url: str = ""
    exam_pattern_source_sha256: str = ""
    exam_pattern_verified_at: str = ""
    chapter_id: str
    chapter: str
    chapter_description: str = ""
    topic_id: str
    topic: str
    topic_description: str = ""
    question_type: QuestionType
    difficulty: int = Field(ge=1, le=10)
    cognitive_level: CognitiveLevel
    representation: Representation
    reasoning_lens: str
    construction_family: str
    diagram_policy: DiagramPolicy
    passage_question_count: int = Field(default=3, ge=2, le=10)
    required_concepts: tuple[str, ...] = ()
    forbidden_concepts: tuple[str, ...] = ()
    seed_ideas: tuple[str, ...] = ()
    tone: str = ""
    random_seed: int
    acceptance: AcceptancePolicy
    include_solution: bool = True
    include_idea: bool = True
    source_kind: SourceKind = SourceKind.ORIGINAL
    variant_family: VariantFamily | None = None
    parent_spec_id: str | None = None
    lineage_root_spec_id: str | None = None
    lineage_depth: int = Field(default=0, ge=0, le=5)
    parent_problem_latex: str = ""
    parent_artifact_sha256: str = ""
    parent_idea_latex: str = ""
    parent_solution_latex: str = ""
    parent_final_latex: str = ""
    parent_was_accepted: bool = False

    @property
    def difficulty_band(self) -> Literal["easy", "medium", "hard"]:
        if self.difficulty <= 3:
            return "easy"
        if self.difficulty <= 7:
            return "medium"
        return "hard"

    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"spec_id"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class AuthoringPlan(BaseModel):
    """Deterministic preflight output for a complete authoring request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    request: AuthoringRequest
    catalog_version: str
    catalog_source: str
    catalog_source_url: str = ""
    catalog_official_source_sha256: str = ""
    catalog_verified_at: str = ""
    allowed_question_types: tuple[QuestionType, ...] = tuple(QuestionType)
    exam_pattern_description: str = ""
    exam_pattern_source_url: str = ""
    exam_pattern_source_sha256: str = ""
    exam_pattern_verified_at: str = ""
    catalog_source_sha256: str
    items: tuple[GenerationSpec, ...]
    distributions: dict[str, dict[str, int]]
    estimated_agent_calls: int
    warnings: tuple[str, ...] = ()
