"""Diagram-related models for VBAgent.

This module contains models for diagram analysis and TikZ generation/validation.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TikZRequirements(BaseModel):
    """TikZ generation requirements"""
    model_config = ConfigDict(extra='forbid')
    
    libraries: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    complexity_score: int = Field(ge=1, le=10, default=5)


class TikZError(BaseModel):
    """A single TikZ error"""
    model_config = ConfigDict(extra='forbid')
    
    type: str  # "syntax", "missing_library", "undefined_command"
    line: int
    message: str
    severity: Literal["error", "warning"] = "error"


class TikZFix(BaseModel):
    """A fix applied to TikZ code"""
    model_config = ConfigDict(extra='forbid')
    
    type: str
    description: str
    before: str
    after: str


class TikZValidation(BaseModel):
    """Output from Agent 7: TikZ Checker/Fixer"""
    model_config = ConfigDict(extra='allow')  # Allow for validation_metadata flexibility
    
    is_valid: bool
    compilation_status: Literal["success", "fixed", "failed"]
    fixed_tikz_code: Optional[str] = None
    
    errors_found: list[TikZError] = Field(default_factory=list)
    fixes_applied: list[TikZFix] = Field(default_factory=list)
    
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Contains: libraries_used, packages_required, complexity_score, compilation_time_ms
    
    validated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
