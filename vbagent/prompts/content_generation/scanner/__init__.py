"""Scanner prompts for different question types.

Subject-based organization with specialized prompts for:
- Physics: vectors, units, circuits, mechanics
- Chemistry: chemical equations, reactions, structures
- Mathematics: proofs, set theory, calculus, geometry

Each subject has its own subdirectory with question-type specific prompts.
"""

# Default user template for all scanner types
USER_TEMPLATE = "Extract LaTeX from this {subject} question image."


def get_scanner_prompt(question_type: str, subject: str = "physics") -> str:
    """Get the scanner prompt for a given question type and subject.
    
    Routes to subject-specific prompt modules.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)
        subject: The subject (physics, chemistry, mathematics)
        
    Returns:
        The system prompt for that question type and subject
    """
    subject_lower = subject.lower()
    
    # Route to subject-specific module
    if subject_lower == "physics":
        from .physics import get_prompt
    elif subject_lower == "chemistry":
        from .chemistry import get_prompt
    elif subject_lower == "mathematics":
        from .mathematics import get_prompt
    else:
        # Fallback to physics for unknown subjects
        from .physics import get_prompt
    
    return get_prompt(question_type)


def get_user_template(subject: str = "physics") -> str:
    """Get user template with subject.
    
    Args:
        subject: The subject name
        
    Returns:
        User template string
    """
    return USER_TEMPLATE.format(subject=subject)


__all__ = [
    "get_scanner_prompt",
    "get_user_template",
    "USER_TEMPLATE",
]
