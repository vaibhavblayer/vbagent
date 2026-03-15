"""Tests for classification models v2."""

import pytest
from vbagent.models.classification import (
    PrimaryClassification,
    DiagramAnalysis,
    DifficultyAssessment,
    ClassificationResult,
    TikZValidation,
)


def test_primary_classification_creation():
    """Test PrimaryClassification model creation (simplified to 3 fields)."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True,
    )
    
    assert primary.subject == "physics"
    assert primary.question_type == "mcq_sc"
    assert primary.has_diagram is True
    assert primary.confidence == 1.0
    assert primary.classified_from == "image"


def test_diagram_analysis_creation():
    """Test DiagramAnalysis model creation."""
    diagram = DiagramAnalysis(
        diagram_type="free_body",
        diagram_category="mechanics",
        diagram_complexity="simple",
        diagram_elements=["force", "vector"],
        suggested_tikz_agent="fbd"
    )
    
    assert diagram.diagram_type == "free_body"
    assert diagram.diagram_category == "mechanics"
    assert diagram.suggested_tikz_agent == "fbd"


def test_difficulty_assessment_creation():
    """Test DifficultyAssessment model creation."""
    difficulty = DifficultyAssessment(
        difficulty="medium",
        difficulty_score=5.5,
        difficulty_reasoning="Requires understanding of force vectors",
        expected_solve_time_minutes=5,
        prerequisite_concepts=["Newton's laws"],
        common_mistakes=["Sign errors"],
        cognitive_level="apply"
    )
    
    assert difficulty.difficulty == "medium"
    assert difficulty.difficulty_score == 5.5
    assert difficulty.cognitive_level == "apply"


def test_classification_result_from_primary():
    """Test ClassificationResult creation from primary (simplified)."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True
    )
    
    result = ClassificationResult.from_primary(primary)
    
    assert result.subject == "physics"
    assert result.question_type == "mcq_sc"
    assert result.has_diagram is True
    assert result.difficulty is None  # Not set yet


def test_classification_result_from_agents():
    """Test ClassificationResult combining all agents (simplified)."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True
    )
    
    diagram = DiagramAnalysis(
        diagram_type="free_body",
        diagram_category="mechanics",
        diagram_complexity="simple",
        suggested_tikz_agent="fbd"
    )
    
    difficulty = DifficultyAssessment(
        difficulty="medium",
        difficulty_score=5.5,
        difficulty_reasoning="Test",
        expected_solve_time_minutes=5,
        cognitive_level="apply"
    )
    
    result = ClassificationResult.from_agents(primary, diagram, difficulty)
    
    assert result.subject == "physics"
    assert result.diagram_type == "free_body"
    assert result.difficulty == "medium"
    assert result.difficulty_score == 5.5
    assert result.suggested_tikz_agent == "fbd"


def test_tikz_validation_creation():
    """Test TikZValidation model creation."""
    validation = TikZValidation(
        is_valid=True,
        compilation_status="success"
    )
    
    assert validation.is_valid is True
    assert validation.compilation_status == "success"
    assert len(validation.errors_found) == 0


def test_model_serialization():
    """Test model JSON serialization (simplified)."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True
    )
    
    # Test serialization
    json_str = primary.model_dump_json()
    assert "physics" in json_str
    assert "mcq_sc" in json_str
    
    # Test deserialization
    primary2 = PrimaryClassification.model_validate_json(json_str)
    assert primary2.subject == primary.subject
    assert primary2.question_type == primary.question_type
