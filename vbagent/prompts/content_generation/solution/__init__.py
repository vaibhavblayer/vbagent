"""Solution generation prompts organized by subject and question type.

This module provides prompts for Stage 2 of the content generation pipeline:
generating solutions from scanned problems.

Unlike scanner prompts (which focus on OCR), solution prompts focus on:
- Mathematical/scientific reasoning
- Step-by-step explanations
- Diagram requirement identification
- Answer derivation
"""

from typing import Optional


def get_solution_prompt(question_type: str, subject: str, chapter: Optional[str] = None, topic: Optional[str] = None) -> str:
    """Get solution generation prompt for a question type and subject.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, subjective, etc.)
        subject: The subject (physics, chemistry, mathematics)
        chapter: Chapter/topic area for topic-specific routing (optional)
        topic: Specific topic for topic-specific routing (optional)
        
    Returns:
        The system prompt for solution generation
        
    Raises:
        ValueError: If subject is not supported
    """
    if subject == "physics":
        from .physics import get_prompt
        return get_prompt(question_type, chapter, topic)
    elif subject == "chemistry":
        from .chemistry import get_prompt
        return get_prompt(question_type)
    elif subject == "mathematics":
        from .mathematics import get_prompt
        return get_prompt(question_type)
    else:
        raise ValueError(f"Unsupported subject: {subject}")
    
    return get_prompt(question_type)


def get_user_template(subject: str) -> str:
    """Get user message template for solution generation.
    
    Args:
        subject: The subject (physics, chemistry, mathematics)
        
    Returns:
        User message template
    """
    # Common template for all subjects
    return """Generate a detailed solution for the following problem:

{problem}

{options}

Provide:
1. Step-by-step solution with clear reasoning
2. Identify any diagrams needed in the solution
3. Final answer (if applicable)
"""


__all__ = [
    "get_solution_prompt",
    "get_user_template",
]
