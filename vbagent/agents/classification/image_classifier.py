"""Agent 1: Enhanced Image Classifier.

Classifies question images without difficulty assessment.
Difficulty is assessed later by Agent 3 after LaTeX extraction.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification_v2 import PrimaryClassification
from vbagent.prompts.subjects import get_subject_config
from vbagent.prompts.subjects.taxonomy import get_chapters, get_all_topics


def get_image_classifier_prompt(subject: str = "physics") -> str:
    """Get enhanced classifier prompt without difficulty."""
    config = get_subject_config(subject)
    chapters = get_chapters(subject)
    all_topics = get_all_topics(subject)
    
    chapters_str = ", ".join(f'"{c}"' for c in chapters[:10])
    if len(chapters) > 10:
        chapters_str += f", ... ({len(chapters)} total)"
    
    topics_str = ", ".join(f'"{t}"' for t in all_topics[:15])
    if len(all_topics) > 15:
        topics_str += f", ... ({len(all_topics)} total)"
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided image and extract structured metadata.

You MUST respond with ONLY a valid JSON object with these fields:

{{
    "subject": "{subject}",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "chapter": "<from list below>",
    "topic": "<from list below>",
    "subtopic": "<specific subtopic>",
    "has_diagram": true | false,
    "num_options": <number if MCQ, else null>,
    "key_concepts": ["<concept1>", "<concept2>"],
    "requires_calculus": true | false,
    "estimated_marks": <typical marks: 1-10>,
    "time_estimate_minutes": <typical solve time: 1-30>,
    "confidence": <0.0 to 1.0>,
    "classified_from": "image"
}}

**Available Chapters:** {chapters_str}
**Available Topics:** {topics_str}

Question types:
- mcq_sc: Single correct MCQ
- mcq_mc: Multiple correct MCQ
- subjective: Open-ended/numerical
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing context/passage
- match: Match the following

Rules:
1. Choose chapter and topic from lists above
2. For passage type: Look for multiple questions (42, 43, 44) sharing same context
3. estimated_marks: Typical marks for this question type (1-10)
4. time_estimate_minutes: Typical time to solve (1-30 minutes)
5. Do NOT assess difficulty - that happens later after LaTeX extraction

Respond with ONLY the JSON object."""


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


def classify_from_image(image_path: str, subject: Optional[str] = None) -> PrimaryClassification:
    """Classify question from image (Agent 1).
    
    Args:
        image_path: Path to question image
        subject: Subject override
        
    Returns:
        PrimaryClassification without difficulty
    """
    if subject is None:
        subject = get_config().subject
    
    agent = create_image_classifier_agent(subject)
    message = create_image_message(image_path, f"Classify this {subject} question.")
    
    result = run_agent_sync(agent, message)
    return result
