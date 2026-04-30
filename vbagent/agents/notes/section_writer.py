"""Section writer agent — generates LaTeX content for one section of concept notes."""

from __future__ import annotations

from vbagent.agents.notes.models import SectionPlan, SectionContent
from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.notes.section_writer import get_section_writer_prompt


def _format_section_plan(plan: SectionPlan, section_index: int, total_sections: int) -> str:
    """Format a section plan into a prompt for the writer."""
    lines = [
        f"## Section {section_index + 1} of {total_sections}: {plan.title}\n",
    ]

    for i, sub in enumerate(plan.subsections):
        lines.append(f"### Subsection {i + 1}: {sub.title}")
        lines.append(f"**Content type**: {sub.content_type}")
        lines.append(f"**Description**: {sub.description}")

        if sub.key_equations:
            lines.append("**Key equations**:")
            for eq in sub.key_equations:
                lines.append(f"  - `{eq}`")

        if sub.diagrams:
            lines.append("**Diagrams**:")
            for d in sub.diagrams:
                lines.append(
                    f"  - `{d.diagram_id}` ({d.diagram_type}): {d.description}"
                )
                lines.append(f"    Caption: {d.caption}")

        lines.append("")

    return "\n".join(lines)


def write_section(
    section_plan: SectionPlan,
    section_index: int,
    total_sections: int,
    topic: str = "",
    subject: str = "physics",
    show_spinner: bool = True,
) -> SectionContent:
    """Write LaTeX content for one section.

    Args:
        section_plan: The plan for this section.
        section_index: 0-based index.
        total_sections: Total number of sections.
        topic: Overall document topic (for context).
        subject: Subject (physics, chemistry, mathematics).
        show_spinner: Show progress spinner.

    Returns:
        SectionContent with the LaTeX.
    """
    agent = create_agent(
        name=f"SectionWriter[{section_index + 1}/{total_sections}]",
        instructions=get_section_writer_prompt(),
        output_type=SectionContent,
        agent_type="notes_writer",
    )

    user_text = f"**Document topic**: {topic}\n"
    user_text += f"**Subject**: {subject}\n\n"
    user_text += _format_section_plan(section_plan,
                                      section_index, total_sections)
    user_text += "\nWrite the complete LaTeX for this section. Use \\input{diagrams/ID.tex} for diagrams."

    return run_agent_sync(agent, user_text, show_spinner=show_spinner, timeout=600)
