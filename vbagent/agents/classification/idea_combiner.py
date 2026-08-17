"""Compatibility aliases for the relocated idea combiner."""

from vbagent.agents.content_generation.idea_combiner import (
    CombinedProblemOutput,
    combine_ideas,
    create_idea_combiner_agent,
)

__all__ = [
    "CombinedProblemOutput",
    "create_idea_combiner_agent",
    "combine_ideas",
]
