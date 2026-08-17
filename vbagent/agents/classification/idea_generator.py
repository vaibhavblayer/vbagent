"""Compatibility aliases for the relocated idea generator."""

from vbagent.agents.content_generation.idea_generator import (
    create_idea_generator_agent,
    generate_from_idea,
)

__all__ = ["create_idea_generator_agent", "generate_from_idea"]
