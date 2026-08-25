"""Solution generation agents — subject-specific.

Routes to the correct subject × question_type prompt, calls the LLM,
and returns SolutionOutput with solution_latex + diagram_requirements + answer
plus a conditional alternate-solution recommendation.
"""

import re
from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.agents.content_generation.solution.structure import (
    has_matching_multipart_structure,
    multipart_enumerate_counts,
)
from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution import get_solution_prompt
from vbagent.utils.latex import use_plain_enumerates


_MULTIPART_STRUCTURE_RETRY = r"""
The solution structure is invalid for this multipart subjective problem.
Regenerate the complete JSON response. In `solution_latex`, mirror every
multipart `enumerate` from the problem with a corresponding `enumerate` and
exactly one `\item` per problem part, in the same order. Put each part's full
reasoning inside its own item and preserve the problem's local `enumerate`
structure. Use plain `\begin{enumerate}` with no label options or counter
commands. Do not flatten the parts into one `align*`, do not type part
numbers or labels manually in `\intertext`, and do not use `tasks` or `\task`.
In `final_answer_latex`, return a second matching `enumerate` with one concise
answer `\item` per problem part, again using plain `\begin{enumerate}`. Do not flatten
the answer key into manually numbered prose or a semicolon-separated sentence.
"""


def _as_solution_output(result) -> SolutionOutput:
    """Normalize SDK output to the public solution model."""
    if isinstance(result, SolutionOutput):
        return result
    return SolutionOutput(solution_latex=str(result))


def _use_plain_subjective_enumerates(output: SolutionOutput) -> SolutionOutput:
    """Normalize agent-emitted subjective lists before validation and use."""
    output.solution_latex = use_plain_enumerates(output.solution_latex)
    if output.final_answer_latex:
        output.final_answer_latex = use_plain_enumerates(
            output.final_answer_latex
        )
    return output


def _has_valid_multipart_output(
    problem_text: str,
    output: SolutionOutput,
) -> bool:
    """Return whether both detailed and concise multipart outputs match."""
    return has_matching_multipart_structure(
        problem_text,
        output.solution_latex,
    ) and has_matching_multipart_structure(
        problem_text,
        output.final_answer_latex or "",
    )


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
    output = _as_solution_output(result)
    if question_type == "subjective":
        output = _use_plain_subjective_enumerates(output)

    if (
        question_type == "subjective"
        and not _has_valid_multipart_output(problem_text, output)
    ):
        required_counts = ", ".join(
            str(count) for count in multipart_enumerate_counts(problem_text)
        )
        retry_prompt = (
            user_prompt
            + "\n\n"
            + _MULTIPART_STRUCTURE_RETRY
            + f"\nRequired direct item count(s): {required_counts}."
        )
        if image_path:
            retry_message = create_image_message(image_path, retry_prompt)
        else:
            retry_message = [{"role": "user", "content": retry_prompt}]
        output = _as_solution_output(
            run_agent_sync(
                agent,
                retry_message,
                show_spinner=show_spinner,
            )
        )
        output = _use_plain_subjective_enumerates(output)
        if not _has_valid_multipart_output(problem_text, output):
            raise ValueError(
                "Multipart subjective solution and final answer do not mirror "
                "the problem's enumerate/item structure"
            )

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
