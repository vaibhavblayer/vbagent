"""Solution generation agents — subject-specific.

Routes to the correct subject × question_type prompt, calls the LLM,
and returns SolutionOutput with solution_latex + diagram_requirements + answer
plus a conditional alternate-solution recommendation.
"""

import re
from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution import get_solution_prompt


def generate_solution(
    problem_text: str,
    question_type: str,
    subject: str,
    chapter: Optional[str] = None,
    topic: Optional[str] = None,
    image_path: Optional[str] = None,
    show_spinner: bool = True,
) -> SolutionOutput:
    """Generate a solution using the subject-specific agent.

    Args:
        problem_text: Scanned problem LaTeX from ProblemOrchestrator.
        question_type: mcq_sc, mcq_mc, subjective, assertion_reason, match, passage.
        subject: physics, chemistry, mathematics.
        chapter: Chapter/topic area for topic-specific routing (optional).
        topic: Specific topic for topic-specific routing (optional).
        image_path: Pass only when the problem contains a diagram the solver needs to see.
        show_spinner: Show progress spinner.

    Returns:
        SolutionOutput with solution_latex, diagram_requirements, answer fields,
        and the optional alternate-solution recommendation.
    """
    system_prompt = get_solution_prompt(question_type, subject, chapter, topic)

    from agents import AgentOutputSchema

    agent = create_agent(
        name=f"{subject.capitalize()}Solution",
        instructions=system_prompt,
        agent_type="solution",
        output_type=AgentOutputSchema(SolutionOutput, strict_json_schema=False),
    )

    user_prompt = f"Generate a complete solution for this {subject} {question_type} problem:\n\n{problem_text}"

    if image_path:
        message = create_image_message(image_path, user_prompt)
    else:
        message = [{"role": "user", "content": user_prompt}]

    result = run_agent_sync(agent, message, show_spinner=show_spinner)

    if isinstance(result, SolutionOutput):
        output = result
    else:
        output = SolutionOutput(solution_latex=str(result))

    if (
        question_type == "subjective"
        and output.answer_type == "subjective"
        and not (output.final_answer_latex or "").strip()
    ):
        raise ValueError(
            "Subjective solution response is missing required "
            "final_answer_latex"
        )
    if question_type == "match":
        answer = (output.answer_value or "").strip().lower()
        if output.answer_type != "mcq" or answer not in {"a", "b", "c", "d"}:
            conclusion = re.search(
                r"correct\s+option\s+is\s+\(([a-d])\)",
                output.solution_latex,
                flags=re.IGNORECASE,
            )
            if not conclusion:
                raise ValueError(
                    "Match solution response is missing the correct code option"
                )
            output.answer_type = "mcq"
            output.answer_value = conclusion.group(1).lower()
        else:
            output.answer_value = answer
        replacement = (output.match_option_replacement_latex or "").strip()
        if replacement:
            if re.search(
                r"\\(?:begin|end)\{tasks\}|\\task\b|\\ans\b",
                replacement,
            ):
                raise ValueError(
                    "Match option replacement must contain only the option payload"
                )
            output.match_option_replacement_latex = replacement
        else:
            output.match_option_replacement_latex = None
    return output


__all__ = [
    "generate_solution",
]
