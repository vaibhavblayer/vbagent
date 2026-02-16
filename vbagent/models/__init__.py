"""Data models for vbagent.

Uses lazy imports to avoid loading pydantic until models are actually needed.

Available models:
- ClassificationResult: Result from image classification
- ScanResult: Result from LaTeX extraction
- IdeaResult: Extracted physics concepts
- PipelineResult: Full pipeline output
- ReviewResult, Suggestion, ReviewStats: QA review models
- VersionStore, StoredSuggestion: Version tracking
- BatchResult, BatchStats: Batch processing models
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .classification import ClassificationResult, QuestionType, Difficulty, DifficultyAssessment, DiagramCategory
    from .structural import StructuralClassification
    from .content import ScanResult, IdeaResult
    from .diagram import TikZRequirements, TikZError, TikZFix, TikZValidation
    from .quality import ReviewIssueType, Suggestion, ReviewResult, ReviewStats, DiffError, DiffErrorType, DiffResult
    from .workflow import PipelineResult, ProcessingStatus, ImageRecord, BatchDatabase, AgentCall, SolutionPlan, AgentOutput, SolutionResult
    from .version_store import SuggestionStatus, StoredSuggestion, VersionStore
    from .diff import generate_unified_diff, apply_unified_diff, apply_diff, parse_diff
    from .metadata import TaxonomyClassification, EnrichedMetadata

__all__ = [
    # Classification
    "ClassificationResult",
    "QuestionType",
    "Difficulty",
    "DiagramCategory",
    "StructuralClassification",
    # Scan
    "ScanResult",
    # Idea
    "IdeaResult",
    # Diagram
    "TikZRequirements",
    "TikZError",
    "TikZFix",
    "TikZValidation",
    # Quality
    "ReviewIssueType",
    "Suggestion",
    "ReviewResult",
    "ReviewStats",
    "DiffError",
    "DiffErrorType",
    "DiffResult",
    # Workflow
    "PipelineResult",
    "ProcessingStatus",
    "ImageRecord",
    "BatchDatabase",
    "AgentCall",
    "SolutionPlan",
    "AgentOutput",
    "SolutionResult",
    # Version store
    "SuggestionStatus",
    "StoredSuggestion",
    "VersionStore",
    # Diff utilities
    "generate_unified_diff",
    "apply_unified_diff",
    "apply_diff",
    "parse_diff",
    # Metadata (NEW)
    "TaxonomyClassification",
    "EnrichedMetadata",
    "DifficultyAssessment",
]


def __getattr__(name: str):
    """Lazy import of model classes to speed up CLI startup."""
    if name in ("ClassificationResult", "QuestionType", "Difficulty", "DiagramCategory"):
        from . import classification
        return getattr(classification, name)
    
    if name == "StructuralClassification":
        from .structural import StructuralClassification
        return StructuralClassification
    
    if name in ("ScanResult", "IdeaResult"):
        from . import content
        return getattr(content, name)
    
    if name in ("TikZRequirements", "TikZError", "TikZFix", "TikZValidation"):
        from . import diagram
        return getattr(diagram, name)
    
    if name in ("PipelineResult", "ProcessingStatus", "ImageRecord", "BatchDatabase", "AgentCall", "SolutionPlan", "AgentOutput", "SolutionResult"):
        from . import workflow
        return getattr(workflow, name)
    
    if name in ("ReviewIssueType", "Suggestion", "ReviewResult", "ReviewStats", "DiffError", "DiffErrorType", "DiffResult"):
        from . import quality
        return getattr(quality, name)
    
    if name in ("SuggestionStatus", "StoredSuggestion", "VersionStore"):
        from . import version_store
        return getattr(version_store, name)
    
    if name in ("generate_unified_diff", "apply_unified_diff", "apply_diff", "parse_diff"):
        from . import diff
        return getattr(diff, name)
    
    if name in ("TaxonomyClassification", "EnrichedMetadata"):
        from . import metadata
        return getattr(metadata, name)
    
    if name == "DifficultyAssessment":
        from .classification import DifficultyAssessment
        return DifficultyAssessment
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
