"""Content generation prompts."""

from vbagent.prompts.content_generation.idea import SYSTEM_PROMPT as IDEA_PROMPT
from vbagent.prompts.content_generation.alternate import SYSTEM_PROMPT as ALTERNATE_PROMPT
from vbagent.prompts.content_generation.converter import SYSTEM_PROMPT as CONVERTER_PROMPT
from vbagent.prompts.content_generation.idea_combiner import get_idea_combiner_prompt
from vbagent.prompts.content_generation.idea_curator import get_idea_curator_prompt
from vbagent.prompts.content_generation.idea_generator import get_idea_generator_prompt
from vbagent.prompts.content_generation.problem_combiner import get_problem_combiner_prompt

__all__ = [
    "IDEA_PROMPT",
    "ALTERNATE_PROMPT",
    "CONVERTER_PROMPT",
    "get_idea_generator_prompt",
    "get_idea_curator_prompt",
    "get_idea_combiner_prompt",
    "get_problem_combiner_prompt",
]
