"""Pydantic models for the solution video pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Script agent models
# ---------------------------------------------------------------------------

class ScriptSegment(BaseModel):
    """A single segment of the narration script."""
    model_config = ConfigDict(extra='forbid')

    segment_type: Literal[
        "intro", "problem_statement", "diagram_description",
        "approach", "step", "substep", "result", "recap", "outro",
    ] = Field(description="Type of this segment")
    narration: str = Field(
        description=(
            "The spoken narration text for this segment. "
            "Write naturally, as if a tutor is explaining to a student. "
            "Use pauses indicated by '...' for emphasis."
        ),
    )
    visual_cue: str = Field(
        description=(
            "What should appear on screen during this narration. "
            "e.g. 'Show problem text', 'Highlight equation 3', "
            "'Draw FBD with forces labeled', 'Transform equation LHS to RHS'."
        ),
    )
    latex: str = Field(
        default="",
        description=(
            "Key LaTeX expression shown during this segment (if any). "
            "e.g. 'F = ma', '\\\\int_0^T v\\\\,dt = s'."
        ),
    )
    duration_hint: float = Field(
        default=5.0,
        description="Estimated duration in seconds (2–15 range)",
    )


class SolutionScript(BaseModel):
    """Complete narration script for a solution video."""
    model_config = ConfigDict(extra='forbid')

    title: str = Field(
        description="Short title for the video (e.g. 'Projectile Motion — Range Formula')")
    segments: list[ScriptSegment] = Field(
        description="Ordered list of narration segments")
    total_duration_estimate: float = Field(
        description="Estimated total video duration in seconds",
    )
    key_equations: list[str] = Field(
        default_factory=list,
        description="List of important LaTeX equations used in the solution",
    )


# ---------------------------------------------------------------------------
# Video coder models
# ---------------------------------------------------------------------------

class VideoSceneCode(BaseModel):
    """Output from the video coder — Manim code for solution presentation."""
    model_config = ConfigDict(extra='forbid')

    scene_name: str = Field(
        default="SolutionVideo",
        description="Name of the Manim Scene class",
    )
    code: str = Field(
        description="Complete Python file with Manim scene code",
    )
    render_flags: str = Field(
        default="-pql",
        description="Manim CLI flags for rendering",
    )


class SegmentSceneCode(BaseModel):
    """Output from the per-segment coder — a complete Scene class for one segment."""
    model_config = ConfigDict(extra='forbid')

    scene_name: str = Field(
        description="PascalCase Scene class name (e.g. Segment01Intro, Segment03Step)",
    )
    code: str = Field(
        description="Complete Scene class code (just the class, no imports, no config)",
    )


class VideoFix(BaseModel):
    """Output from the video fixer agent."""
    model_config = ConfigDict(extra='forbid')

    code: str = Field(description="Fixed Python file")
    what_changed: str = Field(description="Brief description of the fix")


# ---------------------------------------------------------------------------
# Voice models
# ---------------------------------------------------------------------------

class VoiceSegment(BaseModel):
    """A single audio segment with timing metadata."""
    model_config = ConfigDict(extra='forbid')

    index: int = Field(
        description="Segment index (0-based, matches script segment order)")
    text: str = Field(description="The narration text that was spoken")
    audio_path: str = Field(
        description="Path to the audio file for this segment")
    duration: float = Field(description="Actual audio duration in seconds")


class VoiceResult(BaseModel):
    """Complete voice generation result."""
    model_config = ConfigDict(extra='forbid')

    segments: list[VoiceSegment] = Field(description="Audio segments in order")
    total_duration: float = Field(
        description="Total audio duration in seconds")
    voice: str = Field(default="alloy", description="TTS voice used")
    output_dir: str = Field(description="Directory containing audio files")


# ---------------------------------------------------------------------------
# Composer models
# ---------------------------------------------------------------------------

class ComposerResult(BaseModel):
    """Result of composing video + audio into final output."""
    model_config = ConfigDict(extra='forbid')

    video_path: str = Field(description="Path to the final composed video")
    duration: float = Field(description="Final video duration in seconds")
    resolution: str = Field(description="Video resolution (e.g. '1080x1920')")
