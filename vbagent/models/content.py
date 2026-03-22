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
    
    Contains extracted concepts and problem-solving ideas.
    Used as output_type for structured outputs with openai-agents SDK.
    """
    topic: str = Field(default="", description="Primary topic (e.g., Mechanics, Thermodynamics, Organic Chemistry)")
    subtopic: str = Field(default="", description="Subtopic (e.g., Collision, Carnot Cycle, Aldol Condensation)")
    concepts: list[str] = Field(default_factory=list, description="Primary concepts tested")
    formulas: list[str] = Field(default_factory=list, description="Key formulas used (LaTeX)")
    techniques: list[str] = Field(default_factory=list, description="Problem-solving techniques")
    difficulty_factors: list[str] = Field(default_factory=list, description="What makes this problem difficult")


class ConceptEntry(BaseModel):
    """A single concept in the concept sheet."""
    name: str = Field(description="Concept name")
    description: str = Field(description="One-line description")
    formulas: list[str] = Field(default_factory=list, description="Key formulas (LaTeX)")
    frequency: int = Field(default=1, description="Number of problems using this concept")
    problem_refs: list[str] = Field(default_factory=list, description="Problem filenames referencing this concept")
    needs_diagram: bool = Field(default=False, description="Whether this concept benefits from a TikZ diagram")
    diagram_description: str = Field(default="", description="Description for TikZ diagram generation")


class ConceptGroup(BaseModel):
    """A group of concepts under a subtopic."""
    subtopic: str = Field(description="Subtopic name")
    entries: list[ConceptEntry] = Field(default_factory=list)


class ConceptSheet(BaseModel):
    """Structured concept sheet output from the concept agent."""
    title: str = Field(description="Sheet title (e.g., 'Mechanics — Collision')")
    topic: str = Field(description="Main topic")
    groups: list[ConceptGroup] = Field(default_factory=list, description="Concepts grouped by subtopic")


class CrossTopicAnalysis(BaseModel):
    """Result from the Cross-Topic Analyzer Agent.
    
    Identifies the best complementary topic to integrate into a problem.
    """
    source_topic: str = Field(description="Detected primary topic of the source problem")
    integration_topic: str = Field(description="The topic to integrate")
    integration_reasoning: str = Field(description="Why this integration is natural and valuable")
    integration_approach: str = Field(description="How the topics connect physically")
    difficulty_delta: str = Field(
        default="harder",
        description="Expected difficulty change: easier, same, or harder"
    )
    example_twist: str = Field(description="One-sentence preview of the variant")
