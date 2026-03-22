"""Quality assurance prompts."""

from vbagent.prompts.quality.reviewer import SYSTEM_PROMPT as REVIEWER_PROMPT
from vbagent.prompts.quality.solution_checker import SYSTEM_PROMPT as SOLUTION_CHECKER_PROMPT
from vbagent.prompts.quality.grammar_checker import SYSTEM_PROMPT as GRAMMAR_CHECKER_PROMPT
from vbagent.prompts.quality.clarity_checker import SYSTEM_PROMPT as CLARITY_CHECKER_PROMPT
from vbagent.prompts.quality.format_checker import SYSTEM_PROMPT as FORMAT_CHECKER_PROMPT

__all__ = [
    "REVIEWER_PROMPT",
    "SOLUTION_CHECKER_PROMPT",
    "GRAMMAR_CHECKER_PROMPT",
    "CLARITY_CHECKER_PROMPT",
    "FORMAT_CHECKER_PROMPT",
]
