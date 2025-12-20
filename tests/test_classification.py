"""Property tests for classification output validity.

**Feature: physics-question-pipeline, Property 1: Classification Output Validity**
**Validates: Requirements 1.1, 1.2, 1.3**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import ValidationError

from vbagent.models.classification import (
    ClassificationResult,
    QuestionType,
    Difficulty,
    DiagramType,
)


# Valid values for enums
VALID_QUESTION_TYPES = ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]
VALID_DIAGRAM_TYPES = ["graph", "circuit", "free_body", "geometry", "none", None]


# Strategies for generating valid classification data
question_type_strategy = st.sampled_from(VALID_QUESTION_TYPES)
difficulty_strategy = st.sampled_from(VALID_DIFFICULTIES)
diagram_type_strategy = st.sampled_from(VALID_DIAGRAM_TYPES)
topic_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


@st.composite
def classification_result_strategy(draw):
    """Generate valid ClassificationResult instances."""
    question_type = draw(question_type_strategy)
    has_diagram = draw(st.booleans())
    
    # num_options only makes sense for MCQ types
    if question_type in ["mcq_sc", "mcq_mc"]:
        num_options = draw(st.integers(min_value=2, max_value=6))
    else:
        num_options = draw(st.none() | st.integers(min_value=2, max_value=6))
    
    return {
        "question_type": question_type,
        "difficulty": draw(difficulty_strategy),
        "topic": draw(topic_strategy),
        "subtopic": draw(topic_strategy),
        "has_diagram": has_diagram,
        "diagram_type": draw(diagram_type_strategy) if has_diagram else None,
        "num_options": num_options,
        "estimated_marks": draw(st.integers(min_value=1, max_value=10)),
        "key_concepts": draw(st.lists(st.text(min_size=1, max_size=30).filter(lambda x: x.strip()), max_size=5)),
        "requires_calculus": draw(st.booleans()),
        "confidence": draw(confidence_strategy),
    }


@given(data=classification_result_strategy())
@settings(max_examples=100)
def test_property_classification_output_validity(data: dict):
    """
    **Feature: physics-question-pipeline, Property 1: Classification Output Validity**
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    Property: For any valid classification data, the ClassificationResult model
    SHALL accept question_type from the set {mcq_sc, mcq_mc, subjective, 
    assertion_reason, passage, match} and difficulty from {easy, medium, hard}.
    """
    # Create ClassificationResult from generated data
    result = ClassificationResult(**data)
    
    # Property 1: question_type must be from valid set
    assert result.question_type in VALID_QUESTION_TYPES, (
        f"question_type '{result.question_type}' not in valid set"
    )
    
    # Property 2: difficulty must be from valid set
    assert result.difficulty in VALID_DIFFICULTIES, (
        f"difficulty '{result.difficulty}' not in valid set"
    )
    
    # Property 3: confidence must be between 0 and 1
    assert 0.0 <= result.confidence <= 1.0, (
        f"confidence {result.confidence} not in [0, 1]"
    )


@given(question_type=st.text(min_size=1).filter(lambda x: x not in VALID_QUESTION_TYPES))
@settings(max_examples=50)
def test_property_invalid_question_type_rejected(question_type: str):
    """
    **Feature: physics-question-pipeline, Property 1: Classification Output Validity**
    **Validates: Requirements 1.2**
    
    Property: For any invalid question_type, the ClassificationResult model
    SHALL reject the input with a validation error.
    """
    assume(question_type.strip())  # Skip empty strings
    
    with pytest.raises(ValidationError):
        ClassificationResult(
            question_type=question_type,
            difficulty="easy",
            topic="physics",
            subtopic="mechanics",
            has_diagram=False,
        )


@given(difficulty=st.text(min_size=1).filter(lambda x: x not in VALID_DIFFICULTIES))
@settings(max_examples=50)
def test_property_invalid_difficulty_rejected(difficulty: str):
    """
    **Feature: physics-question-pipeline, Property 1: Classification Output Validity**
    **Validates: Requirements 1.3**
    
    Property: For any invalid difficulty, the ClassificationResult model
    SHALL reject the input with a validation error.
    """
    assume(difficulty.strip())  # Skip empty strings
    
    with pytest.raises(ValidationError):
        ClassificationResult(
            question_type="mcq_sc",
            difficulty=difficulty,
            topic="physics",
            subtopic="mechanics",
            has_diagram=False,
        )


@given(confidence=st.floats().filter(lambda x: x < 0.0 or x > 1.0))
@settings(max_examples=50)
def test_property_invalid_confidence_rejected(confidence: float):
    """
    **Feature: physics-question-pipeline, Property 1: Classification Output Validity**
    **Validates: Requirements 1.1**
    
    Property: For any confidence value outside [0, 1], the ClassificationResult
    model SHALL reject the input with a validation error.
    """
    assume(not (confidence != confidence))  # Skip NaN
    
    with pytest.raises(ValidationError):
        ClassificationResult(
            question_type="mcq_sc",
            difficulty="easy",
            topic="physics",
            subtopic="mechanics",
            has_diagram=False,
            confidence=confidence,
        )


def test_classification_result_json_serialization():
    """Test that ClassificationResult can be serialized to JSON and back."""
    result = ClassificationResult(
        question_type="mcq_sc",
        difficulty="medium",
        topic="kinematics",
        subtopic="projectile motion",
        has_diagram=True,
        diagram_type="graph",
        num_options=4,
        estimated_marks=3,
        key_concepts=["velocity", "acceleration"],
        requires_calculus=False,
        confidence=0.95,
    )
    
    # Serialize to JSON
    json_str = result.model_dump_json()
    
    # Deserialize back
    restored = ClassificationResult.model_validate_json(json_str)
    
    # Verify round-trip
    assert restored == result
