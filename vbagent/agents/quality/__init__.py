"""Quality assurance agents.

- Reviewer: Review problem quality
- Solution Checker: Validate solutions
- Grammar Checker: Check grammar and language
- Clarity Checker: Check problem clarity
- Format Checker: Check formatting
- LaTeX Fixer: Fix LaTeX compilation issues
"""

from .base import parse_check_result, has_check_passed
from .reviewer import review_problem_sync
from .solution_checker import check_solution, has_solution_passed
from .grammar_checker import check_grammar, has_grammar_passed
from .clarity_checker import check_clarity, has_clarity_passed
from .format_checker import check_format, has_format_passed
from .latex_fixer import fix_latex

# Backward-compatible aliases
parse_solution_check = parse_check_result
parse_grammar_check = parse_check_result
parse_clarity_check = parse_check_result

__all__ = [
    # Shared
    "parse_check_result",
    "has_check_passed",
    # Reviewer
    "review_problem_sync",
    # Solution Checker
    "check_solution",
    "parse_solution_check",
    "has_solution_passed",
    # Grammar Checker
    "check_grammar",
    "parse_grammar_check",
    "has_grammar_passed",
    # Clarity Checker
    "check_clarity",
    "parse_clarity_check",
    "has_clarity_passed",
    # Format Checker
    "check_format",
    "has_format_passed",
    # LaTeX Fixer
    "fix_latex",
]
