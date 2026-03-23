"""Idea Curator Agent.

Takes all ideas from the store, performs semantic deduplication,
text cleanup, topic re-assignment, and suggests missing ideas.
"""

from __future__ import annotations

from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.ideas.models import Idea
from vbagent.prompts.classification.idea_curator import get_idea_curator_prompt


class CuratedIdea(BaseModel):
    """A single curated idea from the curator agent."""
    text: str = ""
    formulas: list[str] = Field(default_factory=list)
    topic: str = ""
    subtopic: str = ""
    merged_from: list[int] = Field(default_factory=list)
    suggested: bool = False


class MergeLogEntry(BaseModel):
    """Explains a merge decision."""
    kept: str = ""
    merged: list[str] = Field(default_factory=list)
    reason: str = ""


class CurationResult(BaseModel):
    """Full output from the curator agent."""
    model_config = ConfigDict(extra="allow")

    curated_ideas: list[CuratedIdea] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    merge_log: list[MergeLogEntry] = Field(default_factory=list)


def create_idea_curator_agent(subject: Optional[str] = None):
    """Create the idea curator agent."""
    if subject is None:
        subject = get_config().subject

    prompt = get_idea_curator_prompt(subject)

    from agents import AgentOutputSchema

    return create_agent(
        name=f"IdeaCurator-{subject}",
        instructions=prompt,
        output_type=AgentOutputSchema(CurationResult, strict_json_schema=False),
        agent_type="idea",
    )


def curate_ideas(
    ideas: list[Idea],
    subject: Optional[str] = None,
) -> CurationResult:
    """Run the curator agent on a list of ideas.

    Args:
        ideas: All ideas from the store
        subject: Subject override

    Returns:
        CurationResult with deduplicated, cleaned ideas + merge log
    """
    if subject is None:
        subject = get_config().subject

    agent = create_idea_curator_agent(subject)

    # Format ideas for context
    ideas_block = ""
    for i, idea in enumerate(ideas):
        formulas_str = ", ".join(idea.formulas[:3]) if idea.formulas else "none"
        ideas_block += f"[{i}] {idea.text}"
        if idea.topic:
            ideas_block += f" (topic: {idea.topic})"
        if idea.formulas:
            ideas_block += f" — formulas: {formulas_str}"
        ideas_block += "\n"

    context = f"""Curate these {len(ideas)} {subject} ideas.

Deduplicate semantically, clean up text, fix topics, and suggest missing ideas.

**Ideas:**
{ideas_block}

Respond with ONLY the JSON object."""

    return run_agent_sync(agent, context)
