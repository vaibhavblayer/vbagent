"""Backward-compatible public facade for question-image classification.

New code should import from
``vbagent.agents.classification.question_classifier``.
"""

from typing import TYPE_CHECKING, Optional

from vbagent.agents.classification.question_classifier import (
    classify_primary_image,
    create_question_classifier,
)
from vbagent.config import get_config
from vbagent.models.classification import PrimaryClassification

if TYPE_CHECKING:
    from agents import Agent

classifier_agent: "Agent"


def create_classifier_agent(subject: Optional[str] = None) -> "Agent":
    """Compatibility wrapper for :func:`create_question_classifier`."""
    return create_question_classifier(subject or get_config().subject)


def classify(
    image_path: str,
    subject: Optional[str] = None,
) -> PrimaryClassification:
    """Classify an image using the canonical question classifier."""
    return classify_primary_image(image_path, subject=subject)


def __getattr__(name: str):
    """Create the legacy default agent only when explicitly requested."""
    if name == "classifier_agent":
        agent = create_classifier_agent("physics")
        globals()[name] = agent
        return agent
    raise AttributeError(name)


__all__ = ["create_classifier_agent", "classifier_agent", "classify"]
