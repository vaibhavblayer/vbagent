"""Classification prompts."""

from vbagent.prompts.classification.classifier import get_classifier_prompt
from vbagent.prompts.classification.diagram_classifier import (
    get_diagram_classifier_prompt,
)
from vbagent.prompts.classification.question_classifier import (
    get_question_classifier_prompt,
)

__all__ = [
    "get_classifier_prompt",
    "get_question_classifier_prompt",
    "get_diagram_classifier_prompt",
]
