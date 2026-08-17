"""Compatibility alias for the renamed diagram-classifier prompt."""

from .diagram_classifier import get_diagram_classifier_prompt

get_diagram_analyzer_prompt = get_diagram_classifier_prompt

__all__ = ["get_diagram_analyzer_prompt"]
