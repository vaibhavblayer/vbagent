"""Solution checker agent for physics problems."""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.agents.quality.base import parse_check_result, has_check_passed
from vbagent.prompts.quality.solution_checker import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output

solution_checker_agent = create_agent(
    name="SolutionChecker",
    instructions=SYSTEM_PROMPT,
    agent_type="solution_checker",
)


def check_solution(full_content: str) -> tuple[bool, str, str]:
    """Check a physics solution for correctness, or create one if missing."""
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    message = USER_TEMPLATE.replace('{full_content}', full_content)
    raw_result = run_agent_sync(solution_checker_agent, message)
    result = clean_latex_output(raw_result)
    return parse_check_result(result, "SOLUTION_CHECK")


def has_solution_passed(result: str) -> bool:
    return has_check_passed(result, "SOLUTION_CHECK")
