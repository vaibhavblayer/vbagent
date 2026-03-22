"""Mathematics-specific scanner prompts.

Scanner prompts for mathematics questions with mathematics-specific:
- Solution structure (proofs, case analysis, QED)
- Notation (set theory, logic, calculus, geometry)
- Packages (TikZ, pgfplots, amsmath, amssymb)
- Diagram types (geometric figures, function graphs, number lines, Venn diagrams)
"""

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .mcq_mc import SYSTEM_PROMPT as MCQ_MC_PROMPT
from .subjective import SYSTEM_PROMPT as SUBJECTIVE_PROMPT
from .assertion_reason import SYSTEM_PROMPT as ASSERTION_REASON_PROMPT
from .passage import SYSTEM_PROMPT as PASSAGE_PROMPT
from .match import SYSTEM_PROMPT as MATCH_PROMPT
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
    "mcq_mc": MCQ_MC_PROMPT,
    "subjective": SUBJECTIVE_PROMPT,
    "assertion_reason": ASSERTION_REASON_PROMPT,
    "passage": PASSAGE_PROMPT,
    "match": MATCH_PROMPT,
}


def get_prompt(question_type: str) -> str:
    """Get mathematics scanner prompt for a question type.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)
        
    Returns:
        The system prompt for that question type
    """
    if question_type not in SCANNER_PROMPTS:
        # Fall back to mcq_sc for unknown types
        return SCANNER_PROMPTS["mcq_sc"]
    
    return SCANNER_PROMPTS[question_type]


__all__ = [
    "SCANNER_PROMPTS",
    "get_prompt",
    "MCQ_SC_PROMPT",
    "MCQ_MC_PROMPT",
    "SUBJECTIVE_PROMPT",
    "ASSERTION_REASON_PROMPT",
    "PASSAGE_PROMPT",
    "MATCH_PROMPT",
    # Common prompt components
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_PLACEHOLDER",
    "OPTIONS_WITH_DIAGRAMS",
    "SOLUTION_STRUCTURE",
]
