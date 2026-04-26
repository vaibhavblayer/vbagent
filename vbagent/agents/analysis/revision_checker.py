"""Agent for auditing and fixing revision sheets against the syllabus."""

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents import Agent

from pydantic import BaseModel, Field

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.prompts.analysis.revision_checker import get_revision_checker_prompt


# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------

class MissingTopic(BaseModel):
    """A syllabus topic missing from the revision sheet, with generated fix."""
    topic_name: str = Field(description="The syllabus topic that is missing")
    latex: str = Field(description="Complete itemize block to add for this topic")


class ExtraIdea(BaseModel):
    """An idea that is outside the syllabus and should be removed."""
    idea_title: str = Field(description="Title of the extra idea")
    under_topic: str = Field(description="Which subsection/topic it appears under")
    reason: str = Field(description="Brief reason why it's out of syllabus")


class ThinTopic(BaseModel):
    """A topic with too few ideas."""
    topic_name: str = Field(description="The syllabus topic")
    idea_count: int = Field(description="Number of ideas currently covering it")


class AuditReport(BaseModel):
    """Complete audit report."""
    missing: list[MissingTopic] = Field(default_factory=list)
    extra: list[ExtraIdea] = Field(default_factory=list)
    thin: list[ThinTopic] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def audit_revision_sheet(
    syllabus_topics: list[str],
    revision_topics: dict[str, list[str]],
    chapter_name: str,
    show_spinner: bool = True,
) -> AuditReport:
    """Audit a revision sheet against the syllabus.

    Args:
        syllabus_topics: Official syllabus topic list for this chapter.
        revision_topics: {topic_name: [idea_title, ...]} from the revision sheet.
        chapter_name: Chapter name.
        show_spinner: Show progress spinner.

    Returns:
        AuditReport with missing, extra, and thin findings.
    """
    agent_input = _build_input(syllabus_topics, revision_topics, chapter_name)

    agent = create_agent(
        name="RevisionSheetChecker",
        instructions=get_revision_checker_prompt(),
        output_type=AuditReport,
        agent_type="idea",
    )

    return run_agent_sync(agent, agent_input, show_spinner=show_spinner)


def extract_topics_from_tex(tex_content: str) -> dict[str, list[str]]:
    """Extract topic names and idea titles from a revision sheet .tex file.

    Returns:
        {topic_name: [idea_title, ...]}
    """
    result = {}
    current_topic = None

    for line in tex_content.split("\n"):
        line = line.strip()

        # Match \subsection*{...}
        sub_match = re.match(r"\\subsection\*\{(.+?)\}", line)
        if sub_match:
            current_topic = sub_match.group(1)
            result[current_topic] = []
            continue

        # Match \item followed by text (idea title)
        item_match = re.match(r"\\item\s+(.+?)$", line)
        if item_match and current_topic is not None:
            title = item_match.group(1).strip()
            # Skip if it looks like a formula line or empty
            if title and not title.startswith("\\begin") and not title.startswith("$"):
                result[current_topic].append(title)

    return result


def apply_fixes(
    tex_content: str,
    report: AuditReport,
) -> str:
    """Apply audit fixes to a .tex file: remove extras, add missing topics.

    Args:
        tex_content: Original .tex content.
        report: Audit report from the checker agent.

    Returns:
        Fixed .tex content.
    """
    fixed = tex_content

    # 1. Remove extra ideas (find \item <title> and remove until next \item or \end{itemize})
    for extra in report.extra:
        fixed = _remove_idea(fixed, extra.idea_title)

    # 2. Add missing topics before \end{multicols}
    if report.missing:
        insert_blocks = ""
        for missing in report.missing:
            insert_blocks += f"\\subsection*{{{missing.topic_name}}}\n\n"
            insert_blocks += missing.latex.strip() + "\n\n"

        fixed = fixed.replace(
            "\\end{multicols}",
            insert_blocks + "\\end{multicols}",
        )

    return fixed


def _remove_idea(tex: str, idea_title: str) -> str:
    """Remove an \\item block by its title from the tex content."""
    # Escape special regex chars in the title
    escaped = re.escape(idea_title)
    # Match from \item <title> through the align* block until next \item or \end{itemize}
    pattern = (
        r"\\item\s+" + escaped + r".*?"
        r"(?=\\item\s|\s*\\end\{itemize\})"
    )
    return re.sub(pattern, "", tex, count=1, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Input builder
# ---------------------------------------------------------------------------

def _build_input(
    syllabus_topics: list[str],
    revision_topics: dict[str, list[str]],
    chapter_name: str,
) -> str:
    text = f"# Chapter: {chapter_name}\n\n"

    text += "## Official Syllabus Topics\n"
    for i, topic in enumerate(syllabus_topics, 1):
        text += f"{i}. {topic}\n"

    text += "\n## Revision Sheet Content\n\n"
    for topic_name, ideas in revision_topics.items():
        text += f"### {topic_name}\n"
        if ideas:
            for idea in ideas:
                text += f"- {idea}\n"
        else:
            text += "- (no ideas)\n"
        text += "\n"

    return text
