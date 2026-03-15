"""Variant prompts for physics problem generation.

Contains prompts for different types of problem variants:
- numerical: Modify only numerical values
- context: Modify only the scenario/context
- conceptual: Modify the core physics concept
- conceptual_calculus: Add calculus-based modifications
- multi_context: Combine multiple problems
"""

from vbagent.prompts.variants.numerical import SYSTEM_PROMPT as NUMERICAL_PROMPT
from vbagent.prompts.variants.context import SYSTEM_PROMPT as CONTEXT_PROMPT
from vbagent.prompts.variants.conceptual import SYSTEM_PROMPT as CONCEPTUAL_PROMPT
from vbagent.prompts.variants.conceptual_calculus import SYSTEM_PROMPT as CALCULUS_PROMPT
from vbagent.prompts.variants.multi_context import SYSTEM_PROMPT as MULTI_CONTEXT_PROMPT
from vbagent.prompts.variants.cross_topic import (
    ANALYZER_SYSTEM_PROMPT as CROSS_TOPIC_ANALYZER_PROMPT,
    GENERATOR_SYSTEM_PROMPT as CROSS_TOPIC_GENERATOR_PROMPT,
)

__all__ = [
    "NUMERICAL_PROMPT",
    "CONTEXT_PROMPT",
    "CONCEPTUAL_PROMPT",
    "CALCULUS_PROMPT",
    "MULTI_CONTEXT_PROMPT",
    "CROSS_TOPIC_ANALYZER_PROMPT",
    "CROSS_TOPIC_GENERATOR_PROMPT",
]
