"""Pydantic models for the concept notes pipeline."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Planner models
# ---------------------------------------------------------------------------

class DiagramSpec(BaseModel):
    """Specification for a diagram to generate."""
    model_config = ConfigDict(extra='forbid')

    diagram_id: str = Field(
        description="Unique ID like 'sec1_fig1', 'sec2_fig3'",
    )
    diagram_type: Literal["tikz", "pgfplot", "circuit", "fbd"] = Field(
        default="tikz",
        description="Type of diagram",
    )
    description: str = Field(
        description=(
            "Detailed description of what the diagram should show. "
            "Be specific: objects, labels, arrows, coordinates, colors."
        ),
    )
    caption: str = Field(
        description="LaTeX caption for the figure environment",
    )


class SubsectionPlan(BaseModel):
    """Plan for one subsection."""
    model_config = ConfigDict(extra='forbid')

    title: str = Field(description="Subsection title")
    content_type: Literal[
        "prose", "prose+equation", "prose+diagram",
        "prose+diagram+equation", "worked_example",
        "comparison_table", "summary", "traps",
    ] = Field(description="What kind of content this subsection contains")
    description: str = Field(
        description=(
            "Detailed description of what to cover. Include key equations, "
            "derivation steps, physical reasoning, and any JEE/NEET-specific points."
        ),
    )
    diagrams: list[DiagramSpec] = Field(
        default_factory=list,
        description="Diagrams needed in this subsection",
    )
    key_equations: list[str] = Field(
        default_factory=list,
        description="Important LaTeX equations to include (boxed)",
    )


class SectionPlan(BaseModel):
    """Plan for one major section."""
    model_config = ConfigDict(extra='forbid')

    title: str = Field(description="Section title")
    subsections: list[SubsectionPlan] = Field(
        description="Ordered list of subsections",
    )


class DocumentPlan(BaseModel):
    """Complete document plan from the planner agent."""
    model_config = ConfigDict(extra='forbid')

    title: str = Field(description="Document title")
    subtitle: str = Field(
        default="",
        description="Subtitle (e.g. 'Single Slit, Double Slit, and the Slab Variant')",
    )
    author: str = Field(
        default="10x Physics — JEE Notes",
        description="Author line",
    )
    sections: list[SectionPlan] = Field(
        description="Ordered list of major sections",
    )
    summary_table: bool = Field(
        default=True,
        description="Whether to include a summary formula table at the end",
    )


# ---------------------------------------------------------------------------
# Section writer models
# ---------------------------------------------------------------------------

class SectionContent(BaseModel):
    """Output from the section writer — LaTeX content for one section."""
    model_config = ConfigDict(extra='forbid')

    section_title: str = Field(description="The section title")
    latex: str = Field(
        description=(
            "Complete LaTeX for this section including \\section, \\subsection, "
            "equations, tables, prose. Use \\input{diagrams/ID.tex} for diagrams."
        ),
    )


# ---------------------------------------------------------------------------
# Notes result
# ---------------------------------------------------------------------------

class NotesResult(BaseModel):
    """Final result of the notes pipeline."""
    model_config = ConfigDict(extra='forbid')

    tex_path: str = Field(description="Path to the generated .tex file")
    pdf_path: Optional[str] = Field(
        default=None, description="Path to compiled PDF (if compiled)",
    )
    title: str = Field(description="Document title")
    sections: int = Field(description="Number of sections")
    diagrams: int = Field(description="Number of diagrams generated")
