"""Compatibility aliases for the relocated problem combiner."""

from vbagent.agents.content_generation.problem_combiner import (
    combine_problems,
    create_problem_combiner_agent,
)

__all__ = ["create_problem_combiner_agent", "combine_problems"]
