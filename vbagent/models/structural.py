"""Structural classification model for Stage 1.

Stage 1 only extracts structural metadata needed for routing.
Semantic metadata (chapter, topic, difficulty) is deferred to Stage 4 & 5.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class StructuralClassification(BaseModel):
    """Stage 1: Structural classification (routing metadata only)"""
    model_config = ConfigDict(extra='forbid')
    
    question_type: Literal[
        "mcq_sc", "mcq_mc", "subjective",
        "assertion_reason", "passage", "match"
    ] = Field(description="Question format type")
    
    has_diagram: bool = Field(description="Whether image contains a diagram")
    
    diagram_type: str = Field(
        default="none",
        description="Type of diagram: free_body, circuit, graph, optics, geometry, none"
    )
    
    num_options: Optional[int] = Field(
        default=None,
        description="Number of options for MCQ questions"
    )
    
    num_subquestions: int = Field(
        default=1,
        description="Number of sub-questions (for passage type)"
    )
    
    requires_calculus: bool = Field(
        default=False,
        description="Whether problem requires calculus"
    )
    
    key_concepts: list[str] = Field(
        default_factory=list,
        description="Initial concept hints (freeform, for context)"
    )
    
    confidence: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="Classification confidence"
    )
    
    classified_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


__all__ = ["StructuralClassification"]
