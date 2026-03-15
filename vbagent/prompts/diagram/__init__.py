"""Diagram generation prompts."""

from vbagent.prompts.diagram.tikz import SYSTEM_PROMPT as TIKZ_PROMPT
from vbagent.prompts.diagram.tikz_checker import SYSTEM_PROMPT as TIKZ_CHECKER_PROMPT

# Physics prompts
from vbagent.prompts.diagram.physics import (
    FBD_PROMPT,
    CIRCUIT_PROMPT,
    GRAPH_PROMPT,
    OPTICS_PROMPT,
)

# Chemistry prompts
from vbagent.prompts.diagram.chemistry import (
    ORGANIC_STRUCTURE_PROMPT,
    REACTION_MECHANISM_PROMPT,
    ORBITAL_PROMPT,
)

__all__ = [
    "TIKZ_PROMPT",
    "TIKZ_CHECKER_PROMPT",
    # Physics
    "FBD_PROMPT",
    "CIRCUIT_PROMPT",
    "GRAPH_PROMPT",
    "OPTICS_PROMPT",
    # Chemistry
    "ORGANIC_STRUCTURE_PROMPT",
    "REACTION_MECHANISM_PROMPT",
    "ORBITAL_PROMPT",
]
