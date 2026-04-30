"""Notes planner agent — creates a structured document plan for concept notes."""

from __future__ import annotations

from vbagent.agents.notes.models import DocumentPlan
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.notes.planner import get_planner_prompt


def plan_notes(
    topic: str,
    syllabus: str = "",
    subject: str = "physics",
    show_spinner: bool = True,
) -> DocumentPlan:
    """Plan a concept notes document.

    Args:
        topic: The topic to cover (e.g. "Wave Optics: Single Slit, Double Slit, Slab").
        syllabus: Optional syllabus text for scope/depth guidance.
        subject: Subject (physics, chemistry, mathematics).
        show_spinner: Show progress spinner.

    Returns:
        DocumentPlan with sections, subsections, and diagram specs.
    """
    agent = create_agent(
        name="NotesPlanner",
        instructions=get_planner_prompt(),
        output_type=DocumentPlan,
        agent_type="notes_planner",
    )

    user_text = f"## Topic\n\n{topic}\n\n"
    user_text += f"**Subject**: {subject}\n\n"

    if syllabus:
        user_text += f"## Syllabus Context\n\n{syllabus}\n\n"

    user_text += (
        "Plan a comprehensive concept notes document for this topic. "
        "Include diagrams where they genuinely help understanding."
    )

    return run_agent_sync(agent, user_text, show_spinner=show_spinner, timeout=600)
