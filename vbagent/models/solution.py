"""Models for solution generation with diagram requirements."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class DiagramRequirement(BaseModel):
    """Diagram requirement with rich context for TikZ generation."""
    
    model_config = ConfigDict(extra='forbid')
    
    diagram_type: str = Field(
        description="Type of diagram: fbd, circuit, graph, optics, vector, geometry, etc."
    )
    description: str = Field(
        description="Brief description of what the diagram should show"
    )
    location: str = Field(
        default="inline",
        description="Where to place diagram: inline, after_solution, before_solution"
    )
    context: str = Field(
        default="",
        description="Detailed explanation for diagram generation (physics/chemistry/math context)"
    )
    values: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs of variables and their values to show in diagram"
    )
    labels: List[str] = Field(
        default_factory=list,
        description="List of labels that must appear in the diagram"
    )


class SolutionOutput(BaseModel):
    """Structured output from solution generation agent."""
    
    model_config = ConfigDict(extra='forbid')
    
    solution_latex: str = Field(
        description="Complete solution in LaTeX format (\\begin{solution}...\\end{solution})"
    )
    diagram_requirements: List[DiagramRequirement] = Field(
        default_factory=list,
        description="List of diagrams needed in the solution"
    )
    reasoning_notes: str = Field(
        default="",
        description="Internal notes about solution approach (not included in output)"
    )


__all__ = ["DiagramRequirement", "SolutionOutput"]
