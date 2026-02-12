"""Agent modules for vbagent using openai-agents SDK.

Uses lazy imports to avoid loading heavy dependencies (openai, agents, mcp, pydantic)
until they are actually needed. This significantly improves CLI startup time.

Available agents and functions:
- classify: Classify physics question images
- scan, scan_with_type: Extract LaTeX from images
- extract_ideas, generate_idea_latex: Extract physics concepts
- generate_alternate: Generate alternate solutions
- generate_variant: Generate problem variants
- check_solution, check_grammar, check_clarity, check_tikz: QA checkers
"""

from typing import TYPE_CHECKING

# Only import for type checking - avoids heavy runtime imports
if TYPE_CHECKING:
    from .base import (
        encode_image,
        create_image_message,
        create_agent,
        run_agent,
        run_agent_sync,
    )
    from .classifier import classifier_agent, classify
    from .scanner import scan, scan_with_type, create_scanner_agent
    from .idea import idea_agent_json, idea_agent_latex, extract_ideas, generate_idea_latex
    from .alternate import alternate_agent, generate_alternate, extract_answer
    from .variant import (
        generate_variant,
        generate_numerical_variant,
        generate_context_variant,
        generate_conceptual_variant,
        generate_calculus_variant,
        get_variant_prompt,
        VALID_VARIANT_TYPES,
    )
    from .selector import (
        ProblemContext,
        discover_problems,
        select_random,
        load_problem_context,
    )
    from .solution_checker import (
        solution_checker_agent,
        check_solution,
        has_solution_passed,
    )
    from .grammar_checker import (
        grammar_checker_agent,
        check_grammar,
        has_grammar_passed,
    )
    from .clarity_checker import (
        clarity_checker_agent,
        check_clarity,
        has_clarity_passed,
    )
    from .tikz_checker import (
        tikz_checker_agent,
        check_tikz,
        check_tikz_with_patch,
        has_tikz_passed,
        has_tikz_environment,
        PatchResult,
    )
    from .tikz import (
        generate_tikz,
        create_tikz_agent,
        validate_tikz_output,
        search_tikz_reference,
    )
    from .fbd import (
        generate_fbd,
        create_fbd_agent,
        validate_fbd_output,
        search_fbd_reference,
    )
    from .reviewer import (
        review_problem,
        review_problem_sync,
        ReviewAgentError,
        ReviewError,
        ReviewErrorType,
    )


__all__ = [
    # Base utilities
    "encode_image",
    "create_image_message",
    "create_agent",
    "run_agent",
    "run_agent_sync",
    # Classifier
    "classifier_agent",
    "classify",
    # Scanner
    "scan",
    "scan_with_type",
    "create_scanner_agent",
    # Idea extraction
    "idea_agent_json",
    "idea_agent_latex",
    "extract_ideas",
    "generate_idea_latex",
    # Alternate solutions
    "alternate_agent",
    "generate_alternate",
    "extract_answer",
    # Variants
    "generate_variant",
    "generate_numerical_variant",
    "generate_context_variant",
    "generate_conceptual_variant",
    "generate_calculus_variant",
    "get_variant_prompt",
    "VALID_VARIANT_TYPES",
    # Problem selection
    "ProblemContext",
    "discover_problems",
    "select_random",
    "load_problem_context",
    # Solution checker
    "solution_checker_agent",
    "check_solution",
    "has_solution_passed",
    # Grammar checker
    "grammar_checker_agent",
    "check_grammar",
    "has_grammar_passed",
    # Clarity checker
    "clarity_checker_agent",
    "check_clarity",
    "has_clarity_passed",
    # TikZ checker
    "tikz_checker_agent",
    "check_tikz",
    "check_tikz_with_patch",
    "has_tikz_passed",
    "has_tikz_environment",
    "PatchResult",
    # TikZ generator
    "generate_tikz",
    "create_tikz_agent",
    "validate_tikz_output",
    "search_tikz_reference",
    # FBD generator
    "generate_fbd",
    "create_fbd_agent",
    "validate_fbd_output",
    "search_fbd_reference",
    # Reviewer
    "review_problem",
    "review_problem_sync",
    "ReviewAgentError",
    "ReviewError",
    "ReviewErrorType",
]


def __getattr__(name: str):
    """Lazy import of agent modules to speed up CLI startup."""
    if name in ("encode_image", "create_image_message", "create_agent", "run_agent", "run_agent_sync"):
        from . import base
        return getattr(base, name)
    
    if name in ("classifier_agent", "classify"):
        from . import classifier
        return getattr(classifier, name)
    
    if name in ("scan", "scan_with_type", "create_scanner_agent"):
        from . import scanner
        return getattr(scanner, name)
    
    if name in ("idea_agent_json", "idea_agent_latex", "extract_ideas", "generate_idea_latex"):
        from . import idea
        return getattr(idea, name)
    
    if name in ("alternate_agent", "generate_alternate", "extract_answer"):
        from . import alternate
        return getattr(alternate, name)
    
    if name in (
        "generate_variant", "generate_numerical_variant", "generate_context_variant",
        "generate_conceptual_variant", "generate_calculus_variant",
        "get_variant_prompt", "VALID_VARIANT_TYPES",
    ):
        from . import variant
        return getattr(variant, name)
    
    if name in ("ProblemContext", "discover_problems", "select_random", "load_problem_context"):
        from . import selector
        return getattr(selector, name)
    
    if name in ("solution_checker_agent", "check_solution", "has_solution_passed"):
        from . import solution_checker
        return getattr(solution_checker, name)
    
    if name in ("grammar_checker_agent", "check_grammar", "has_grammar_passed"):
        from . import grammar_checker
        return getattr(grammar_checker, name)
    
    if name in ("clarity_checker_agent", "check_clarity", "has_clarity_passed"):
        from . import clarity_checker
        return getattr(clarity_checker, name)
    
    if name in ("tikz_checker_agent", "check_tikz", "check_tikz_with_patch", "has_tikz_passed", "has_tikz_environment", "PatchResult"):
        from . import tikz_checker
        return getattr(tikz_checker, name)
    
    if name in ("generate_tikz", "create_tikz_agent", "validate_tikz_output", "search_tikz_reference"):
        from . import tikz
        return getattr(tikz, name)
    
    if name in ("generate_fbd", "create_fbd_agent", "validate_fbd_output", "search_fbd_reference"):
        from . import fbd
        return getattr(fbd, name)
    
    if name in ("review_problem", "review_problem_sync", "ReviewAgentError", "ReviewError", "ReviewErrorType"):
        from . import reviewer
        return getattr(reviewer, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
