"""Compatibility alias for the renamed question-classifier prompt."""

from .question_classifier import get_question_classifier_prompt

get_unified_classifier_prompt = get_question_classifier_prompt

__all__ = ["get_unified_classifier_prompt"]
