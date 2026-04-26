"""Animation assessor agent — decides if a problem benefits from animation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from vbagent.agents.animation.models import AnimationAssessment
from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.prompts.animation.assessor import get_assessor_prompt


def _get_problem_id(image_path: str | None, problem_latex: str) -> str | None:
    """Derive a problem_id for caching from the input."""
    if image_path:
        return Path(image_path).stem
    if problem_latex:
        import hashlib
        return "tex_" + hashlib.sha256(problem_latex[:500].encode()).hexdigest()[:12]
    return None


def assess_animation(
    problem_latex: str = "",
    image_path: str | None = None,
    solution_latex: str = "",
    show_spinner: bool = True,
    use_cache: bool = True,
) -> AnimationAssessment:
    """Assess whether a problem benefits from a Manim animation.

    Uses pipeline cache to avoid re-assessing the same problem.
    """
    # Check cache
    problem_id = _get_problem_id(image_path, problem_latex)
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cached = cache.get(problem_id, "animation_assessment")
        if cached and isinstance(cached, dict):
            return AnimationAssessment(**cached)

    agent = create_agent(
        name="AnimationAssessor",
        instructions=get_assessor_prompt(),
        output_type=AnimationAssessment,
        agent_type="animation_assessor",
    )

    # Build input
    user_text = ""
    if problem_latex:
        user_text += f"## Problem\n\n{problem_latex}\n\n"
    if solution_latex:
        user_text += f"## Solution\n\n{solution_latex}\n\n"
    if not user_text:
        user_text = "Assess the problem in the attached image."

    user_text += "\nShould this problem be animated? If yes, describe the animation."

    if image_path:
        message = create_image_message(image_path, user_text)
    else:
        message = user_text

    result = run_agent_sync(agent, message, show_spinner=show_spinner)

    # Save to cache
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cache.set(problem_id, "animation_assessment", result.model_dump())

    return result
