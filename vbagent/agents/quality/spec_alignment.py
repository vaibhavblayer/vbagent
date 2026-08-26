"""Structured verification of a candidate against its immutable authoring spec."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.quality.spec_alignment import SYSTEM_PROMPT, USER_TEMPLATE


class SpecAlignmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam_aligned: bool
    subject_aligned: bool
    chapter_aligned: bool
    topic_aligned: bool
    question_type_aligned: bool
    cognitive_level_aligned: bool
    representation_aligned: bool
    reasoning_lens_applied: bool
    construction_family_aligned: bool
    required_concepts_covered: bool
    forbidden_concepts_absent: bool
    out_of_scope_concepts: list[str] = Field(default_factory=list)
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def passed(self) -> bool:
        return all(
            (
                self.exam_aligned,
                self.subject_aligned,
                self.chapter_aligned,
                self.topic_aligned,
                self.question_type_aligned,
                self.cognitive_level_aligned,
                self.representation_aligned,
                self.reasoning_lens_applied,
                self.construction_family_aligned,
                self.required_concepts_covered,
                self.forbidden_concepts_absent,
                not self.out_of_scope_concepts,
            )
        )


def verify_spec_alignment(
    *,
    exam: str,
    subject: str,
    chapter: str,
    chapter_description: str,
    topic: str,
    topic_description: str,
    question_type: str,
    cognitive_level: str,
    representation: str,
    reasoning_lens: str,
    construction_family: str,
    exam_pattern_description: str,
    exam_pattern_source_url: str,
    required_concepts: list[str] | tuple[str, ...],
    forbidden_concepts: list[str] | tuple[str, ...],
    problem_latex: str,
    solution_latex: str,
) -> SpecAlignmentResult:
    agent = create_agent(
        name=f"SpecAlignment-{subject}",
        instructions=SYSTEM_PROMPT,
        output_type=SpecAlignmentResult,
        agent_type="taxonomy_classifier",
    )
    prompt = USER_TEMPLATE.format(
        exam=exam,
        subject=subject,
        chapter=chapter,
        chapter_description=chapter_description or "none provided",
        topic=topic,
        topic_description=topic_description or "none provided",
        question_type=question_type,
        cognitive_level=cognitive_level,
        representation=representation,
        reasoning_lens=reasoning_lens,
        construction_family=construction_family,
        exam_pattern_description=exam_pattern_description or "custom/unspecified",
        exam_pattern_source_url=exam_pattern_source_url or "custom/unspecified",
        required_concepts=", ".join(required_concepts) or "none beyond the exact topic",
        forbidden_concepts=", ".join(forbidden_concepts) or "none",
        problem_latex=problem_latex,
        solution_latex=solution_latex,
    )
    return run_agent_sync(agent, prompt, show_spinner=True)
