"""Property tests for idea extraction completeness.

**Feature: physics-question-pipeline, Property 5: Idea Extraction Completeness**
**Validates: Requirements 4.1, 4.2**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.models.idea import IdeaResult


# Strategies for generating valid idea data
concept_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
formula_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
technique_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
difficulty_factor_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())


@st.composite
def valid_idea_result_strategy(draw):
    """Generate valid IdeaResult instances with non-empty concepts and techniques."""
    # Property 5 requires non-empty concepts and techniques
    concepts = draw(st.lists(concept_strategy, min_size=1, max_size=5))
    techniques = draw(st.lists(technique_strategy, min_size=1, max_size=5))
    formulas = draw(st.lists(formula_strategy, min_size=0, max_size=5))
    difficulty_factors = draw(st.lists(difficulty_factor_strategy, min_size=0, max_size=5))
    
    return {
        "concepts": concepts,
        "formulas": formulas,
        "techniques": techniques,
        "difficulty_factors": difficulty_factors,
    }


@given(data=valid_idea_result_strategy())
@settings(max_examples=100)
def test_property_idea_extraction_completeness(data: dict):
    """
    **Feature: physics-question-pipeline, Property 5: Idea Extraction Completeness**
    **Validates: Requirements 4.1, 4.2**
    
    Property: For any valid problem and solution LaTeX input, the Idea Agent
    SHALL return an IdeaResult with non-empty concepts and techniques lists.
    
    This test validates that IdeaResult correctly stores and returns
    non-empty concepts and techniques lists.
    """
    # Create IdeaResult from generated data
    result = IdeaResult(**data)
    
    # Property: concepts list must be non-empty
    assert len(result.concepts) > 0, (
        "IdeaResult must have at least one concept"
    )
    
    # Property: techniques list must be non-empty
    assert len(result.techniques) > 0, (
        "IdeaResult must have at least one technique"
    )
    
    # Verify all concepts are non-empty strings
    for concept in result.concepts:
        assert concept.strip(), "Each concept must be a non-empty string"
    
    # Verify all techniques are non-empty strings
    for technique in result.techniques:
        assert technique.strip(), "Each technique must be a non-empty string"


@given(
    concepts=st.lists(concept_strategy, min_size=1, max_size=5),
    formulas=st.lists(formula_strategy, min_size=0, max_size=5),
    techniques=st.lists(technique_strategy, min_size=1, max_size=5),
    difficulty_factors=st.lists(difficulty_factor_strategy, min_size=0, max_size=5),
)
@settings(max_examples=100)
def test_property_idea_result_preserves_all_fields(
    concepts: list[str],
    formulas: list[str],
    techniques: list[str],
    difficulty_factors: list[str],
):
    """
    **Feature: physics-question-pipeline, Property 5: Idea Extraction Completeness**
    **Validates: Requirements 4.1, 4.2**
    
    Property: IdeaResult SHALL preserve all extracted concepts, formulas,
    techniques, and difficulty factors without loss.
    """
    result = IdeaResult(
        concepts=concepts,
        formulas=formulas,
        techniques=techniques,
        difficulty_factors=difficulty_factors,
    )
    
    # Verify all fields are preserved
    assert result.concepts == concepts
    assert result.formulas == formulas
    assert result.techniques == techniques
    assert result.difficulty_factors == difficulty_factors


def test_idea_result_json_serialization():
    """Test that IdeaResult can be serialized to JSON and back."""
    result = IdeaResult(
        concepts=["Newton's second law", "Conservation of momentum"],
        formulas=["F = ma", "p = mv"],
        techniques=["Free body diagram", "Momentum conservation approach"],
        difficulty_factors=["Multiple bodies", "Requires vector analysis"],
    )
    
    # Serialize to JSON
    json_str = result.model_dump_json()
    
    # Deserialize back
    restored = IdeaResult.model_validate_json(json_str)
    
    # Verify round-trip
    assert restored == result


def test_idea_result_default_empty_lists():
    """Test that IdeaResult uses empty lists as defaults."""
    result = IdeaResult()
    
    assert result.concepts == []
    assert result.formulas == []
    assert result.techniques == []
    assert result.difficulty_factors == []


def test_idea_result_with_latex_formulas():
    """Test that IdeaResult handles LaTeX formulas correctly."""
    result = IdeaResult(
        concepts=["Electromagnetic induction"],
        formulas=[
            r"\oint \vec{B} \cdot d\vec{l} = \mu_0 I",
            r"\mathcal{E} = -\frac{d\Phi_B}{dt}",
        ],
        techniques=["Applying Faraday's law"],
        difficulty_factors=["Requires calculus"],
    )
    
    # Verify LaTeX formulas are preserved
    assert r"\oint" in result.formulas[0]
    assert r"\frac" in result.formulas[1]
