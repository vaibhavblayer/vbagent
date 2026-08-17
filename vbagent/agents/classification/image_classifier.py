"""Compatibility facade for the former image-only classifier.

The canonical image path is :mod:`.question_classifier`.
"""

from typing import Optional

from vbagent.agents.classification.question_classifier import (
    classify_primary_image,
    create_question_classifier,
)
from vbagent.models.classification import PrimaryClassification
from vbagent.prompts.classification.question_classifier import (
    get_question_classifier_prompt,
)


get_image_classifier_prompt = get_question_classifier_prompt
create_image_classifier_agent = create_question_classifier


def classify_from_image(
    image_path: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> PrimaryClassification:
    """Classify an image and return the legacy primary result shape."""
    return classify_primary_image(
        image_path,
        subject=subject,
        show_spinner=show_spinner,
    )


__all__ = [
    "get_image_classifier_prompt",
    "create_image_classifier_agent",
    "classify_from_image",
]
