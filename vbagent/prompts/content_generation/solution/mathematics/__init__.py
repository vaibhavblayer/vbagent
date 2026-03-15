"""Mathematics-specific solution generation prompts.

Solution prompts for mathematics questions focusing on:
- Mathematical reasoning and proofs
- Step-by-step problem solving
- Diagram requirement identification (graphs, geometric figures, etc.)
- Proper mathematical notation
"""

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .subjective import SYSTEM_PROMPT as SUBJECTIVE_PROMPT
from .common import (
    LATEX_FORMATTING_RULES,
    DIAGRAM_IDENTIFICATION,
    SOLUTION_QUALITY,
    MATHEMATICS_PACKAGES,
    SOLUTION_WITH_DIAGRAM_TEMPLATE,
)

# Mapping from question type to prompt
SOLUTION_PROMPTS = {
    "mcq_sc": MCQ_SC_PROMPT,
    "mcq_mc": MCQ_SC_PROMPT,  # TODO: Create specific MCQ_MC prompt
    "subjective": SUBJECTIVE_PROMPT,
    "assertion_reason": MCQ_SC_PROMPT,  # TODO: Create specific prompt
    "passage": SUBJECTIVE_PROMPT,  # TODO: Create specific prompt
    "match": SUBJECTIVE_PROMPT,  # TODO: Create specific prompt
}


def get_prompt(question_type: str) -> str:
    """Get mathematics solution generation prompt for a question type.
    
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
    "DIAGRAM_IDENTIFICATION",
    "SOLUTION_QUALITY",
    "MATHEMATICS_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
]
