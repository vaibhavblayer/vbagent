"""Classifier agent for question image classification.

Used by CLI commands (scan, classify, batch, convert) for single-image
classification. The unified pipeline uses classify_and_analyze() instead.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agents import Agent

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.config import get_config
from vbagent.models.classification import PrimaryClassification
from vbagent.prompts.classification.classifier import get_classifier_prompt, get_user_template


def create_classifier_agent(subject: Optional[str] = None) -> "Agent":
    """Create classifier agent for image classification."""
    if subject is None:
        subject = get_config().subject

    prompt = get_classifier_prompt(subject)

    return create_agent(
        name=f"Classifier-{subject}",
        instructions=prompt,
        output_type=PrimaryClassification,
        agent_type="classifier",
    )


# Default classifier agent (physics)
classifier_agent = create_classifier_agent("physics")


def classify(image_path: str, subject: Optional[str] = None) -> PrimaryClassification:
    """Classify a question image and return structured metadata.

    Args:
        image_path: Path to the image file to classify
        subject: Subject override (uses config if not provided)

    Returns:
        PrimaryClassification with extracted metadata
    """
    if subject is None:
        subject = get_config().subject

    agent = create_classifier_agent(subject)
    user_template = get_user_template(subject)
    message = create_image_message(image_path, user_template)
    return run_agent_sync(agent, message, timeout=60)
