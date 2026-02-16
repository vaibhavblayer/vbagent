"""Review data models for QA Review Agent.

Pydantic models for structured review suggestions and results.

DEPRECATED: This module is deprecated. Import from vbagent.models.quality instead.
"""

# Re-export from quality module for backward compatibility
from .quality import (
    ReviewIssueType,
    Suggestion,
    ReviewResult,
    ReviewStats,
)

__all__ = [
    "ReviewIssueType",
    "Suggestion",
    "ReviewResult",
    "ReviewStats",
]
