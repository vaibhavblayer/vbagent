"""Per-segment coder agent — generates a Manim Scene class for one script segment."""

from __future__ import annotations

from vbagent.agents.solution_video.models import ScriptSegment, SegmentSceneCode
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.solution_video.segment_coder import get_segment_coder_prompt


def generate_segment_code(
    segment: ScriptSegment,
    segment_index: int,
    total_segments: int,
    previous_summaries: list[str],
    dim_config: dict,
    show_spinner: bool = True,
) -> SegmentSceneCode:
    """Generate a Manim Scene class for a single script segment.

    Args:
        segment: The script segment to visualize.
        segment_index: 0-based index of this segment.
        total_segments: Total number of segments.
        previous_summaries: Visual cue summaries from previous segments (for context).
        dim_config: Dimension config (pixel_width, pixel_height, frame_rate).
        show_spinner: Show progress spinner.

    Returns:
        SegmentSceneCode with a complete Scene class.
    """
    # Build the expected scene name
    type_label = segment.segment_type.replace(
        "_", " ").title().replace(" ", "")
    scene_name = f"Segment{segment_index + 1:02d}{type_label}"

    agent = create_agent(
        name=f"SegmentCoder[{segment_index + 1}/{total_segments}]",
        instructions=get_segment_coder_prompt(),
        output_type=SegmentSceneCode,
        agent_type="video_coder",
    )

    user_text = f"## Segment {segment_index + 1} of {total_segments}\n\n"
    user_text += f"**scene_name**: `{scene_name}`\n"
    user_text += f"**Type**: {segment.segment_type}\n"
    user_text += f"**Duration**: ~{segment.duration_hint:.0f}s\n\n"
    user_text += f"**Narration** (what the viewer hears):\n> {segment.narration}\n\n"
    user_text += f"**Visual cue** (what to show on screen):\n> {segment.visual_cue}\n\n"

    if segment.latex:
        user_text += f"**Key LaTeX**: `{segment.latex}`\n\n"

    if previous_summaries:
        user_text += "**Previous segments showed**:\n"
        for i, summary in enumerate(previous_summaries):
            user_text += f"  {i + 1}. {summary}\n"
        user_text += "\n"

    user_text += (
        "Generate ONLY the Scene class. No imports, no config."
    )

    result = run_agent_sync(
        agent, user_text, show_spinner=show_spinner, timeout=600)

    return result
