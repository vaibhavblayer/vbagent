"""Data models for solution orchestration.

DEPRECATED: This module is deprecated. Import from vbagent.models.workflow instead.
"""

# Re-export from workflow module for backward compatibility
from .workflow import (
    AgentCall,
    SolutionPlan,
    AgentOutput,
    SolutionResult,
)

__all__ = [
    "AgentCall",
    "SolutionPlan",
    "AgentOutput",
    "SolutionResult",
]
