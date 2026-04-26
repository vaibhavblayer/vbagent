"""Animation fixer agent — fixes Manim compilation errors."""

from __future__ import annotations

from vbagent.agents.animation.models import AnimationFix
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.animation.fixer import get_fixer_prompt


def fix_animation(
    code: str,
    error_output: str,
    show_spinner: bool = True,
) -> AnimationFix:
    """Fix a Manim script that failed to render.

    Args:
        code: The broken Python file content.
        error_output: stderr/stdout from the failed manim render.
        show_spinner: Show progress spinner.

    Returns:
        AnimationFix with the corrected code.
    """
    agent = create_agent(
        name="AnimationFixer",
        instructions=get_fixer_prompt(),
        output_type=AnimationFix,
        agent_type="tikz",
    )

    user_text = f"## Broken Code\n\n```python\n{code}\n```\n\n"
    user_text += f"## Error Output\n\n```\n{error_output}\n```\n\n"
    user_text += "Fix the code and return the complete corrected file."

    return run_agent_sync(agent, user_text, show_spinner=show_spinner, timeout=120)
