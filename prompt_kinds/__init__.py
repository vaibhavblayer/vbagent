"""Generic, model-agnostic prompt type wrappers.

Each module exposes a single name: `PROMPT`, imported from
`vbimagetotext.prompts` to avoid duplicating or modifying content.
"""

from . import (
    assertion_reason_type,
    mcq_mc_type,
    mcq_sc_type,
    passage_type,
    subjective_type,
    match_type,
)

# Variants available, not used by default classifier
from . import (
    variant_numerical,
    variant_conceptual,
    variant_context,
    variant_numerical_context,
    variant_conceptual_calculus,
)

PROMPT_BY_TYPE = {
    "assertion_reason": assertion_reason_type.PROMPT,
    "mcq_mc": mcq_mc_type.PROMPT,
    "mcq_sc": mcq_sc_type.PROMPT,
    "passage": passage_type.PROMPT,
    "subjective": subjective_type.PROMPT,
    "match": match_type.PROMPT,
}


def get_prompt_for_type(name: str) -> str:
    try:
        return PROMPT_BY_TYPE[name]
    except KeyError:
        raise ValueError(f"Unknown prompt type: {name}")


__all__ = [
    # Accessors
    "get_prompt_for_type",
    # Core types (modules)
    "assertion_reason_type",
    "mcq_mc_type",
    "mcq_sc_type",
    "passage_type",
    "subjective_type",
    "match_type",
    # Variants (modules)
    "variant_numerical",
    "variant_conceptual",
    "variant_context",
    "variant_numerical_context",
    "variant_conceptual_calculus",
]
