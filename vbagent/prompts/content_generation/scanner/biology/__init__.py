"""Biology-specific scanner prompts.

Scanner prompts for biology questions with biology-specific:
- Scientific name formatting (italics for genus/species)
- Key term bolding
- TikZ for cell diagrams, flowcharts, life cycles
- mhchem for biological molecules (ATP, NADH, CO2)

Currently supports: mcq_sc
"""

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .common import (
    TIKZ_GUIDELINES,
    TIKZ_GUIDELINES_SHORT,
    LATEX_FORMATTING_RULES,
    DIAGRAM_PLACEHOLDER,
    PASSAGE_DIAGRAM_INLINE,
    OPTIONS_WITH_DIAGRAMS,
    SOLUTION_STRUCTURE,
)

# Mapping from question type to prompt
SCANNER_PROMPTS = {
    "mcq_sc": MCQ_SC_PROMPT,
    # Other types fall back to mcq_sc for now
    "mcq_mc": MCQ_SC_PROMPT,
    "subjective": MCQ_SC_PROMPT,
    "assertion_reason": MCQ_SC_PROMPT,
    "passage": MCQ_SC_PROMPT,
    "match": MCQ_SC_PROMPT,
}


def get_prompt(question_type: str) -> str:
    """Get biology scanner prompt for a question type.

    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)

    Returns:
        The system prompt for that question type
    """
    return SCANNER_PROMPTS.get(question_type, MCQ_SC_PROMPT)


__all__ = [
    "SCANNER_PROMPTS",
    "get_prompt",
    "MCQ_SC_PROMPT",
    # Common prompt components
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_PLACEHOLDER",
    "OPTIONS_WITH_DIAGRAMS",
    "SOLUTION_STRUCTURE",
]
