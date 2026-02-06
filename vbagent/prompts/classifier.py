"""Classifier agent prompts."""

from vbagent.prompts.subjects import get_subject_config, SUBJECTS


def get_classifier_prompt(subject: str = "physics") -> str:
    """Get classifier prompt for a subject.
    
    Args:
        subject: Subject name (physics, chemistry, etc.)
        
    Returns:
        System prompt for classification
    """
    if subject not in SUBJECTS:
        subject = "physics"
    
    config = get_subject_config(subject)
    topics_str = ", ".join(config.topics[:10])  # First 10 topics as examples
    diagram_types_str = ", ".join(config.diagram_types)
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided image of a {config.display_name.lower()} problem and extract structured metadata.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:

{{
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "difficulty": "easy" | "medium" | "hard",
    "topic": "<{config.display_name.lower()} topic e.g., {topics_str}>",
    "subtopic": "<specific subtopic>",
    "has_diagram": true | false,
    "diagram_type": "<type if present: {diagram_types_str}, none>",
    "num_options": <number of options if MCQ, else null>,
    "estimated_marks": <integer>,
    "key_concepts": ["<concept1>", "<concept2>"],
    "requires_calculus": true | false,
    "confidence": <0.0 to 1.0>
}}

Question type definitions:
- mcq_sc: Multiple choice with single correct answer
- mcq_mc: Multiple choice with multiple correct answers  
- subjective: Open-ended requiring detailed solution
- assertion_reason: Assertion and reason type questions
- passage: Comprehension/passage based questions
- match: Match the following type

Respond with ONLY the JSON object."""


def get_user_template(subject: str = "physics") -> str:
    """Get user template for classifier.
    
    Args:
        subject: Subject name
        
    Returns:
        User template string
    """
    return f"Classify this {subject} question image."


# Legacy exports for backward compatibility
SYSTEM_PROMPT = get_classifier_prompt("physics")
USER_TEMPLATE = "Classify this physics question image."
