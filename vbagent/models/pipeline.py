"""Pipeline result data model.

DEPRECATED: This module is deprecated. Import from vbagent.models.workflow instead.
"""

# Re-export from workflow module for backward compatibility
from .workflow import PipelineResult

__all__ = ["PipelineResult"]
