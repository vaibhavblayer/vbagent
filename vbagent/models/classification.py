"""Classification result data model."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


QuestionType = Literal[
    "mcq_sc",
    "mcq_mc",
    "subjective",
    "assertion_reason",
    "passage",
    "match"
]

Difficulty = Literal["easy", "medium", "hard"]

DiagramType = Literal["graph", "circuit", "free_body", "geometry", "none"]


class ClassificationResult(BaseModel):
    """Result from the Classifier Agent.
    
    Contains metadata extracted from a question image.
    Used as output_type for structured outputs with openai-agents SDK.
    """
    question_type: QuestionType = Field(description="Type of question")
    difficulty: Difficulty = Field(description="Difficulty level")
    chapter: str = Field(description="Chapter name from predefined list")
    topic: str = Field(description="Topic name from predefined list")
    subtopic: str | None = Field(default=None, description="Specific subtopic")
    has_diagram: bool = Field(description="Whether the question contains a diagram")
    diagram_type: DiagramType | None = Field(default=None, description="Type of diagram if present")
    num_options: int | None = Field(default=None, description="Number of options if MCQ")
    key_concepts: list[str] = Field(default_factory=list, description="Key concepts")
    requires_calculus: bool = Field(default=False, description="Whether calculus is required")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Classification confidence")
    classified_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of classification")
    
    @field_validator('classified_at', mode='before')
    @classmethod
    def fix_classified_at(cls, v):
        """Ensure classified_at is a timestamp"""
        if not v or v in ["image", "latex", "generated", "combined"]:
            return datetime.now().isoformat()
        return v
