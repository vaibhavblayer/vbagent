"""Format checker agent for physics content.

Checks and fixes formatting issues specific to problem types,
including metadata cleanup, LaTeX structure, and type-specific formatting.
"""

import re

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.quality.format_checker import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output


# Create the format checker agent
format_checker_agent = create_agent(
    name="FormatChecker",
    instructions=SYSTEM_PROMPT,
    agent_type="quality.format_checker",  # Uses format_checker model config
)


def check_format(
    full_content: str,
    subject: str = "physics",
    question_type: str = "subjective",
    has_diagram: bool = False,
) -> tuple[bool, str, str]:
    """Check physics content for formatting issues.
    
    Analyzes the content for:
    - Metadata cleanup (example numbers, exam years)
    - LaTeX structure issues
    - Problem-type specific formatting
    - Common OCR errors
    
    Args:
        full_content: Full LaTeX file content
        subject: Subject of the problem (physics, chemistry, etc.)
        question_type: Type of question (mcq_sc, mcq_mc, subjective, etc.)
        has_diagram: Whether the problem has a diagram
        
    Returns:
        Tuple of (passed, summary, corrected_content)
        - passed: True if no issues found
        - summary: Description of what was fixed (or "PASSED")
        - corrected_content: The corrected file content (empty if passed)
        
    Raises:
        ValueError: If content is empty
    """
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    
    # Format the message with metadata
    message = USER_TEMPLATE.format(
        subject=subject,
        question_type=question_type,
        has_diagram=has_diagram,
        full_content=full_content,
    )
    
    raw_result = run_agent_sync(format_checker_agent, message)
    result = clean_latex_output(raw_result)
    
    return parse_check_result(result, "FORMAT_CHECK")


def parse_check_result(result: str, check_type: str) -> tuple[bool, str, str]:
    """Parse the check result to extract pass/fail status and content.
    
    Args:
        result: Raw result from checker
        check_type: Type of check (FORMAT_CHECK, GRAMMAR_CHECK, etc.)
        
    Returns:
        Tuple of (passed, summary, corrected_content)
    """
    # Check if passed
    passed_pattern = rf'%\s*{check_type}:\s*PASSED'
    if re.search(passed_pattern, result, re.IGNORECASE):
        # Extract the summary after PASSED
        match = re.search(rf'%\s*{check_type}:\s*PASSED\s*[-–—]?\s*(.*?)(?:\n|$)', result, re.IGNORECASE)
        summary = match.group(1).strip() if match else "No issues found"
        return True, summary, ""
    
    # Extract summary from comment
    summary_pattern = rf'%\s*{check_type}:\s*(.*?)(?:\n|$)'
    summary_match = re.search(summary_pattern, result, re.IGNORECASE)
    summary = summary_match.group(1).strip() if summary_match else "Formatting issues fixed"
    
    # Remove the check comment line to get clean content
    corrected_content = re.sub(rf'%\s*{check_type}:.*?\n', '', result, count=1, flags=re.IGNORECASE)
    corrected_content = corrected_content.strip()
    
    return False, summary, corrected_content


def has_format_passed(result: str) -> bool:
    """Check if format check passed.
    
    Args:
        result: Raw result from checker
        
    Returns:
        True if format check passed
    """
    return '% FORMAT_CHECK: PASSED' in result or 'FORMAT_CHECK: PASSED' in result.upper()
