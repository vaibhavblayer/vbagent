"""Script writer agent — generates narration scripts for solution videos."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from vbagent.agents.solution_video.models import SolutionScript
from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.prompts.solution_video.script_writer import get_script_writer_prompt


def _get_problem_id(image_path: str | None, problem_latex: str) -> str | None:
    """Derive a problem_id for caching from the input."""
    if image_path:
        return Path(image_path).stem
    if problem_latex:
        return "tex_" + hashlib.sha256(problem_latex[:500].encode()).hexdigest()[:12]
    return None


def generate_script(
    problem_latex: str = "",
    solution_latex: str = "",
    image_path: str | None = None,
    show_spinner: bool = True,
    use_cache: bool = True,
) -> SolutionScript:
    """Generate a narration script for a solution video.

    Args:
        problem_latex: Problem statement in LaTeX.
        solution_latex: Complete solution in LaTeX.
        image_path: Optional path to problem image.
        show_spinner: Show progress spinner.
        use_cache: Use pipeline cache.

    Returns:
        SolutionScript with ordered narration segments.
    """
    # Check cache
    problem_id = _get_problem_id(image_path, problem_latex)
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cached = cache.get(problem_id, "solution_script")
        if cached and isinstance(cached, dict):
            return SolutionScript(**cached)

    agent = create_agent(
        name="ScriptWriter",
        instructions=get_script_writer_prompt(),
        output_type=SolutionScript,
        agent_type="script_writer",
    )

    # Build input
    user_text = ""
    if problem_latex:
        user_text += f"## Problem\n\n{problem_latex}\n\n"
    if solution_latex:
        user_text += f"## Solution\n\n{solution_latex}\n\n"
    if not user_text:
        user_text = "Write a narration script for the problem in the attached image."

    user_text += (
        "\nWrite a complete narration script for a solution video. "
        "Cover the problem statement, approach, each solution step, "
        "and the final result with a recap."
    )

    if image_path:
        message = create_image_message(image_path, user_text)
    else:
        message = user_text

    result = run_agent_sync(agent, message, show_spinner=show_spinner)

    # Save to cache
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cache.set(problem_id, "solution_script", result.model_dump())

    return result
