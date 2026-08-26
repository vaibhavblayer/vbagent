"""Results and stage evidence for canonical authoring runs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from vbagent.authoring.models import GenerationSpec


REQUIRED_ACCEPTANCE_GATES = (
    "draft",
    "structure",
    "independent_solution",
    "final_structure",
    "classification",
    "answer_agreement",
    "spec_alignment",
    "difficulty",
    "compile",
    "review",
    "novelty",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: str
    required: bool = True
    passed: bool
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = Field(default=0, ge=0)


class AuthoredCandidate(BaseModel):
    """Complete evidence bundle for one generated candidate."""

    model_config = ConfigDict(extra="forbid")

    spec: GenerationSpec
    status: CandidateStatus = CandidateStatus.PLANNED
    problem_latex: str = ""
    draft_solution_latex: str = ""
    independent_solution_latex: str = ""
    final_latex: str = ""
    idea_latex: str = ""
    diagram_code: str = ""
    diagram_description: str = ""
    classification: dict[str, Any] = Field(default_factory=dict)
    difficulty: dict[str, Any] = Field(default_factory=dict)
    answer_agreement: dict[str, Any] = Field(default_factory=dict)
    spec_alignment: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    gates: list[GateResult] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    error_stage: str | None = None
    error_message: str | None = None
    created_at: str = Field(default_factory=_now)
    completed_at: str | None = None

    @property
    def accepted(self) -> bool:
        return self.status is CandidateStatus.ACCEPTED
