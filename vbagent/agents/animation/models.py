"""Pydantic models for animation pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KeyParameter(BaseModel):
    """A single key-value parameter for the animation."""
    model_config = ConfigDict(extra='forbid')

    name: str = Field(description="Parameter name (e.g. 'v0', 'angle', 'mass')")
    value: str = Field(description="Parameter value with unit (e.g. '20 m/s', '45°')")


class AnimationAssessment(BaseModel):
    """Output from the assessor agent — should we animate, and what?"""
    model_config = ConfigDict(extra='forbid')

    should_animate: bool = Field(
        description="Whether this problem benefits from animation",
    )
    mode: Literal["problem", "concept", "none"] = Field(
        default="none",
        description=(
            "'problem' = animate the specific scenario from the question. "
            "'concept' = animate the underlying fundamental idea. "
            "'none' = no animation needed."
        ),
    )
    animation_type: str = Field(
        default="none",
        description=(
            "Category: trajectory, collision, shm, wave, circular_motion, "
            "rotation, optics, field_lines, energy, fluid, graph_evolution, other, none"
        ),
    )
    concept_description: str = Field(
        default="",
        description=(
            "Creative description of what the animation should show. "
            "For 'problem' mode: describe the specific scenario. "
            "For 'concept' mode: describe the fundamental idea to illustrate."
        ),
    )
    key_parameters: list[KeyParameter] = Field(
        default_factory=list,
        description="Physical parameters to use in the animation",
    )
    duration_hint: float = Field(
        default=20.0,
        description="Suggested duration in seconds (15–45 range)",
    )
    reason: str = Field(
        default="",
        description="Brief reason for the assessment decision",
    )


class AnimationCode(BaseModel):
    """Output from the coder agent — complete Manim scene."""
    model_config = ConfigDict(extra='forbid')

    scene_name: str = Field(
        default="ProblemScene",
        description="Name of the Manim Scene class",
    )
    code: str = Field(
        description="Complete Python file with Manim scene code",
    )
    render_flags: str = Field(
        default="-pql",
        description="Manim CLI flags for rendering (e.g. -pql for low quality preview)",
    )


class AnimationFix(BaseModel):
    """Output from the fixer agent."""
    model_config = ConfigDict(extra='forbid')

    code: str = Field(description="Fixed Python file")
    what_changed: str = Field(description="Brief description of the fix")


# ---------------------------------------------------------------------------
# Multi-scene (explain mode) models
# ---------------------------------------------------------------------------

class ScenePlan(BaseModel):
    """A single scene in a multi-scene animation plan."""
    model_config = ConfigDict(extra='forbid')

    scene_name: str = Field(description="PascalCase class name (e.g. UnpolarisedLight)")
    description: str = Field(description="Detailed visual description of what to animate")
    duration_hint: float = Field(default=20.0, description="Suggested duration in seconds (15–30)")
    key_concept: str = Field(description="One-line summary of what this scene teaches")


class AnimationPlan(BaseModel):
    """Output from the planner agent — sequence of scenes."""
    model_config = ConfigDict(extra='forbid')

    topic: str = Field(description="The topic being explained")
    scenes: list[ScenePlan] = Field(description="Ordered list of scenes")


class SceneCode(BaseModel):
    """Output from the coder agent for a single scene in multi-scene mode."""
    model_config = ConfigDict(extra='forbid')

    scene_name: str = Field(description="The Scene class name")
    code: str = Field(description="Complete Scene class code (just the class, no imports)")

