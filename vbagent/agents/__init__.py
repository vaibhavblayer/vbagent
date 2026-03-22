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
    from .content_generation.scanner import scan, scan_with_type, create_scanner_agent
    from .classification.taxonomy_classifier import classify_taxonomy, create_taxonomy_classifier_agent
    from .classification.difficulty_assessor import assess_difficulty, create_difficulty_assessor_agent
    from .metadata.enricher import enrich_metadata, enrich_metadata_sync, enrich_metadata_parallel
    from .content_generation.idea import idea_agent_json, idea_agent_latex, extract_ideas, generate_idea_latex
    from .content_generation.alternate import alternate_agent, generate_alternate, extract_answer
    from .variants.variant import (
        generate_variant,
        generate_numerical_variant,
        generate_context_variant,
        generate_conceptual_variant,
        generate_calculus_variant,
        get_variant_prompt,
        VALID_VARIANT_TYPES,
    )
    from .selection.selector import (
        ProblemContext,
        discover_problems,
        select_random,
        load_problem_context,
    )
    from .quality.solution_checker import (
        solution_checker_agent,
        check_solution,
        has_solution_passed,
    )
    from .quality.grammar_checker import (
        grammar_checker_agent,
        check_grammar,
        has_grammar_passed,
    )
    from .quality.clarity_checker import (
        clarity_checker_agent,
        check_clarity,
        has_clarity_passed,
    )
    from .diagram.tikz_checker import (
        tikz_checker_agent,
        check_tikz,
        check_tikz_with_patch,
        has_tikz_passed,
        has_tikz_environment,
        PatchResult,
    )
    from .diagram.tikz import (
        generate_tikz,
        create_tikz_agent,
        validate_tikz_output,
        search_tikz_reference,
    )
    from .diagram.fbd import (
        generate_fbd,
        create_fbd_agent,
        validate_fbd_output,
        search_fbd_reference,
    )
    from .quality.reviewer import (
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
    # Metadata Enrichment (NEW)
    "classify_taxonomy",
    "create_taxonomy_classifier_agent",
    "assess_difficulty",
    "create_difficulty_assessor_agent",
    "enrich_metadata",
    "enrich_metadata_sync",
    "enrich_metadata_parallel",
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
        from .content_generation import scanner
        return getattr(scanner, name)
    
    if name in ("classify_taxonomy", "create_taxonomy_classifier_agent"):
        from .classification import taxonomy_classifier
        return getattr(taxonomy_classifier, name)
    
    if name in ("assess_difficulty", "create_difficulty_assessor_agent"):
        from .classification import difficulty_assessor
        return getattr(difficulty_assessor, name)
    
    if name in ("enrich_metadata", "enrich_metadata_sync", "enrich_metadata_parallel"):
        from .metadata import enricher
        return getattr(enricher, name)
    
    if name in ("idea_agent_json", "idea_agent_latex", "extract_ideas", "generate_idea_latex"):
        from .content_generation import idea
        return getattr(idea, name)
    
    if name in ("alternate_agent", "generate_alternate", "extract_answer"):
        from .content_generation import alternate
        return getattr(alternate, name)
    
    if name in (
        "generate_variant", "generate_numerical_variant", "generate_context_variant",
        "generate_conceptual_variant", "generate_calculus_variant",
        "get_variant_prompt", "VALID_VARIANT_TYPES",
    ):
        from .variants import variant
        return getattr(variant, name)
    
    if name in ("ProblemContext", "discover_problems", "select_random", "load_problem_context"):
        from .selection import selector
        return getattr(selector, name)
    
    if name in ("solution_checker_agent", "check_solution", "has_solution_passed"):
        from .quality import solution_checker
        return getattr(solution_checker, name)
    
    if name in ("grammar_checker_agent", "check_grammar", "has_grammar_passed"):
        from .quality import grammar_checker
        return getattr(grammar_checker, name)
    
    if name in ("clarity_checker_agent", "check_clarity", "has_clarity_passed"):
        from .quality import clarity_checker
        return getattr(clarity_checker, name)
    
    if name in ("tikz_checker_agent", "check_tikz", "check_tikz_with_patch", "has_tikz_passed", "has_tikz_environment", "PatchResult"):
        from .diagram import tikz_checker
        return getattr(tikz_checker, name)
    
    if name in ("generate_tikz", "create_tikz_agent", "validate_tikz_output", "search_tikz_reference"):
        from .diagram import tikz
        return getattr(tikz, name)
    
    if name in ("generate_fbd", "create_fbd_agent", "validate_fbd_output", "search_fbd_reference"):
        from .diagram import fbd
        return getattr(fbd, name)
    
    if name in ("review_problem", "review_problem_sync", "ReviewAgentError", "ReviewError", "ReviewErrorType"):
        from .quality import reviewer
        return getattr(reviewer, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
