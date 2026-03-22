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
    DiagramCategory,
)


# Valid values for enums
VALID_QUESTION_TYPES = ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]
VALID_DIAGRAM_CATEGORIES = [
    "mechanics", "kinematics", "circuits", "optics", "waves",
    "thermodynamics", "organic", "inorganic", "graphs", "geometry", "none"
]


# Strategies for generating valid classification data
question_type_strategy = st.sampled_from(VALID_QUESTION_TYPES)
difficulty_strategy = st.sampled_from(VALID_DIFFICULTIES)
diagram_category_strategy = st.sampled_from(VALID_DIAGRAM_CATEGORIES)
topic_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


@st.composite
def classification_result_strategy(draw):
    """Generate valid ClassificationResult instances."""
    question_type = draw(question_type_strategy)
    has_diagram = draw(st.booleans())
    
    return {
        "subject": "physics",
        "question_type": question_type,
        "has_diagram": has_diagram,
        "diagram_category": draw(st.none() | diagram_category_strategy) if has_diagram else None,
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
    
    # Property 2: confidence must be between 0 and 1
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
            subject="physics",
            question_type=question_type,
            has_diagram=False,
        )


@given(difficulty=st.text(min_size=1).filter(lambda x: x not in VALID_DIFFICULTIES))
@settings(max_examples=50)
def test_property_invalid_difficulty_rejected(difficulty: str):
    """
    **Feature: physics-question-pipeline, Property 1: Classification Output Validity**
    **Validates: Requirements 1.3**
    
    Property: For any invalid difficulty, the DifficultyAssessment model
    SHALL reject the input with a validation error.
    """
    assume(difficulty.strip())  # Skip empty strings
    
    from vbagent.models.classification import DifficultyAssessment
    with pytest.raises(ValidationError):
        DifficultyAssessment(
            difficulty=difficulty,
            difficulty_score=5.0,
            difficulty_reasoning="test",
            expected_solve_time_minutes=5,
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
            subject="physics",
            question_type="mcq_sc",
            has_diagram=False,
            confidence=confidence,
        )


def test_classification_result_json_serialization():
    """Test that ClassificationResult can be serialized to JSON and back."""
    result = ClassificationResult(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True,
        diagram_category="kinematics",
        confidence=0.95,
    )
    
    # Serialize to JSON
    json_str = result.model_dump_json()
    
    # Deserialize back
    restored = ClassificationResult.model_validate_json(json_str)
    
    # Verify round-trip
    assert restored == result
