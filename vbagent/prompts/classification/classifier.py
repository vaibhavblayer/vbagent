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
    
    diagram_types_str = ", ".join(config.diagram_types)
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided image of a {config.display_name.lower()} problem and extract structured metadata.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:

{{
    "subject": "physics" | "chemistry" | "mathematics" | "biology",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "confidence": <0.0 to 1.0>
}}

Question type definitions:
- mcq_sc: Multiple choice with single correct answer (standalone question)
- mcq_mc: Multiple choice with multiple correct answers (standalone question)
- subjective: Open-ended requiring detailed solution
- assertion_reason: Assertion and reason type questions
- passage: Comprehension/passage based questions - MULTIPLE questions based on a SHARED passage, graph, or scenario. Look for:
  * A passage/paragraph/graph/scenario at the top
  * Multiple numbered questions (e.g., 42, 43, 44) referring to the same passage
  * Headers like "Comprehensive Passage", "Passage", "Comprehension", or question ranges like [42-45]
  * If you see 2+ questions sharing the same context/diagram, classify as "passage"
- match: Match the following type (two columns to be matched)

CRITICAL: If the image contains MULTIPLE questions (e.g., items 42, 43, 44) all referring to the SAME passage/graph/scenario, classify as "passage", NOT mcq_sc.

**Subject Detection:**
- If the image clearly shows a subject different from "{config.display_name}", update the "subject" field accordingly
- Default to "{config.display_name.lower()}" if unclear

**Diagram Detection:**
- Look for diagrams, graphs, charts, or visual representations
- Set "has_diagram" to true if ANY visual element is present
- Set to false for pure text/questions without visuals

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
