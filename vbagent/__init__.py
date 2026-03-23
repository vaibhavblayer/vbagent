"""VBAgent - Physics question processing pipeline using OpenAI.

This package provides agents for processing physics questions:
- Classification: Analyze question images for metadata
- Scanning: Extract LaTeX from question images
- Variants: Generate problem variants (numerical, context, conceptual)
- Ideas: Extract physics concepts
- TikZ: Generate and check diagrams
- Review: QA checking
- Alternates: Generate alternate solutions

Usage as a library:
    from vbagent import classify, scan, generate_variant
    from vbagent.models import ClassificationResult, ScanResult
    from vbagent.config import get_config, set_config, AgentModelConfig

    # Classify an image
    result = classify("question.png")
    
    # Scan with classification
    latex_result = scan("question.png", result)
    
    # Generate a variant
    variant = generate_variant(latex_result.latex, "numerical")
    
    # Generate TikZ diagram
    tikz = generate_tikz("A free body diagram showing forces on a block")
    
    # Configure models
    config = get_config()
    config.agents["scanner"] = AgentModelConfig(model="gpt-5.4-mini")
    set_config(config)

Submodule access:
    from vbagent.agents import classify, scan, generate_tikz
    from vbagent.models import ClassificationResult, ScanResult, ReviewResult
    from vbagent.prompts import get_scanner_prompt, get_variant_prompt
    from vbagent.references import ReferenceStore, TikZStore
    from vbagent.config import VBAgentConfig
"""

from typing import TYPE_CHECKING

__version__ = "0.3.4"

# Lazy imports for library consumers
if TYPE_CHECKING:
    from vbagent.agents import (
        # Classification
        classify,
        # Scanning
        scan,
        scan_with_type,
        # Metadata Enrichment (NEW)
        classify_taxonomy,
        assess_difficulty,
        enrich_metadata,
        # Solution Orchestration
        create_solution_orchestrator,
        SolutionOrchestrator,
        # Ideas
        extract_ideas,
        generate_idea_latex,
        # Alternates
        generate_alternate,
        # Variants
        generate_variant,
        generate_numerical_variant,
        generate_context_variant,
        generate_conceptual_variant,
        generate_calculus_variant,
        get_variant_prompt,
        VALID_VARIANT_TYPES,
        # TikZ generation
        generate_tikz,
        validate_tikz_output,
        # FBD generation
        generate_fbd,
        validate_fbd_output,
        # QA Checkers
        check_solution,
        check_grammar,
        check_clarity,
        check_tikz,
        check_tikz_with_patch,
        # Review
        review_problem,
        review_problem_sync,
        # Problem selection
        discover_problems,
        select_random,
        load_problem_context,
        ProblemContext,
        # Base utilities
        create_agent,
        run_agent,
        run_agent_sync,
        encode_image,
        create_image_message,
    )
    from vbagent.models import (
        ClassificationResult,
        ScanResult,
        IdeaResult,
        PipelineResult,
        ReviewResult,
        ReviewStats,
        Suggestion,
        ReviewIssueType,
        # Metadata models
        TaxonomyClassification,
        EnrichedMetadata,
        # Difficulty from classification
        DifficultyAssessment,
    )
    from vbagent.config import (
        VBAgentConfig,
        AgentModelConfig,
        get_config,
        set_config,
        save_config,
        reset_config,
        get_model,
        get_model_settings,
        AGENT_TYPES,
        MODELS,
    )

__all__ = [
    # Version
    "__version__",
    # Classification
    "classify",
    # Scanning
    "scan",
    "scan_with_type",
    # Metadata Enrichment (NEW)
    "classify_taxonomy",
    "assess_difficulty",
    "enrich_metadata",
    # Solution Orchestration
    "create_solution_orchestrator",
    "SolutionOrchestrator",
    # Ideas
    "extract_ideas",
    "generate_idea_latex",
    # Alternates
    "generate_alternate",
    # Variants
    "generate_variant",
    "generate_numerical_variant",
    "generate_context_variant",
    "generate_conceptual_variant",
    "generate_calculus_variant",
    "get_variant_prompt",
    "VALID_VARIANT_TYPES",
    # TikZ generation
    "generate_tikz",
    "validate_tikz_output",
    # FBD generation
    "generate_fbd",
    "validate_fbd_output",
    # QA Checkers
    "check_solution",
    "check_grammar",
    "check_clarity",
    "check_tikz",
    "check_tikz_with_patch",
    # Review
    "review_problem",
    "review_problem_sync",
    # Problem selection
    "discover_problems",
    "select_random",
    "load_problem_context",
    "ProblemContext",
    # Agent utilities
    "create_agent",
    "run_agent",
    "run_agent_sync",
    "encode_image",
    "create_image_message",
    # Models
    "ClassificationResult",
    "ScanResult",
    "IdeaResult",
    "PipelineResult",
    "ReviewResult",
    "ReviewStats",
    "Suggestion",
    "ReviewIssueType",
    # Metadata models
    "TaxonomyClassification",
    "EnrichedMetadata",
    "DifficultyAssessment",
    # Configuration
    "VBAgentConfig",
    "AgentModelConfig",
    "get_config",
    "set_config",
    "save_config",
    "reset_config",
    "get_model",
    "get_model_settings",
    "AGENT_TYPES",
    "MODELS",
]


def __getattr__(name: str):
    """Lazy import to avoid loading heavy dependencies until needed."""
    # Agent functions
    if name in (
        "classify",
        "scan", "scan_with_type",
        "classify_taxonomy", "assess_difficulty", "enrich_metadata",
        "extract_ideas", "generate_idea_latex",
        "generate_alternate",
        "generate_variant", "generate_numerical_variant", "generate_context_variant",
        "generate_conceptual_variant", "generate_calculus_variant",
        "get_variant_prompt", "VALID_VARIANT_TYPES",
        "generate_tikz", "validate_tikz_output",
        "generate_fbd", "validate_fbd_output",
        "check_solution", "check_grammar", "check_clarity", "check_tikz", "check_tikz_with_patch",
        "review_problem", "review_problem_sync",
        "discover_problems", "select_random", "load_problem_context", "ProblemContext",
        "create_agent", "run_agent", "run_agent_sync",
        "encode_image", "create_image_message",
    ):
        from vbagent import agents
        return getattr(agents, name)
    
    # Orchestrator
    if name in ("create_solution_orchestrator", "SolutionOrchestrator"):
        from vbagent.agents.orchestration.solution_orchestrator import (
            create_solution_orchestrator,
            SolutionOrchestrator,
        )
        return create_solution_orchestrator if name == "create_solution_orchestrator" else SolutionOrchestrator
    
    # Models
    if name in (
        "ClassificationResult", "ScanResult", "IdeaResult",
        "PipelineResult", "ReviewResult", "ReviewStats",
        "Suggestion", "ReviewIssueType",
        "TaxonomyClassification", "DifficultyAssessment", "EnrichedMetadata",
    ):
        from vbagent import models
        return getattr(models, name)
    
    # Configuration
    if name in (
        "VBAgentConfig", "AgentModelConfig",
        "get_config", "set_config", "save_config", "reset_config",
        "get_model", "get_model_settings",
        "AGENT_TYPES", "MODELS",
    ):
        from vbagent import config
        return getattr(config, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
