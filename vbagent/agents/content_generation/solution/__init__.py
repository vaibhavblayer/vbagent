"""Solution generation agents — subject-specific.

Routes to the correct subject × question_type prompt, calls the LLM,
and returns SolutionOutput with solution_latex + diagram_requirements + answer.
"""

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
        SolutionOutput with solution_latex, diagram_requirements, answer_type, answer_value.
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
        return result
    return SolutionOutput(solution=str(result))


__all__ = [
    "generate_solution",
]
