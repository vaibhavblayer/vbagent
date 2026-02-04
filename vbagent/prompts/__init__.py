"""Prompt modules for vbagent agents.

Provides prompt templates for all agent types. These can be used
to customize agent behavior or create custom agents.

Usage:
    from vbagent.prompts import get_scanner_prompt, get_variant_prompt
    
    # Get scanner prompt for MCQ questions
    prompt = get_scanner_prompt("mcq_sc")
    
    # Get variant prompts
    system, user = get_variant_prompt("numerical")
    
    # Access individual prompts
    from vbagent.prompts import CLASSIFIER_PROMPT, IDEA_PROMPT

Available prompt modules:
- scanner: LaTeX extraction prompts by question type
- variants: Problem variant generation prompts
- classifier: Image classification prompt
- idea: Concept extraction prompt
- alternate: Alternate solution prompt
- reviewer: QA review prompt
- tikz: TikZ diagram generation prompt
- solution_checker, grammar_checker, clarity_checker, tikz_checker: QA checker prompts
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import get_scanner_prompt, SCANNER_PROMPTS
    from .classifier import SYSTEM_PROMPT as CLASSIFIER_PROMPT
    from .idea import SYSTEM_PROMPT as IDEA_PROMPT
    from .alternate import SYSTEM_PROMPT as ALTERNATE_PROMPT
    from .reviewer import SYSTEM_PROMPT as REVIEWER_PROMPT
    from .tikz import SYSTEM_PROMPT as TIKZ_PROMPT
    from .solution_checker import SYSTEM_PROMPT as SOLUTION_CHECKER_PROMPT
    from .grammar_checker import SYSTEM_PROMPT as GRAMMAR_CHECKER_PROMPT
    from .clarity_checker import SYSTEM_PROMPT as CLARITY_CHECKER_PROMPT
    from .tikz_checker import SYSTEM_PROMPT as TIKZ_CHECKER_PROMPT

__all__ = [
    # Scanner
    "get_scanner_prompt",
    "SCANNER_PROMPTS",
    # Variant
    "get_variant_prompt",
    # Individual prompts
    "CLASSIFIER_PROMPT",
    "IDEA_PROMPT",
    "ALTERNATE_PROMPT",
    "REVIEWER_PROMPT",
    "TIKZ_PROMPT",
    "SOLUTION_CHECKER_PROMPT",
    "GRAMMAR_CHECKER_PROMPT",
    "CLARITY_CHECKER_PROMPT",
    "TIKZ_CHECKER_PROMPT",
]


def get_variant_prompt(variant_type: str) -> tuple[str, str]:
    """Get the system and user prompts for a variant type.
    
    Args:
        variant_type: Type of variant (numerical, context, conceptual, calculus)
        
    Returns:
        Tuple of (system_prompt, user_template)
        
    Raises:
        ValueError: If variant_type is not valid
    """
    from vbagent.agents.variant import get_variant_prompt as _get_variant_prompt
    return _get_variant_prompt(variant_type)


def __getattr__(name: str):
    """Lazy import of prompt modules."""
    if name in ("get_scanner_prompt", "SCANNER_PROMPTS"):
        from . import scanner
        return getattr(scanner, name)
    
    if name == "CLASSIFIER_PROMPT":
        from .classifier import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "IDEA_PROMPT":
        from .idea import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "ALTERNATE_PROMPT":
        from .alternate import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "REVIEWER_PROMPT":
        from .reviewer import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "TIKZ_PROMPT":
        from .tikz import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "SOLUTION_CHECKER_PROMPT":
        from .solution_checker import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "GRAMMAR_CHECKER_PROMPT":
        from .grammar_checker import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "CLARITY_CHECKER_PROMPT":
        from .clarity_checker import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    if name == "TIKZ_CHECKER_PROMPT":
        from .tikz_checker import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
