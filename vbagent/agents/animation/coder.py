"""Animation coder agent — generates Manim scene code."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vbagent.agents.animation.models import AnimationAssessment, AnimationCode
from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.prompts.animation.coder import get_coder_prompt


def _get_problem_id(image_path: str | None, problem_latex: str) -> str | None:
    """Derive a problem_id for caching from the input."""
    if image_path:
        return Path(image_path).stem
    if problem_latex:
        import hashlib
        return "tex_" + hashlib.sha256(problem_latex[:500].encode()).hexdigest()[:12]
    return None


def generate_animation(
    assessment: AnimationAssessment,
    problem_latex: str = "",
    image_path: str | None = None,
    solution_latex: str = "",
    show_spinner: bool = True,
    use_cache: bool = True,
    dim_config: dict | None = None,
) -> AnimationCode:
    """Generate Manim animation code from an assessment.

    Uses pipeline cache to avoid re-generating for the same problem.
    """
    # Default dimensions: vertical 1080x1920 @ 60fps
    if dim_config is None:
        dim_config = {"pixel_width": 1080, "pixel_height": 1920, "frame_rate": 60}
    # Check cache
    problem_id = _get_problem_id(image_path, problem_latex)
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cached = cache.get(problem_id, "animation_code")
        if cached and isinstance(cached, str) and cached.strip():
            # animation_code is stored as raw Python text
            # Try to extract scene name from the code
            import re
            scene_match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', cached)
            scene_name = scene_match.group(1) if scene_match else "ProblemScene"
            return AnimationCode(scene_name=scene_name, code=cached)

    agent = create_agent(
        name="AnimationCoder",
        instructions=get_coder_prompt(),
        output_type=AnimationCode,
        agent_type="animation_coder",
    )

    # Build detailed input for the coder
    user_text = f"## Animation Request\n\n"
    user_text += f"**Mode**: {assessment.mode}\n"
    user_text += f"**Type**: {assessment.animation_type}\n"
    user_text += f"**Duration**: ~{assessment.duration_hint}s\n\n"
    user_text += f"**Scene Config** (MUST include at top of file):\n"
    user_text += f"```python\n"
    user_text += f"config.frame_rate = {dim_config['frame_rate']}\n"
    user_text += f"config.pixel_width = {dim_config['pixel_width']}\n"
    user_text += f"config.pixel_height = {dim_config['pixel_height']}\n"
    user_text += f"```\n\n"
    user_text += f"**Description**:\n{assessment.concept_description}\n\n"

    if assessment.key_parameters:
        params = ", ".join(f"{p.name} = {p.value}" for p in assessment.key_parameters)
        user_text += f"**Parameters**: {params}\n\n"

    if problem_latex:
        user_text += f"## Problem\n\n{problem_latex}\n\n"
    if solution_latex:
        user_text += f"## Solution\n\n{solution_latex}\n\n"

    user_text += "Generate the complete Manim scene file."

    if image_path:
        message = create_image_message(image_path, user_text)
    else:
        message = user_text

    result = run_agent_sync(agent, message, show_spinner=show_spinner, timeout=600)

    # Save to cache
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cache.set(problem_id, "animation_code", result.code)

    return result
