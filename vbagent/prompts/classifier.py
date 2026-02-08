"""Classifier agent prompts."""

from vbagent.prompts.subjects import get_subject_config, SUBJECTS
from vbagent.prompts.subjects.taxonomy import get_chapters, get_all_topics


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
    
    # Get chapters and topics from taxonomy
    chapters = get_chapters(subject)
    all_topics = get_all_topics(subject)
    
    # Format chapters list (first 10 as examples)
    chapters_str = ", ".join(f'"{c}"' for c in chapters[:10])
    if len(chapters) > 10:
        chapters_str += f", ... ({len(chapters)} total)"
    
    # Format topics list (first 15 as examples)
    topics_str = ", ".join(f'"{t}"' for t in all_topics[:15])
    if len(all_topics) > 15:
        topics_str += f", ... ({len(all_topics)} total)"
    
    diagram_types_str = ", ".join(config.diagram_types)
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided image of a {config.display_name.lower()} problem and extract structured metadata.

You MUST respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:

{{
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "difficulty": "easy" | "medium" | "hard",
    "chapter": "<chapter name from the list below>",
    "topic": "<topic name from the list below>",
    "subtopic": "<specific subtopic>",
    "has_diagram": true | false,
    "diagram_type": "<type if present: {diagram_types_str}, none>",
    "num_options": <number of options if MCQ, else null>,
    "estimated_marks": <integer>,
    "key_concepts": ["<concept1>", "<concept2>"],
    "requires_calculus": true | false,
    "confidence": <0.0 to 1.0>
}}

**IMPORTANT: You MUST choose chapter and topic from these predefined lists:**

**Available Chapters:** {chapters_str}

**Available Topics:** {topics_str}

**Rules for chapter and topic selection:**
1. Choose the MOST APPROPRIATE chapter from the list above
2. Choose the MOST APPROPRIATE topic from the list above
3. If unsure, choose the closest matching chapter/topic
4. The topic should be related to the chosen chapter
5. Use exact names from the lists (case-insensitive matching is acceptable)

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
