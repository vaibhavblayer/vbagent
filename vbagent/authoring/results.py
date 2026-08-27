"""Results and stage evidence for canonical authoring runs."""

from __future__ import annotations

import re
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
    DRAFT = "draft"
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

    @property
    def deliverable_latex(self) -> str:
        """Preserve every available selected component, including review drafts."""
        content = self.final_latex or "\n\n".join(
            part
            for part in (
                self.problem_latex,
                (self.independent_solution_latex or self.draft_solution_latex)
                if self.spec.include_solution
                else "",
            )
            if part
        )
        if (
            self.spec.include_idea
            and self.idea_latex
            and self.idea_latex not in content
        ):
            content = content.rstrip() + "\n\n" + self.idea_latex
        return content

    @property
    def published_problem_latex(self) -> str:
        """Recover the actual saved question, not a pre-validation draft."""
        return (
            re.split(r"\\begin\{(?:solution|idea)\}", self.final_latex, maxsplit=1)[
                0
            ].strip()
            if self.final_latex.strip()
            else self.problem_latex
        )

    @property
    def published_solution_latex(self) -> str:
        """Use the saved solution, which can differ from fresh verification evidence."""
        match = re.search(
            r"\\begin\{solution\}.*?\\end\{solution\}", self.final_latex, re.DOTALL
        )
        return (
            match.group(0)
            if match
            else (self.independent_solution_latex or self.draft_solution_latex)
        )
