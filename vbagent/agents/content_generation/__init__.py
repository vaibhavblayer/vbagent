"""Content generation agents.

This module contains agents responsible for generating various types of content:
- Scanner: Extract problems from LaTeX files
- Idea: Generate problem ideas
- Alternate: Create alternate versions of problems
- Converter: Convert between problem formats
"""

from .scanner import scan, scan_with_type, scan_problem, scan_solution, create_scanner_agent
from .idea import extract_ideas, generate_idea_latex, has_idea_environment, count_idea_environments
from .alternate import generate_alternate, extract_answer, extract_existing_alternates, has_alternate_solution, count_alternate_solutions
from .converter import convert_format

__all__ = [
    # Scanner
    "scan",
    "scan_with_type",
    "scan_problem",
    "scan_solution",
    "create_scanner_agent",
    # Idea
    "extract_ideas",
    "generate_idea_latex",
    "has_idea_environment",
    "count_idea_environments",
    # Alternate
    "generate_alternate",
    "extract_answer",
    "extract_existing_alternates",
    "has_alternate_solution",
    "count_alternate_solutions",
    # Converter
    "convert_format",
]
