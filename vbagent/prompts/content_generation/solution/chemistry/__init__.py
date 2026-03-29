"""Chemistry-specific solution generation prompts.

Solution prompts for chemistry questions focusing on:
- Chemical reasoning and principles
- Reaction mechanisms and equations
- Diagram requirement identification (structures, energy diagrams, etc.)
- Proper chemistry notation
"""

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .mcq_mc import SYSTEM_PROMPT as MCQ_MC_PROMPT
from .subjective import SYSTEM_PROMPT as SUBJECTIVE_PROMPT
from .assertion_reason import SYSTEM_PROMPT as ASSERTION_REASON_PROMPT
from .passage import SYSTEM_PROMPT as PASSAGE_PROMPT
from .match import SYSTEM_PROMPT as MATCH_PROMPT
from .common import (
    LATEX_FORMATTING_RULES,
    SOLUTION_QUALITY,
    CHEMISTRY_PACKAGES,
    SOLUTION_WITH_DIAGRAM_TEMPLATE,
)

# Mapping from question type to prompt
SOLUTION_PROMPTS = {
    "mcq_sc": MCQ_SC_PROMPT,
    "mcq_mc": MCQ_MC_PROMPT,
    "subjective": SUBJECTIVE_PROMPT,
    "integer": SUBJECTIVE_PROMPT,
    "assertion_reason": ASSERTION_REASON_PROMPT,
    "passage": PASSAGE_PROMPT,
    "match": MATCH_PROMPT,
    "matrix_match": MATCH_PROMPT,
}


def get_prompt(question_type: str) -> str:
    """Get chemistry solution generation prompt for a question type.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, subjective, etc.)
        
    Returns:
        The system prompt for solution generation
    """
    if question_type not in SOLUTION_PROMPTS:
        # Fall back to subjective for unknown types
        return SOLUTION_PROMPTS["subjective"]
    
    return SOLUTION_PROMPTS[question_type]


__all__ = [
    "SOLUTION_PROMPTS",
    "get_prompt",
    "MCQ_SC_PROMPT",
    "SUBJECTIVE_PROMPT",
    # Common components
    "LATEX_FORMATTING_RULES",
    "SOLUTION_QUALITY",
    "CHEMISTRY_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
]
