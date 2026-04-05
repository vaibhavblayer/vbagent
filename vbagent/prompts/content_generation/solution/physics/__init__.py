"""Physics-specific solution generation prompts.

Solution prompts for physics questions focusing on:
- Physics reasoning and principles
- Step-by-step problem solving
- Diagram requirement identification
- Proper physics notation and formatting
"""

from typing import Optional

from .mcq_sc import SYSTEM_PROMPT as MCQ_SC_PROMPT
from .mcq_mc import SYSTEM_PROMPT as MCQ_MC_PROMPT
from .subjective import SYSTEM_PROMPT as SUBJECTIVE_PROMPT
from .assertion_reason import SYSTEM_PROMPT as ASSERTION_REASON_PROMPT
from .passage import SYSTEM_PROMPT as PASSAGE_PROMPT
from .match import SYSTEM_PROMPT as MATCH_PROMPT
from .common import (
    LATEX_FORMATTING_RULES,
    SOLUTION_QUALITY,
    PHYSICS_PACKAGES,
    SOLUTION_WITH_DIAGRAM_TEMPLATE,
)

# Mapping from question type to prompt
SOLUTION_PROMPTS = {
    "mcq_sc": MCQ_SC_PROMPT,
    "mcq_mc": MCQ_MC_PROMPT,
    "subjective": SUBJECTIVE_PROMPT,
    "integer": SUBJECTIVE_PROMPT,  # integer uses subjective-style solution + \ansint
    "assertion_reason": ASSERTION_REASON_PROMPT,
    "passage": PASSAGE_PROMPT,
    "match": MATCH_PROMPT,
    "matrix_match": MATCH_PROMPT,
}


def get_prompt(question_type: str, chapter: Optional[str] = None, topic: Optional[str] = None) -> str:
    """Get physics solution generation prompt for a question type.
    
    Supports topic-specific routing when chapter/topic are provided.
    Falls back to generic physics prompt if topic agent not found.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, subjective, etc.)
        chapter: Chapter/topic area for topic-specific routing (optional)
        topic: Specific topic for topic-specific routing (optional)
        
    Returns:
        The system prompt for solution generation
    """
    # Try topic-specific prompt first if chapter or topic provided
    if chapter or topic:
        from .topics import get_topic_prompt
        topic_prompt = get_topic_prompt(chapter, topic, question_type)
        if topic_prompt:  # If topic agent found
            # Log which topic agent is being used (for debugging)
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Using topic-specific agent for chapter='{chapter}', topic='{topic}'")
            return topic_prompt
    
    # Fall back to generic physics prompt
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
    "PHYSICS_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
]
