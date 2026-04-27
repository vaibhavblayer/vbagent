"""Format checker agent for physics content."""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.agents.quality.base import parse_check_result, has_check_passed
from vbagent.prompts.quality.format_checker import get_system_prompt, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output


def check_format(
    full_content: str,
    subject: str = "physics",
    question_type: str = "subjective",
    has_diagram: bool = False,
) -> tuple[bool, str, str]:
    """Check content for formatting issues, subject-aware."""
    if not full_content.strip():
        raise ValueError("Content cannot be empty")

    # Create agent with subject-specific prompt
    agent = create_agent(
        name="FormatChecker",
        instructions=get_system_prompt(subject),
        agent_type="format_checker",
    )

    message = USER_TEMPLATE.format(
        subject=subject,
        question_type=question_type,
        has_diagram=has_diagram,
        full_content=full_content,
    )
    raw_result = run_agent_sync(agent, message)
    result = clean_latex_output(raw_result)
    return parse_check_result(result, "FORMAT_CHECK")


def has_format_passed(result: str) -> bool:
    return has_check_passed(result, "FORMAT_CHECK")


# Backward-compatible module-level agent (uses physics prompt)
from vbagent.prompts.quality.format_checker import SYSTEM_PROMPT as _PHYSICS_PROMPT

format_checker_agent = create_agent(
    name="FormatChecker",
    instructions=_PHYSICS_PROMPT,
    agent_type="format_checker",
)
