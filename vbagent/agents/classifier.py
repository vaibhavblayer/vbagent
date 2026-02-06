"""Classifier agent for question image classification.

Uses openai-agents SDK to analyze question images and extract
structured metadata including question type, difficulty, topic, etc.
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
from vbagent.models.classification import ClassificationResult
from vbagent.prompts.classifier import get_classifier_prompt, get_user_template


def create_classifier_agent(subject: Optional[str] = None) -> "Agent":
    """Create a classifier agent for a subject.
    
    Args:
        subject: Subject override (uses config if not provided)
        
    Returns:
        Configured Agent instance for classification
    """
    if subject is None:
        subject = get_config().subject
    
    prompt = get_classifier_prompt(subject)
    
    return create_agent(
        name=f"Classifier-{subject}",
        instructions=prompt,
        output_type=ClassificationResult,
        agent_type="classifier",
    )


# Legacy: Create default classifier agent for backward compatibility
classifier_agent = create_classifier_agent("physics")


def classify(image_path: str, subject: Optional[str] = None) -> ClassificationResult:
    """Analyze a question image and return structured metadata.
    
    Args:
        image_path: Path to the image file to classify
        subject: Subject override (uses config if not provided)
        
    Returns:
        ClassificationResult with extracted metadata
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    if subject is None:
        subject = get_config().subject
    
    agent = create_classifier_agent(subject)
    user_template = get_user_template(subject)
    message = create_image_message(image_path, user_template)
    result = run_agent_sync(agent, message)
    return result
