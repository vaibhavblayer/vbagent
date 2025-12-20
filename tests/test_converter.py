"""Property tests for format conversion structure.

**Feature: physics-question-pipeline, Property 11: Format Conversion Structure**
**Validates: Requirements 8.1, 8.2, 8.3, 8.5**
"""

import re

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.agents.converter import VALID_FORMATS
from vbagent.prompts.converter import get_format_instructions, FORMAT_INSTRUCTIONS


# Strategy for generating format types
format_strategy = st.sampled_from(list(VALID_FORMATS))


def has_tasks_environment(latex: str) -> bool:
    """Check if LaTeX contains a tasks environment."""
    return r"\begin{tasks}" in latex or r"\end{tasks}" in latex


def has_task_items(latex: str) -> bool:
    """Check if LaTeX contains task items."""
    return r"\task" in latex


def requests_numerical_answer(latex: str) -> bool:
    """Check if the question requests a numerical/integer answer."""
    patterns = [
        r"integer",
        r"numerical",
        r"nearest\s+integer",
        r"answer\s+is\s+a\s+number",
        r"find\s+the\s+value",
        r"calculate",
        r"compute",
    ]
    latex_lower = latex.lower()
    return any(re.search(p, latex_lower) for p in patterns)


def validate_mcq_structure(latex: str) -> bool:
    """Validate that MCQ output has proper structure.
    
    MCQ outputs should contain:
    - tasks environment
    - task items for options
    """
    return has_tasks_environment(latex) and has_task_items(latex)


def validate_subjective_structure(latex: str) -> bool:
    """Validate that subjective output has proper structure.
    
    Subjective outputs should NOT contain:
    - tasks environment
    """
    return not has_tasks_environment(latex)


def validate_integer_structure(latex: str) -> bool:
    """Validate that integer type output has proper structure.
    
    Integer outputs should NOT contain:
    - tasks environment
    """
    return not has_tasks_environment(latex)


@given(target_format=format_strategy)
@settings(max_examples=100)
def test_property_format_instructions_exist(target_format: str):
    """
    **Feature: physics-question-pipeline, Property 11: Format Conversion Structure**
    **Validates: Requirements 8.1, 8.2, 8.3, 8.5**
    
    Property: For any valid target format, format-specific instructions
    SHALL exist and be non-empty.
    """
    instructions = get_format_instructions(target_format)
    
    assert instructions, (
        f"Format instructions for '{target_format}' should not be empty"
    )
    assert len(instructions) > 50, (
        f"Format instructions for '{target_format}' should be substantial"
    )


@given(target_format=format_strategy)
@settings(max_examples=100)
def test_property_mcq_instructions_mention_tasks(target_format: str):
    """
    **Feature: physics-question-pipeline, Property 11: Format Conversion Structure**
    **Validates: Requirements 8.1, 8.2**
    
    Property: For MCQ target formats, instructions SHALL mention tasks environment.
    For non-MCQ formats, instructions SHALL mention NOT using tasks environment.
    """
    instructions = get_format_instructions(target_format)
    
    if target_format in ("mcq_sc", "mcq_mc"):
        assert "tasks" in instructions.lower(), (
            f"MCQ format '{target_format}' instructions should mention tasks environment"
        )
        assert "\\task" in instructions or "task" in instructions.lower(), (
            f"MCQ format '{target_format}' instructions should mention task items"
        )
    else:
        # Subjective and integer should mention NOT using tasks
        assert "no tasks" in instructions.lower() or "remove" in instructions.lower(), (
            f"Non-MCQ format '{target_format}' instructions should mention not using tasks"
        )


@given(
    source_format=format_strategy,
    target_format=format_strategy
)
@settings(max_examples=100)
def test_property_format_conversion_valid_formats(source_format: str, target_format: str):
    """
    **Feature: physics-question-pipeline, Property 11: Format Conversion Structure**
    **Validates: Requirements 8.1, 8.2, 8.3, 8.5**
    
    Property: For any source and target format combination, both formats
    SHALL be in the set of valid formats.
    """
    assert source_format in VALID_FORMATS, (
        f"Source format '{source_format}' should be valid"
    )
    assert target_format in VALID_FORMATS, (
        f"Target format '{target_format}' should be valid"
    )


def test_mcq_sc_instructions_single_correct():
    """Test that mcq_sc instructions specify single correct answer."""
    instructions = get_format_instructions("mcq_sc")
    
    assert "single" in instructions.lower() or "one" in instructions.lower(), (
        "MCQ single correct instructions should mention single/one correct answer"
    )
    assert "4 options" in instructions or "exactly 4" in instructions.lower(), (
        "MCQ instructions should specify 4 options"
    )


def test_mcq_mc_instructions_multiple_correct():
    """Test that mcq_mc instructions specify multiple correct answers."""
    instructions = get_format_instructions("mcq_mc")
    
    assert "multiple" in instructions.lower() or "at least 2" in instructions.lower(), (
        "MCQ multiple correct instructions should mention multiple correct answers"
    )


def test_subjective_instructions_no_options():
    """Test that subjective instructions specify no options."""
    instructions = get_format_instructions("subjective")
    
    assert "remove" in instructions.lower() or "no" in instructions.lower(), (
        "Subjective instructions should mention removing options"
    )


def test_integer_instructions_single_number():
    """Test that integer instructions specify single number answer."""
    instructions = get_format_instructions("integer")
    
    assert "integer" in instructions.lower() or "single" in instructions.lower(), (
        "Integer instructions should mention integer/single number answer"
    )


def test_all_formats_have_instructions():
    """Test that all valid formats have corresponding instructions."""
    for fmt in VALID_FORMATS:
        instructions = get_format_instructions(fmt)
        assert instructions, f"Format '{fmt}' should have instructions"
        assert fmt in FORMAT_INSTRUCTIONS, f"Format '{fmt}' should be in FORMAT_INSTRUCTIONS"


def test_validate_mcq_structure_with_tasks():
    """Test MCQ structure validation with tasks environment."""
    mcq_latex = r"""
    \item What is the velocity?
    \begin{tasks}(4)
        \task 10 m/s
        \task 20 m/s
        \task 30 m/s
        \task 40 m/s
    \end{tasks}
    \begin{solution}
    The answer is (A).
    \end{solution}
    """
    assert validate_mcq_structure(mcq_latex)


def test_validate_mcq_structure_without_tasks():
    """Test MCQ structure validation fails without tasks environment."""
    no_tasks_latex = r"""
    \item What is the velocity?
    (A) 10 m/s (B) 20 m/s (C) 30 m/s (D) 40 m/s
    \begin{solution}
    The answer is (A).
    \end{solution}
    """
    assert not validate_mcq_structure(no_tasks_latex)


def test_validate_subjective_structure():
    """Test subjective structure validation."""
    subjective_latex = r"""
    \item Derive the equation for projectile motion.
    \begin{solution}
    Starting from Newton's second law...
    \end{solution}
    """
    assert validate_subjective_structure(subjective_latex)


def test_validate_subjective_structure_fails_with_tasks():
    """Test subjective structure validation fails with tasks environment."""
    with_tasks_latex = r"""
    \item Derive the equation.
    \begin{tasks}(4)
        \task Option A
    \end{tasks}
    """
    assert not validate_subjective_structure(with_tasks_latex)


def test_validate_integer_structure():
    """Test integer type structure validation."""
    integer_latex = r"""
    \item Find the velocity in m/s. Give your answer as the nearest integer.
    \begin{solution}
    v = 25 m/s
    \end{solution}
    """
    assert validate_integer_structure(integer_latex)
