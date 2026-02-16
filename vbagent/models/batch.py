"""Batch processing database models.

DEPRECATED: This module is deprecated. Import from vbagent.models.workflow instead.
"""

# Re-export from workflow module for backward compatibility
from .workflow import (
    ProcessingStatus,
    ImageRecord,
    BatchDatabase,
)

__all__ = [
    "ProcessingStatus",
    "ImageRecord",
    "BatchDatabase",
]
