"""Models for solution generation with diagram requirements."""

from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field, ConfigDict


class DiagramRequirement(BaseModel):
    """Diagram requirement with rich context for TikZ generation.
    
    Phase 2 Enhancement: Added detailed specifications for intelligent
    diagram generation with step-by-step support and subject-specific context.
    """
    
    model_config = ConfigDict(extra='forbid')
    
    # Core identification
    diagram_id: str = Field(
        default="diagram_1",
        description="Unique identifier for this diagram (e.g., 'fbd_1', 'circuit_main', 'step_2_graph')"
    )
    diagram_type: str = Field(
        description="Type of diagram: fbd, circuit, graph, optics, organic_structure, function_graph, etc."
    )
    description: str = Field(
        description="Detailed description of what the diagram should show"
    )
    
    # Placement and sizing
    location: str = Field(
        default="inline",
        description="Where to place diagram: inline, after_solution, before_solution, after_step_N"
    )
    size: str = Field(
        default="medium",
        description="Diagram size: small, medium, large"
    )
    
    # Rich context for generation
    context: str = Field(
        default="",
        description="Detailed explanation for diagram generation (physics/chemistry/math context)"
    )
    values: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs of variables and their values to show in diagram (e.g., {'mass': '2kg', 'angle': '30°'})"
    )
    labels: List[str] = Field(
        default_factory=list,
        description="List of labels that must appear in the diagram (e.g., ['A', 'B', 'mg', 'N', 'T'])"
    )
    annotations: List[str] = Field(
        default_factory=list,
        description="Additional annotations or notes to add (e.g., ['Show direction of motion', 'Highlight equilibrium'])"
    )
    
    # Step-by-step support
    step_number: Optional[int] = Field(
        default=None,
        description="If this is a step-by-step diagram, which step it represents (1, 2, 3, etc.)"
    )
    depends_on: Optional[str] = Field(
        default=None,
        description="If this diagram builds on another, the diagram_id it depends on"
    )
    
    # Subject-specific context (Phase 2)
    physics_context: Optional[Dict[str, str]] = Field(
        default=None,
        description="Physics-specific: coordinate_system, forces, motion_type, reference_frame, etc."
    )
    chemistry_context: Optional[Dict[str, str]] = Field(
        default=None,
        description="Chemistry-specific: show_lone_pairs, show_charges, mechanism_step, stereochemistry, etc."
    )
    mathematics_context: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mathematics-specific: show_grid, axis_range, show_asymptotes, domain, range, etc."
    )


class SolutionOutput(BaseModel):
    """Structured output from solution generation agent.
    
    Phase 2 Enhancement: Supports multiple diagrams with detailed specifications
    and step-by-step solution support.
    """
    
    model_config = ConfigDict(extra='ignore')
    
    solution_latex: str = Field(
        description="Complete solution in LaTeX format (\\begin{solution}...\\end{solution})"
    )
    diagram_requirements: List[DiagramRequirement] = Field(
        default_factory=list,
        description=(
            "List of diagrams needed in the solution with detailed specifications. "
            "For every item, solution_latex must contain the exact marker "
            "'% DIAGRAM PLACEHOLDER: <diagram_id>' using the same diagram_id."
        )
    )
    reasoning_notes: str = Field(
        default="",
        description="Internal notes about solution approach (not included in output)"
    )
    
    # Answer marking
    answer_type: Literal["mcq", "integer", "subjective"] = Field(
        default="subjective",
        description="Type of answer: mcq (mark correct option), integer (\\ansint{N}), subjective (no marking)"
    )
    answer_value: Optional[str] = Field(
        default=None,
        description=(
            "The answer: lowercase option letter(s) for MCQ, integer for "
            "integer-type, None for subjective"
        )
    )
    match_option_replacement_latex: Optional[str] = Field(
        default=None,
        description=(
            "Match questions only: the complete correct option payload, "
            "without \\task or \\ans, when none of the four scanned code "
            "options matches the derived mapping. Null when an existing "
            "option already matches."
        ),
    )
    final_answer_latex: Optional[str] = Field(
        default=None,
        description=(
            "Concise answer-key-ready LaTeX for a subjective problem. "
            "Contains no derivation and no surrounding environment; None for "
            "MCQ and integer-type problems."
        ),
    )

    alternate_solution_recommended: bool = Field(
        default=False,
        description=(
            "Whether a genuinely different and pedagogically useful alternate "
            "solution method is worth generating. Set false for routine or "
            "one-method problems."
        ),
    )
    alternate_solution_hint: Optional[str] = Field(
        default=None,
        description=(
            "A short, actionable hint for the alternate-solution agent when "
            "alternate_solution_recommended is true; null otherwise."
        ),
    )
    
    # Additional metadata
    solution_steps: Optional[List[str]] = Field(
        default=None,
        description="List of solution steps for step-by-step diagrams"
    )
    key_concepts: Optional[List[str]] = Field(
        default=None,
        description="Key concepts used in this solution"
    )
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to handle both 'solution' and 'solution_latex' field names."""
        if isinstance(obj, dict):
            # If 'solution' is present but 'solution_latex' is not, copy it
            if 'solution' in obj and 'solution_latex' not in obj:
                obj = obj.copy()
                obj['solution_latex'] = obj.pop('solution')
        return super().model_validate(obj, **kwargs)


__all__ = ["DiagramRequirement", "SolutionOutput"]
