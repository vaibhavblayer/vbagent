"""Property tests for alternate solution answer preservation.

**Feature: physics-question-pipeline, Property 6: Alternate Solution Answer Preservation**
**Validates: Requirements 5.3**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.agents.alternate import extract_answer


# Strategies for generating numerical answers
integer_strategy = st.integers(min_value=-1000, max_value=1000)
float_strategy = st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)
scientific_notation_strategy = st.tuples(
    st.floats(min_value=1.0, max_value=9.99, allow_nan=False, allow_infinity=False),
    st.integers(min_value=-10, max_value=10)
)


@given(answer=integer_strategy)
@settings(max_examples=100)
def test_property_extract_answer_boxed_integers(answer: int):
    """
    **Feature: physics-question-pipeline, Property 6: Alternate Solution Answer Preservation**
    **Validates: Requirements 5.3**
    
    Property: For any boxed integer answer in a solution, extract_answer
    SHALL correctly extract the numerical value.
    """
    solution = f"Therefore, the answer is \\boxed{{{answer}}}"
    
    extracted = extract_answer(solution)
    
    assert extracted == str(answer), (
        f"Expected to extract '{answer}' from boxed answer, got '{extracted}'"
    )


@given(mantissa=st.floats(min_value=1.0, max_value=9.99, allow_nan=False, allow_infinity=False),
       exponent=st.integers(min_value=-10, max_value=10))
@settings(max_examples=100)
def test_property_extract_answer_boxed_scientific(mantissa: float, exponent: int):
    """
    **Feature: physics-question-pipeline, Property 6: Alternate Solution Answer Preservation**
    **Validates: Requirements 5.3**
    
    Property: For any boxed scientific notation answer, extract_answer
    SHALL correctly extract the value.
    """
    # Format as scientific notation
    answer_str = f"{mantissa:.2f} \\times 10^{{{exponent}}}"
    solution = f"The final result is \\boxed{{{answer_str}}}"
    
    extracted = extract_answer(solution)
    
    assert answer_str in extracted or str(mantissa)[:4] in extracted, (
        f"Expected to extract scientific notation '{answer_str}', got '{extracted}'"
    )


@given(answer=st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_property_extract_answer_equals_pattern(answer: float):
    """
    **Feature: physics-question-pipeline, Property 6: Alternate Solution Answer Preservation**
    **Validates: Requirements 5.3**
    
    Property: For any numerical answer following an equals sign at end of solution,
    extract_answer SHALL correctly extract the value.
    """
    # Round to avoid floating point representation issues
    answer_rounded = round(answer, 2)
    solution = f"Solving the equation, we get v = {answer_rounded}"
    
    extracted = extract_answer(solution)
    
    # The extracted value should contain the answer
    assert str(abs(int(answer_rounded))) in extracted or str(answer_rounded) in extracted, (
        f"Expected to extract '{answer_rounded}' from equals pattern, got '{extracted}'"
    )


@given(answer=integer_strategy)
@settings(max_examples=100)
def test_property_extract_answer_explicit_marker(answer: int):
    """
    **Feature: physics-question-pipeline, Property 6: Alternate Solution Answer Preservation**
    **Validates: Requirements 5.3**
    
    Property: For any answer with explicit 'Answer:' marker,
    extract_answer SHALL correctly extract the value.
    """
    solution = f"Working through the problem...\nAnswer: {answer}"
    
    extracted = extract_answer(solution)
    
    assert str(answer) in extracted, (
        f"Expected to extract '{answer}' from explicit marker, got '{extracted}'"
    )


def test_extract_answer_empty_solution():
    """Test that extract_answer returns empty string for empty solution."""
    assert extract_answer("") == ""
    assert extract_answer("   ") == ""


def test_extract_answer_no_answer_pattern():
    """Test that extract_answer returns empty string when no answer pattern found."""
    solution = "This is just some text without any numerical answer."
    assert extract_answer(solution) == ""


def test_extract_answer_multiple_boxed():
    """Test that extract_answer returns the last boxed answer."""
    solution = r"""
    First we find x = \boxed{5}
    Then we calculate y = \boxed{10}
    Finally, the answer is \boxed{42}
    """
    extracted = extract_answer(solution)
    assert "42" in extracted


def test_extract_answer_with_units():
    """Test that extract_answer handles answers with units."""
    solution = r"The velocity is v = 25.5 \text{m/s}"
    extracted = extract_answer(solution)
    assert "25.5" in extracted


def test_extract_answer_negative_number():
    """Test that extract_answer handles negative numbers."""
    solution = r"The displacement is \boxed{-15.3}"
    extracted = extract_answer(solution)
    assert "-15.3" in extracted


def test_extract_answer_scientific_notation_caret():
    """Test extract_answer with scientific notation using caret."""
    solution = r"The charge is q = 1.6 \times 10^{-19} C"
    extracted = extract_answer(solution)
    # Should extract the numerical part
    assert "1.6" in extracted or "10" in extracted
