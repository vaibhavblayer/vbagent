"""Compatibility aliases for the relocated idea curator."""

from vbagent.agents.content_generation.idea_curator import (
    CuratedIdea,
    CurationResult,
    MergeLogEntry,
    create_idea_curator_agent,
    curate_ideas,
)

__all__ = [
    "CuratedIdea",
    "CurationResult",
    "MergeLogEntry",
    "create_idea_curator_agent",
    "curate_ideas",
]
