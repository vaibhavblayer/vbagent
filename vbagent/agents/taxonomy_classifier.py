"""Stage 4: Taxonomy Classifier Agent.

Classifies problems into curriculum taxonomy (chapter/topic/subtopic)
after LaTeX extraction. Uses structured outputs for guaranteed compliance.
"""

from typing import Optional
import json

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.metadata import TaxonomyClassification
from vbagent.agents.classification.schema_builder import (
    create_taxonomy_schema,
    get_taxonomy_json_schema,
)
from vbagent.prompts.subjects import get_subject_config
from vbagent.prompts.subjects.taxonomy import get_chapters, get_all_topics


def get_taxonomy_classifier_prompt(subject: str = "physics") -> str:
    """Get taxonomy classifier prompt.
    
    Args:
        subject: Subject name
        
    Returns:
        System prompt for taxonomy classification
    """
    config = get_subject_config(subject)
    chapters = get_chapters(subject)
    all_topics = get_all_topics(subject)
    
    # Show first few as examples
    chapters_str = ", ".join(f'"{c}"' for c in chapters[:8])
    if len(chapters) > 8:
        chapters_str += f", ... ({len(chapters)} total)"
    
    topics_str = ", ".join(f'"{t}"' for t in all_topics[:12])
    if len(all_topics) > 12:
        topics_str += f", ... ({len(all_topics)} total)"
    
    return f"""You are an expert {config.display_name.lower()} curriculum specialist. Classify the given problem into the curriculum taxonomy.

You will receive:
- LaTeX problem statement
- LaTeX solution (if available)
- TikZ code (if available)
- Hints from initial classification (question_type, key_concepts)

Your task: Classify into chapter, topic, and subtopic from the predefined curriculum.

**Available Chapters:** {chapters_str}

**Available Topics:** {topics_str}

**Instructions:**
1. Analyze the problem content, solution approach, and concepts used
2. Choose the MOST APPROPRIATE chapter from the list above
3. Choose the MOST APPROPRIATE topic from the list above
4. Specify a precise subtopic (specific aspect within the topic)
5. List key concepts demonstrated in the problem
6. List prerequisite concepts students need to know
7. Identify related topics from the curriculum
8. Assign Bloom's taxonomy cognitive level (remember, understand, apply, analyze, evaluate, create)
9. Identify relevant exams (JEE Main, JEE Advanced, NEET, CBSE, etc.)

**Guidelines:**
- Use exact chapter/topic names from the lists (case-insensitive matching)
- For multi-concept problems, choose the PRIMARY chapter/topic
- Subtopic should be specific (e.g., "static vs kinetic friction", not just "friction")
- Key concepts should be specific physics principles used
- Prerequisites should be foundational concepts needed
- Cognitive level: Most problems are "apply" or "analyze"

Respond with a JSON object matching the schema."""
    
    
def create_taxonomy_classifier_agent(subject: Optional[str] = None):
    """Create taxonomy classifier agent with structured output.
    
    Args:
        subject: Subject name (defaults to config subject)
        
    Returns:
        Agent instance configured for taxonomy classification
    """
    if subject is None:
        subject = get_config().subject
    
    prompt = get_taxonomy_classifier_prompt(subject)
    config = get_config()
    
    # Get JSON schema for structured output
    json_schema = get_taxonomy_json_schema(subject)
    
    agent = create_agent(
        name=f"TaxonomyClassifier-{subject}",
        instructions=prompt,
        agent_type="taxonomy_classifier",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "taxonomy_classification",
                "schema": json_schema,
                "strict": True,
            }
        }
    )
    
    return agent


def classify_taxonomy(
    latex_problem: str,
    latex_solution: Optional[str] = None,
    tikz_code: Optional[str] = None,
    question_type: Optional[str] = None,
    key_concepts: Optional[list[str]] = None,
    requires_calculus: bool = False,
    subject: Optional[str] = None,
) -> TaxonomyClassification:
    """Classify problem into curriculum taxonomy.
    
    Args:
        latex_problem: LaTeX problem statement
        latex_solution: LaTeX solution (optional)
        tikz_code: TikZ diagram code (optional)
        question_type: Question type from Stage 1 (optional hint)
        key_concepts: Key concepts from Stage 1 (optional hints)
        requires_calculus: Whether problem requires calculus
        subject: Subject name (defaults to config)
        
    Returns:
        TaxonomyClassification with chapter, topic, subtopic, etc.
    """
    if subject is None:
        subject = get_config().subject
    
    # Build input message
    parts = [f"**Problem:**\n{latex_problem}"]
    
    if latex_solution:
        parts.append(f"\n**Solution:**\n{latex_solution}")
    
    if tikz_code:
        parts.append(f"\n**Diagram (TikZ):**\n{tikz_code}")
    
    # Add hints from Stage 1
    hints = []
    if question_type:
        hints.append(f"Question type: {question_type}")
    if key_concepts:
        hints.append(f"Initial concepts: {', '.join(key_concepts)}")
    if requires_calculus:
        hints.append("Requires calculus")
    
    if hints:
        parts.append(f"\n**Hints:**\n" + "\n".join(f"- {h}" for h in hints))
    
    message = "\n".join(parts)
    
    # Create agent and run
    agent = create_taxonomy_classifier_agent(subject)
    response = run_agent_sync(agent, message)
    
    # Parse response
    schema_model = create_taxonomy_schema(subject)
    parsed = schema_model.model_validate_json(response)
    
    # Convert to TaxonomyClassification
    result = TaxonomyClassification(
        chapter=parsed.chapter,
        topic=parsed.topic,
        subtopic=parsed.subtopic,
        key_concepts=parsed.key_concepts,
        prerequisite_concepts=parsed.prerequisite_concepts,
        related_topics=parsed.related_topics,
        cognitive_level=parsed.cognitive_level,
        exam_relevance=parsed.exam_relevance,
        confidence=parsed.confidence,
    )
    
    # Fallback to mini if confidence is low
    config = get_config()
    if result.confidence < config.taxonomy_confidence_threshold:
        # Retry with gpt-5-mini
        config.taxonomy_classifier.model = "gpt-5-mini"
        agent = create_taxonomy_classifier_agent(subject)
        response = run_agent_sync(agent, message)
        parsed = schema_model.model_validate_json(response)
        result = TaxonomyClassification(
            chapter=parsed.chapter,
            topic=parsed.topic,
            subtopic=parsed.subtopic,
            key_concepts=parsed.key_concepts,
            prerequisite_concepts=parsed.prerequisite_concepts,
            related_topics=parsed.related_topics,
            cognitive_level=parsed.cognitive_level,
            exam_relevance=parsed.exam_relevance,
            confidence=parsed.confidence,
        )
    
    return result


__all__ = [
    "create_taxonomy_classifier_agent",
    "classify_taxonomy",
    "get_taxonomy_classifier_prompt",
]
