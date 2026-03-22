"""Formatting rules for chemistry scanner prompts.

Re-exports subject-specific constants from common.py and
generic formatting rules from the parent module.
"""

from .common import (
    TIKZ_GUIDELINES,
    TIKZ_GUIDELINES_SHORT,
    LATEX_FORMATTING_RULES,
    OPTIONS_WITH_DIAGRAMS,
    DIAGRAM_PLACEHOLDER,
)
from .._shared import SOLUTION_FORMATTING_RULES, PROBLEM_FORMATTING_RULES

__all__ = [
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "OPTIONS_WITH_DIAGRAMS",
    "DIAGRAM_PLACEHOLDER",
    "SOLUTION_FORMATTING_RULES",
    "PROBLEM_FORMATTING_RULES",
]
