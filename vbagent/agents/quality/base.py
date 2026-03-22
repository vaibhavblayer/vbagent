"""Shared utilities for quality checker agents.

Extracts the duplicated parse_check_result / has_check_passed logic
that was copy-pasted across solution_checker, grammar_checker,
clarity_checker, format_checker, and diagram/tikz_checker.
"""

import re


def parse_check_result(result: str, check_type: str) -> tuple[bool, str, str]:
    """Parse a checker result to extract pass/fail status and content.

    All quality checkers embed a comment like ``% CHECK_TYPE: PASSED``
    or ``% CHECK_TYPE: <summary>`` in their output.

    Args:
        result: Raw result string from the checker agent.
        check_type: The tag to look for (e.g. "SOLUTION_CHECK", "GRAMMAR_CHECK").

    Returns:
        Tuple of (passed, summary, corrected_content).
    """
    passed_pattern = rf'%\s*{check_type}:\s*PASSED'
    if re.search(passed_pattern, result, re.IGNORECASE):
        match = re.search(
            rf'%\s*{check_type}:\s*PASSED\s*[-–—]?\s*(.*?)(?:\n|$)',
            result,
            re.IGNORECASE,
        )
        summary = match.group(1).strip() if match else "No issues found"
        return True, summary, ""

    summary_pattern = rf'%\s*{check_type}:\s*(.*?)(?:\n|$)'
    summary_match = re.search(summary_pattern, result, re.IGNORECASE)
    summary = (
        summary_match.group(1).strip()
        if summary_match
        else "Issues found and corrected"
    )

    corrected_content = re.sub(
        rf'%\s*{check_type}:.*?\n', '', result, count=1, flags=re.IGNORECASE
    )
    return False, summary, corrected_content.strip()


def has_check_passed(result: str, check_type: str) -> bool:
    """Quick check whether a checker result indicates PASSED.

    Args:
        result: Raw result string.
        check_type: The tag (e.g. "TIKZ_CHECK").
    """
    tag = f"% {check_type}: PASSED"
    return tag in result or f"{check_type}: PASSED" in result.upper()
