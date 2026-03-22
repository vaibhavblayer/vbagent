"""Diagram generation prompts."""

from vbagent.prompts.diagram.tikz_checker import SYSTEM_PROMPT as TIKZ_CHECKER_PROMPT

# Physics prompts
from vbagent.prompts.diagram.physics import (
    FBD_PROMPT,
    CIRCUIT_PROMPT,
    GRAPH_PROMPT,
    OPTICS_PROMPT,
    GENERIC_TIKZ_PROMPT,
)

# Chemistry prompts
from vbagent.prompts.diagram.chemistry import (
    ORGANIC_STRUCTURE_PROMPT,
    REACTION_MECHANISM_PROMPT,
    ORBITAL_PROMPT,
    LEWIS_STRUCTURE_PROMPT,
    CHEMICAL_EQUATION_PROMPT,
    ENERGY_DIAGRAM_PROMPT,
)

# Mathematics prompts
from vbagent.prompts.diagram.mathematics import (
    FUNCTION_GRAPH_PROMPT,
    COORDINATE_GEOMETRY_PROMPT,
    GEOMETRIC_FIGURE_PROMPT,
    NUMBER_LINE_PROMPT,
    VENN_DIAGRAM_PROMPT,
)

__all__ = [
    "TIKZ_CHECKER_PROMPT",
    # Physics
    "FBD_PROMPT",
    "CIRCUIT_PROMPT",
    "GRAPH_PROMPT",
    "OPTICS_PROMPT",
    "GENERIC_TIKZ_PROMPT",
    # Chemistry
    "ORGANIC_STRUCTURE_PROMPT",
    "REACTION_MECHANISM_PROMPT",
    "ORBITAL_PROMPT",
    "LEWIS_STRUCTURE_PROMPT",
    "CHEMICAL_EQUATION_PROMPT",
    "ENERGY_DIAGRAM_PROMPT",
    # Mathematics
    "FUNCTION_GRAPH_PROMPT",
    "COORDINATE_GEOMETRY_PROMPT",
    "GEOMETRIC_FIGURE_PROMPT",
    "NUMBER_LINE_PROMPT",
    "VENN_DIAGRAM_PROMPT",
]
