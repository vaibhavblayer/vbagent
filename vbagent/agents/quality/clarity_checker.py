"""Clarity checker agent for physics content."""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.agents.quality.base import parse_check_result, has_check_passed
from vbagent.prompts.quality.clarity_checker import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output

clarity_checker_agent = create_agent(
    name="ClarityChecker",
    instructions=SYSTEM_PROMPT,
    agent_type="clarity_checker",
)


def check_clarity(full_content: str) -> tuple[bool, str, str]:
    """Check physics content for clarity and conciseness."""
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    message = USER_TEMPLATE.replace('{full_content}', full_content)
    raw_result = run_agent_sync(clarity_checker_agent, message)
    result = clean_latex_output(raw_result)
    return parse_check_result(result, "CLARITY_CHECK")


def has_clarity_passed(result: str) -> bool:
    return has_check_passed(result, "CLARITY_CHECK")
