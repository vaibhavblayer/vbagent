"""Classifier agent for question image classification.

Stage 1: Structural classification only (routing metadata).
Semantic metadata (chapter, topic, difficulty) deferred to Stage 4 & 5.
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
from vbagent.models.classification import ClassificationResult, PrimaryClassification
from vbagent.models.structural import StructuralClassification  # New Stage 1
from vbagent.prompts.classification.classifier import get_classifier_prompt, get_user_template
from vbagent.prompts.classification.taxonomy import get_chapter_for_topic


def get_structural_classifier_prompt(subject: str = "physics") -> str:
    """Get Stage 1 structural classifier prompt (no chapter/topic/difficulty)."""
    from vbagent.prompts.subjects import get_subject_config
    
    config = get_subject_config(subject)
    
    return f"""You are an expert {config.display_name.lower()} question analyzer. Analyze the image and extract STRUCTURAL metadata only.

You MUST respond with ONLY a valid JSON object:

{{
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "diagram_type": "free_body" | "circuit" | "graph" | "optics" | "geometry" | "none",
    "num_options": <number if MCQ, else null>,
    "num_subquestions": <number of sub-questions, default 1>,
    "requires_calculus": true | false,
    "key_concepts": ["<hint1>", "<hint2>"],
    "confidence": <0.0 to 1.0>
}}

**Question Types:**
- mcq_sc: Single correct MCQ
- mcq_mc: Multiple correct MCQ
- subjective: Open-ended/numerical answer
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing context (look for question numbers like 42, 43, 44)
- match: Match the following

**Diagram Types:**
- free_body: Forces, vectors on objects
- circuit: Electrical circuits
- graph: Plots, charts, coordinate graphs
- optics: Lenses, mirrors, ray diagrams
- geometry: Geometric shapes, constructions
- none: No diagram

**Key Concepts:**
- Freeform hints about the topic (e.g., "friction", "projectile motion")
- Used for context retrieval, not strict classification

**IMPORTANT:**
- Do NOT classify chapter, topic, or difficulty (that happens later)
- Focus only on structural features visible in the image
- For passage type: Look for multiple numbered questions sharing context

Respond with ONLY the JSON object."""


def create_structural_classifier_agent(subject: Optional[str] = None) -> "Agent":
    """Create Stage 1 structural classifier agent.
    
    Args:
        subject: Subject override (uses config if not provided)
        
    Returns:
        Configured Agent instance for structural classification
    """
    if subject is None:
        subject = get_config().subject
    
    prompt = get_structural_classifier_prompt(subject)
    
    return create_agent(
        name=f"StructuralClassifier-{subject}",
        instructions=prompt,
        output_type=StructuralClassification,
        agent_type="classifier",
    )


def create_classifier_agent(subject: Optional[str] = None) -> "Agent":
    """Create legacy v1 classifier agent (backward compatibility).
    
    For new code, use classify_structural() instead.
    """
    if subject is None:
        subject = get_config().subject
    
    prompt = get_classifier_prompt(subject)
    
    return create_agent(
        name=f"Classifier-{subject}",
        instructions=prompt,
        output_type=PrimaryClassification,
        agent_type="classifier",
    )


# Legacy: Create default classifier agent for backward compatibility
classifier_agent = create_classifier_agent("physics")


def classify_structural(
    image_path: str,
    subject: Optional[str] = None
) -> StructuralClassification:
    """Stage 1: Structural classification (routing metadata only).
    
    Args:
        image_path: Path to the image file to classify
        subject: Subject override (uses config if not provided)
        
    Returns:
        StructuralClassification with routing metadata
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    if subject is None:
        subject = get_config().subject
    
    config = get_config()
    
    # Try with nano first
    agent = create_structural_classifier_agent(subject)
    message = create_image_message(image_path, "Analyze this question image.")
    result = run_agent_sync(agent, message, timeout=60)
    
    # Fallback to mini if confidence is low
    if result.confidence < config.classifier_confidence_threshold:
        # Retry with gpt-5-mini
        original_model = config.classifier.model
        config.classifier.model = "gpt-5-mini"
        agent = create_structural_classifier_agent(subject)
        result = run_agent_sync(agent, message, timeout=60)
        config.classifier.model = original_model  # Restore
    
    return result


def classify(image_path: str, subject: Optional[str] = None) -> PrimaryClassification:
    """Analyze a question image and return structured metadata (LEGACY v1).
    
    For new code, use classify_structural() for Stage 1 classification.
    
    Args:
        image_path: Path to the image file to classify
        subject: Subject override (uses config if not provided)
        
    Returns:
        PrimaryClassification with extracted metadata
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    if subject is None:
        subject = get_config().subject
    
    agent = create_classifier_agent(subject)
    user_template = get_user_template(subject)
    message = create_image_message(image_path, user_template)
    result = run_agent_sync(agent, message, timeout=60)
    
    return result
