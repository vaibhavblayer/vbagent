"""Video fixer agent — fixes broken Manim code for solution videos."""

from __future__ import annotations

from vbagent.agents.solution_video.models import VideoFix
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.solution_video.video_fixer import get_video_fixer_prompt


def fix_video_code(
    code: str,
    error_output: str,
    show_spinner: bool = True,
) -> VideoFix:
    """Fix a solution video Manim script that failed to render.

    Args:
        code: The broken Python file content.
        error_output: stderr/stdout from the failed manim render.
        show_spinner: Show progress spinner.

    Returns:
        VideoFix with the corrected code.
    """
    agent = create_agent(
        name="SolutionVideoFixer",
        instructions=get_video_fixer_prompt(),
        output_type=VideoFix,
        agent_type="video_fixer",
    )

    user_text = f"## Broken Code\n\n```python\n{code}\n```\n\n"
    user_text += f"## Error Output\n\n```\n{error_output}\n```\n\n"
    user_text += "Fix the code and return the complete corrected file."

    return run_agent_sync(agent, user_text, show_spinner=show_spinner, timeout=120)
