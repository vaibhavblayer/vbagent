"""Animation planner agent — breaks a topic into a sequence of scenes."""

from __future__ import annotations

from vbagent.agents.animation.models import AnimationPlan
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.animation.planner import get_planner_prompt


def plan_animation(
    topic: str,
    show_spinner: bool = True,
) -> AnimationPlan:
    """Plan a multi-scene animation for a topic.

    Args:
        topic: The concept/topic to explain (e.g. "Polarisation of light")
        show_spinner: Show progress spinner.

    Returns:
        AnimationPlan with ordered list of scenes.
    """
    agent = create_agent(
        name="AnimationPlanner",
        instructions=get_planner_prompt(),
        output_type=AnimationPlan,
        agent_type="animation_assessor",  # lightweight, medium reasoning
    )

    user_text = f"Plan a multi-scene animation explaining: {topic}"

    return run_agent_sync(agent, user_text, show_spinner=show_spinner)
