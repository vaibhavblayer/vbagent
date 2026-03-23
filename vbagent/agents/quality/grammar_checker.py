"""Grammar checker agent for physics content."""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.agents.quality.base import parse_check_result, has_check_passed
from vbagent.prompts.quality.grammar_checker import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output

grammar_checker_agent = create_agent(
    name="GrammarChecker",
    instructions=SYSTEM_PROMPT,
    agent_type="grammar_checker",
)


def check_grammar(full_content: str) -> tuple[bool, str, str]:
    """Check physics content for grammar and spelling errors."""
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    message = USER_TEMPLATE.replace('{full_content}', full_content)
    raw_result = run_agent_sync(grammar_checker_agent, message)
    result = clean_latex_output(raw_result)
    return parse_check_result(result, "GRAMMAR_CHECK")


def has_grammar_passed(result: str) -> bool:
    return has_check_passed(result, "GRAMMAR_CHECK")
