"""Biology-specific solution generation prompts.

Solution prompts for biology questions focusing on:
- Biological reasoning and principles
- Cell biology, genetics, ecology, physiology
- Diagram requirement identification (cell structures, flowcharts, etc.)
- Proper biology notation (scientific names, key terms)

Currently supports: mcq_sc (all other types fall back to mcq_sc)
"""

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .common import (
    LATEX_FORMATTING_RULES,
    SOLUTION_QUALITY,
    BIOLOGY_PACKAGES,
    SOLUTION_WITH_DIAGRAM_TEMPLATE,
)

# Mapping from question type to prompt
SOLUTION_PROMPTS = {
    "mcq_sc": MCQ_SC_PROMPT,
    # All other types fall back to mcq_sc for now
    "mcq_mc": MCQ_SC_PROMPT,
    "subjective": MCQ_SC_PROMPT,
    "integer": MCQ_SC_PROMPT,
    "assertion_reason": MCQ_SC_PROMPT,
    "passage": MCQ_SC_PROMPT,
    "match": MCQ_SC_PROMPT,
    "matrix_match": MCQ_SC_PROMPT,
}


def get_prompt(question_type: str) -> str:
    """Get biology solution generation prompt for a question type.

    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)

    Returns:
        The system prompt for solution generation
    """
    return SOLUTION_PROMPTS.get(question_type, MCQ_SC_PROMPT)


__all__ = [
    "SOLUTION_PROMPTS",
    "get_prompt",
    "MCQ_SC_PROMPT",
    # Common components
    "LATEX_FORMATTING_RULES",
    "SOLUTION_QUALITY",
    "BIOLOGY_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
]
