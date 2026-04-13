"""Pydantic models for concept organization output."""

from pydantic import BaseModel, Field


class Concept(BaseModel):
    """A single concept with problem references and optional nested sub-items."""
    text: str = Field(description="Main concept description (use LaTeX for all math symbols)")
    problem_numbers: list[int] = Field(description="Problem numbers that use this concept")
    sub_items: list[str] = Field(default_factory=list, description="Nested sub-concepts or cases (use LaTeX for math)")


class Formula(BaseModel):
    """A formula with description and problem references."""
    latex: str = Field(description="Formula in LaTeX format (without $ delimiters)")
    description: str = Field(description="Brief description (use LaTeX for any math)")
    problem_numbers: list[int] = Field(description="Problem numbers that use this formula")


class Technique(BaseModel):
    """A problem-solving technique with problem references and optional steps."""
    text: str = Field(description="Main technique description (use LaTeX for math)")
    problem_numbers: list[int] = Field(description="Problem numbers that use this technique")
    sub_items: list[str] = Field(default_factory=list, description="Nested technique steps (use LaTeX for math)")


class TopicConcepts(BaseModel):
    """Organized concepts for a single topic."""
    topic_name: str = Field(description="Name of the topic")
    concepts: list[Concept] = Field(default_factory=list, description="Key concepts for this topic")
    formulas: list[Formula] = Field(default_factory=list, description="Important formulas for this topic")
    techniques: list[Technique] = Field(default_factory=list, description="Problem-solving techniques for this topic")


class OrganizedConcepts(BaseModel):
    """Complete organized output for all topics in a chapter."""
    topics: list[TopicConcepts] = Field(description="Organized concepts by topic")
