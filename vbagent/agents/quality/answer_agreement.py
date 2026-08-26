"""Independent adjudication of draft and independently generated solutions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.quality.answer_agreement import SYSTEM_PROMPT, USER_TEMPLATE


class AnswerAgreementResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_well_posed: bool
    draft_solution_correct: bool
    independent_solution_correct: bool
    answers_agree: bool
    draft_final_answer: str = ""
    independent_final_answer: str = ""
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def passed(self) -> bool:
        return all(
            (
                self.problem_well_posed,
                self.draft_solution_correct,
                self.independent_solution_correct,
                self.answers_agree,
            )
        )


def verify_answer_agreement(
    *,
    subject: str,
    question_type: str,
    problem_latex: str,
    draft_solution_latex: str,
    independent_solution_latex: str,
) -> AnswerAgreementResult:
    agent = create_agent(
        name=f"AnswerAgreement-{subject}",
        instructions=SYSTEM_PROMPT,
        output_type=AnswerAgreementResult,
        agent_type="solution_checker",
    )
    prompt = USER_TEMPLATE.format(
        subject=subject,
        question_type=question_type,
        problem_latex=problem_latex,
        draft_solution_latex=draft_solution_latex,
        independent_solution_latex=independent_solution_latex,
    )
    return run_agent_sync(agent, prompt, show_spinner=True)
