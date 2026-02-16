"""Diagram generation prompts."""

from vbagent.prompts.diagram.tikz import SYSTEM_PROMPT as TIKZ_PROMPT
from vbagent.prompts.diagram.fbd import SYSTEM_PROMPT as FBD_PROMPT
from vbagent.prompts.diagram.tikz_checker import SYSTEM_PROMPT as TIKZ_CHECKER_PROMPT

__all__ = [
    "TIKZ_PROMPT",
    "FBD_PROMPT",
    "TIKZ_CHECKER_PROMPT",
]
