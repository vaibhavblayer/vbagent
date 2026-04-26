"""Per-scene coder agent for multi-scene (explain) mode."""

from __future__ import annotations

from vbagent.agents.animation.models import SceneCode, ScenePlan
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.animation.scene_coder import get_scene_coder_prompt


def generate_scene(
    scene_plan: ScenePlan,
    scene_index: int,
    total_scenes: int,
    previous_summaries: list[str],
    dim_config: dict,
    show_spinner: bool = True,
) -> SceneCode:
    """Generate Manim code for a single scene.

    Args:
        scene_plan: The plan for this scene.
        scene_index: 1-based index of this scene.
        total_scenes: Total number of scenes.
        previous_summaries: Key concepts from previous scenes (for continuity).
        dim_config: Dimension config (pixel_width, pixel_height, frame_rate).
        show_spinner: Show progress spinner.

    Returns:
        SceneCode with the class definition.
    """
    agent = create_agent(
        name=f"SceneCoder[{scene_index}/{total_scenes}]",
        instructions=get_scene_coder_prompt(),
        output_type=SceneCode,
        agent_type="animation_coder",  # heavy model, xhigh reasoning
    )

    user_text = f"## Scene {scene_index} of {total_scenes}\n\n"
    user_text += f"**Class name**: `{scene_plan.scene_name}`\n"
    user_text += f"**Duration**: ~{scene_plan.duration_hint}s\n"
    user_text += f"**Key concept**: {scene_plan.key_concept}\n\n"
    user_text += f"**Description**:\n{scene_plan.description}\n\n"

    user_text += f"**Canvas**: {dim_config['pixel_width']}x{dim_config['pixel_height']} @ {dim_config['frame_rate']}fps\n\n"

    if previous_summaries:
        user_text += "**Previous scenes showed**:\n"
        for i, summary in enumerate(previous_summaries, 1):
            user_text += f"  {i}. {summary}\n"
        user_text += "\nBuild on these concepts but start fresh visually.\n"

    user_text += "\nGenerate ONLY the Scene class. No imports, no config."

    return run_agent_sync(agent, user_text, show_spinner=show_spinner, timeout=600)
