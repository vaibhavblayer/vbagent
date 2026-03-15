"""Variant generation agents.

This module contains agents responsible for generating problem variants:
- Variant: Generate single variants
- Multi-context Variant: Generate variants with multiple contexts
"""

from .variant import (
    generate_variant,
    create_variant_agent,
    get_variant_prompt,
    generate_numerical_variant,
    generate_context_variant,
    generate_conceptual_variant,
    generate_calculus_variant,
    VALID_VARIANT_TYPES,
    STANDARD_VARIANT_TYPES,
)
from .multi_context_variant import generate_multi_context_variant
from .cross_topic import analyze_cross_topic, generate_cross_topic_variant

__all__ = [
    # Variant
    "generate_variant",
    "create_variant_agent",
    "get_variant_prompt",
    "generate_numerical_variant",
    "generate_context_variant",
    "generate_conceptual_variant",
    "generate_calculus_variant",
    "VALID_VARIANT_TYPES",
    "STANDARD_VARIANT_TYPES",
    # Multi-context
    "generate_multi_context_variant",
    # Cross-topic
    "analyze_cross_topic",
    "generate_cross_topic_variant",
]
