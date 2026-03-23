"""SketchReader agent — extracts structured intent from handwritten scribbles.

Unlike the unified classifier (which analyzes printed question images),
this agent interprets rough sketches: hand-drawn circuits, graphs,
equations, diagrams, and half-formed problem ideas.

Output: SketchAnalysis with topic hints, equations, diagram description,
values, labels, and what the user likely wants to create.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config


class SketchAnalysis(BaseModel):
    """Structured output from the SketchReader agent."""

    sketch_type: str = Field(
        description="What the sketch primarily shows: circuit, graph, fbd, optics, "
        "organic_structure, equation, geometric_figure, coordinate_geometry, mixed, text"
    )
    topic_hint: str = Field(
        default="",
        description="Inferred topic (e.g., 'RC circuit charging', 'projectile on incline')",
    )
    subtopic_hint: str = Field(
        default="",
        description="More specific subtopic if identifiable",
    )
    equations: list[str] = Field(
        default_factory=list,
        description="LaTeX equations visible or implied in the sketch",
    )
    diagram_description: str = Field(
        default="",
        description="Detailed description of the diagram for TikZ generation",
    )
    values_given: dict[str, str] = Field(
        default_factory=dict,
        description="Variable-value pairs visible in the sketch (e.g., {'R': '5Ω', 'V': '10V'})",
    )
    labels: list[str] = Field(
        default_factory=list,
        description="Labels that should appear in the diagram",
    )
    what_to_find: str = Field(
        default="",
        description="What the sketch suggests should be asked/found",
    )
    rough_answer: str = Field(
        default="",
        description="If an answer or result is visible in the sketch",
    )
    suggested_question_type: str = Field(
        default="subjective",
        description="Best question type for this sketch: mcq_sc, subjective, integer, etc.",
    )
    suggested_difficulty: str = Field(
        default="medium",
        description="Suggested difficulty: easy, medium, hard",
    )
    notes: str = Field(
        default="",
        description="Any other observations about the sketch",
    )


def _get_sketch_reader_prompt(subject: str) -> str:
    """Build the SketchReader system prompt."""
    return f"""You are an expert {subject} teacher analyzing a student's handwritten sketch or scribble.

This is NOT a printed question — it's a rough hand-drawn sketch that may contain:
- Hand-drawn diagrams (circuits, force diagrams, graphs, molecular structures)
- Handwritten equations or formulas
- Rough labels, arrows, annotations
- Half-formed problem ideas or notes
- Numerical values scattered around the sketch

Your job: interpret what the student INTENDED and extract structured information.

Be GENEROUS in interpretation — if a squiggly line near axes looks like a sine wave,
interpret it as "sinusoidal function, possibly SHM or AC signal".

Respond with ONLY a valid JSON object matching the SketchAnalysis schema.

Rules:
- sketch_type must be one of: circuit, graph, fbd, optics, organic_structure,
  equation, geometric_figure, coordinate_geometry, mixed, text
- equations should be valid LaTeX (e.g., "V = IR", "F = ma")
- diagram_description should be detailed enough for a TikZ agent to reproduce the sketch
- values_given: extract any numerical values with their variable names
- labels: list all text labels visible in the sketch
- what_to_find: infer what question could be asked about this setup
- If multiple sketches are on one page, describe all of them in diagram_description

For {subject} specifically:
- Physics: look for forces, circuits, optical elements, graphs, field lines
- Chemistry: look for molecular structures, reaction arrows, orbital diagrams
- Mathematics: look for coordinate axes, geometric figures, function curves

Respond with ONLY the JSON object."""


def create_sketch_reader_agent(subject: str | None = None):
    """Create the SketchReader agent."""
    subject = subject or get_config().subject
    return create_agent(
        name=f"SketchReader-{subject}",
        instructions=_get_sketch_reader_prompt(subject),
        output_type=SketchAnalysis,
        agent_type="classifier",
    )


def analyze_sketch(
    image_path: str,
    subject: str | None = None,
    show_spinner: bool = True,
) -> SketchAnalysis:
    """Analyze a handwritten sketch image.

    Args:
        image_path: Path to the sketch/scribble image
        subject: Subject context (physics/chemistry/mathematics)
        show_spinner: Whether to show spinner

    Returns:
        SketchAnalysis with extracted intent and structure
    """
    subject = subject or get_config().subject
    agent = create_sketch_reader_agent(subject)
    message = create_image_message(
        image_path,
        f"Analyze this handwritten {subject} sketch. Extract all information you can see — "
        "equations, diagram elements, labels, values, and what problem could be created from this.",
    )
    return run_agent_sync(agent, message, show_spinner=show_spinner, timeout=90)
