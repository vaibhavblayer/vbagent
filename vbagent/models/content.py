"""Content generation result data models.

This module consolidates models for content generation agents:
- ScanResult: LaTeX extraction from scanner agent
- IdeaResult: Physics concepts from idea agent
"""

from pydantic import BaseModel, Field


class ScanResult(BaseModel):
    """Result from the Scanner Agent.
    
    Contains extracted LaTeX and diagram information.
    """
    latex: str = Field(description="Extracted LaTeX code")
    has_diagram: bool = Field(default=False, description="Whether the question has a diagram")
    raw_diagram_description: str | None = Field(default=None, description="Description of diagram if present")


class IdeaResult(BaseModel):
    """Result from the Idea Agent.
    
    Contains extracted physics concepts and problem-solving ideas.
    Used as output_type for structured outputs with openai-agents SDK.
    """
    concepts: list[str] = Field(default_factory=list, description="Primary physics concepts")
    formulas: list[str] = Field(default_factory=list, description="Key formulas used")
    techniques: list[str] = Field(default_factory=list, description="Problem-solving techniques")
    difficulty_factors: list[str] = Field(default_factory=list, description="What makes this problem difficult")
