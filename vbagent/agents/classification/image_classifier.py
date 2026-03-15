"""Agent 1: Enhanced Image Classifier.

Classifies question images without difficulty assessment.
Difficulty is assessed later by Agent 3 after LaTeX extraction.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import PrimaryClassification
from vbagent.prompts.subjects import get_subject_config
from vbagent.prompts.classification.question_types import get_question_type_guidance
from vbagent.agents.classification.subject_detector import (
    detect_subject_from_image,
    detect_subject_from_latex,
)


def get_image_classifier_prompt(subject: str = "physics") -> str:
    """Get simplified classifier prompt (3 fields only)."""
    config = get_subject_config(subject)
    question_type_guidance = get_question_type_guidance()
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided image and extract structured metadata.

You MUST respond with ONLY a valid JSON object with these fields:

{{
    "subject": "physics" | "chemistry" | "mathematics" | "biology",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "confidence": <0.0 to 1.0>,
    "classified_from": "image"
}}

Question types:
- mcq_sc: Single correct MCQ
- mcq_mc: Multiple correct MCQ
- subjective: Open-ended/numerical
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing context/passage
- match: Match the following

Detailed detection cues:
{question_type_guidance}

Rules:
1. For passage type: Look for multiple questions (42, 43, 44) sharing same context
2. has_diagram: true if ANY visual element (diagram, graph, chart) is present
3. classified_from: always "image"

Respond with ONLY the JSON object."""


def _resolve_subject_for_image(image_path: str, subject: Optional[str]) -> str:
    if subject:
        return subject
    try:
        return detect_subject_from_image(image_path)
    except (ValueError, TimeoutError):
        return get_config().subject


def _resolve_subject_for_latex(latex_content: str, subject: Optional[str]) -> str:
    if subject:
        return subject
    try:
        return detect_subject_from_latex(latex_content)
    except (ValueError, TimeoutError):
        return get_config().subject


def create_image_classifier_agent(subject: Optional[str] = None):
    """Create enhanced image classifier agent."""
    if subject is None:
        subject = get_config().subject
    
    prompt = get_image_classifier_prompt(subject)
    
    return create_agent(
        name=f"ImageClassifier-{subject}",
        instructions=prompt,
        output_type=PrimaryClassification,
        agent_type="classifier",
    )


def classify_from_image(image_path: str, subject: Optional[str] = None, show_spinner: bool = True) -> PrimaryClassification:
    """Classify question from image (Agent 1).
    
    Args:
        image_path: Path to question image
        subject: Subject override
        show_spinner: Whether to show animated spinner
        
    Returns:
        PrimaryClassification without difficulty
    """
    subject = _resolve_subject_for_image(image_path, subject)
    
    agent = create_image_classifier_agent(subject)
    message = create_image_message(image_path, f"Classify this {subject} question.")
    
    result = run_agent_sync(agent, message, show_spinner=show_spinner, timeout=60)
    return result
