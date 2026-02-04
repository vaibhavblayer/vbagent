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
    from .classification import ClassificationResult, QuestionType, Difficulty, DiagramType
    from .scan import ScanResult
    from .idea import IdeaResult
    from .pipeline import PipelineResult
    from .review import ReviewIssueType, Suggestion, ReviewResult, ReviewStats
    from .version_store import SuggestionStatus, StoredSuggestion, VersionStore
    from .batch import BatchDatabase, ImageRecord, ProcessingStatus
    from .diff import generate_unified_diff, apply_unified_diff, apply_diff, parse_diff

__all__ = [
    # Classification
    "ClassificationResult",
    "QuestionType",
    "Difficulty",
    "DiagramType",
    # Scan
    "ScanResult",
    # Idea
    "IdeaResult",
    # Pipeline
    "PipelineResult",
    # Review
    "ReviewIssueType",
    "Suggestion",
    "ReviewResult",
    "ReviewStats",
    # Version store
    "SuggestionStatus",
    "StoredSuggestion",
    "VersionStore",
    # Batch
    "BatchDatabase",
    "ImageRecord",
    "ProcessingStatus",
    # Diff utilities
    "generate_unified_diff",
    "apply_unified_diff",
    "apply_diff",
    "parse_diff",
]


def __getattr__(name: str):
    """Lazy import of model classes to speed up CLI startup."""
    if name in ("ClassificationResult", "QuestionType", "Difficulty", "DiagramType"):
        from . import classification
        return getattr(classification, name)
    
    if name == "ScanResult":
        from .scan import ScanResult
        return ScanResult
    
    if name == "IdeaResult":
        from .idea import IdeaResult
        return IdeaResult
    
    if name == "PipelineResult":
        from .pipeline import PipelineResult
        return PipelineResult
    
    if name in ("ReviewIssueType", "Suggestion", "ReviewResult", "ReviewStats"):
        from . import review
        return getattr(review, name)
    
    if name in ("SuggestionStatus", "StoredSuggestion", "VersionStore"):
        from . import version_store
        return getattr(version_store, name)
    
    if name in ("BatchDatabase", "ImageRecord", "ProcessingStatus"):
        from . import batch
        return getattr(batch, name)
    
    if name in ("generate_unified_diff", "apply_unified_diff", "apply_diff", "parse_diff"):
        from . import diff
        return getattr(diff, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
