"""Dynamic Pydantic schema builder for structured taxonomy outputs.

Creates Pydantic models with Literal types from taxonomy at runtime.
Used for OpenAI structured outputs to enforce valid chapter/topic selection.
"""

from typing import Type, get_args
from pydantic import BaseModel, Field, create_model
from functools import lru_cache

from vbagent.prompts.classification.taxonomy import get_chapters, get_all_topics


@lru_cache(maxsize=4)  # Cache for each subject
def create_taxonomy_schema(subject: str) -> Type[BaseModel]:
    """Create a Pydantic model with Literal types for taxonomy.
    
    Args:
        subject: Subject name (physics, chemistry, mathematics, biology)
        
    Returns:
        Pydantic model class with structured taxonomy fields
        
    Example:
        >>> PhysicsSchema = create_taxonomy_schema("physics")
        >>> # PhysicsSchema.chapter is Literal["Kinematics", "Laws of Motion", ...]
        >>> # PhysicsSchema.topic is Literal["motion in a straight line", ...]
    """
    chapters = get_chapters(subject)
    topics = get_all_topics(subject)
    
    # Create Literal types
    # Note: We can't use typing.Literal directly with dynamic values,
    # so we'll use str with Field constraints and validation
    
    # For now, use str types with descriptions
    # OpenAI structured outputs will enforce these via JSON schema
    fields = {
        "chapter": (
            str,
            Field(
                description=f"Chapter from: {', '.join(chapters[:5])}... ({len(chapters)} total)"
            )
        ),
        "topic": (
            str,
            Field(
                description=f"Topic from: {', '.join(topics[:10])}... ({len(topics)} total)"
            )
        ),
        "subtopic": (
            str,
            Field(description="Specific subtopic within the topic")
        ),
        "key_concepts": (
            list[str],
            Field(default_factory=list, description="Key concepts in the problem")
        ),
        "prerequisite_concepts": (
            list[str],
            Field(default_factory=list, description="Prerequisites needed")
        ),
        "related_topics": (
            list[str],
            Field(default_factory=list, description="Related curriculum topics")
        ),
        "cognitive_level": (
            str,
            Field(
                default="apply",
                description="Bloom's level: remember, understand, apply, analyze, evaluate, create"
            )
        ),
        "exam_relevance": (
            list[str],
            Field(default_factory=list, description="Relevant exams (JEE Main, NEET, etc.)")
        ),
        "confidence": (
            float,
            Field(default=1.0, ge=0.0, le=1.0, description="Classification confidence")
        ),
    }
    
    # Create dynamic model
    model_name = f"{subject.capitalize()}TaxonomySchema"
    schema_model = create_model(model_name, **fields)
    
    return schema_model


def get_taxonomy_json_schema(subject: str) -> dict:
    """Get JSON schema for taxonomy structured output.
    
    Args:
        subject: Subject name
        
    Returns:
        JSON schema dict for OpenAI structured outputs
    """
    schema_model = create_taxonomy_schema(subject)
    json_schema = schema_model.model_json_schema()
    
    # Add enum constraints for chapter and topic
    chapters = get_chapters(subject)
    topics = get_all_topics(subject)
    
    # Modify schema to add enum constraints
    if "properties" in json_schema:
        if "chapter" in json_schema["properties"]:
            json_schema["properties"]["chapter"]["enum"] = chapters
        if "topic" in json_schema["properties"]:
            json_schema["properties"]["topic"]["enum"] = topics
        if "cognitive_level" in json_schema["properties"]:
            json_schema["properties"]["cognitive_level"]["enum"] = [
                "remember", "understand", "apply",
                "analyze", "evaluate", "create"
            ]
    
    return json_schema


__all__ = [
    "create_taxonomy_schema",
    "get_taxonomy_json_schema",
]
