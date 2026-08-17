"""Compatibility aliases for the renamed question classifier.

Use :mod:`vbagent.agents.classification.question_classifier` in new code.
"""

from .question_classifier import (
    QuestionClassification,
    classify_question_image,
    create_question_classifier,
    to_diagram_analysis,
    to_primary_classification,
)

UnifiedClassificationResult = QuestionClassification
create_unified_classifier_agent = create_question_classifier
classify_and_analyze = classify_question_image
to_primary = to_primary_classification

__all__ = [
    "UnifiedClassificationResult",
    "create_unified_classifier_agent",
    "classify_and_analyze",
    "to_primary",
    "to_diagram_analysis",
]
