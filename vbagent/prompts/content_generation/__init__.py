"""Content generation prompts."""

from vbagent.prompts.content_generation.idea import SYSTEM_PROMPT as IDEA_PROMPT
from vbagent.prompts.content_generation.alternate import SYSTEM_PROMPT as ALTERNATE_PROMPT
from vbagent.prompts.content_generation.converter import SYSTEM_PROMPT as CONVERTER_PROMPT

__all__ = [
    "IDEA_PROMPT",
    "ALTERNATE_PROMPT",
    "CONVERTER_PROMPT",
]
