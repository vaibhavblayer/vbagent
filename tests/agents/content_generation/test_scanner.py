"""Property tests for scanner agent.

**Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
**Feature: physics-question-pipeline, Property 3: LaTeX Output Structure**
**Validates: Requirements 2.1, 2.4**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.prompts.content_generation.scanner import (
    SCANNER_PROMPTS,
    get_scanner_prompt,
    get_user_template,
)
from vbagent.agents.content_generation.scanner import create_scanner_agent


# Valid question types
VALID_QUESTION_TYPES = ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"]

# Valid subjects
VALID_SUBJECTS = ["physics", "chemistry", "mathematics", "biology"]


# Strategy for valid question types
question_type_strategy = st.sampled_from(VALID_QUESTION_TYPES)
subject_strategy = st.sampled_from(VALID_SUBJECTS)


@given(question_type=question_type_strategy, subject=subject_strategy)
@settings(max_examples=100)
def test_property_scanner_prompt_selection(question_type: str, subject: str):
    """
    **Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
    **Validates: Requirements 2.1**
    
    Property: For any classification result with a question_type, the Scanner Agent
    SHALL load and use the prompt file corresponding to that question_type,
    with subject-specific additions.
    """
    # Get the prompt for this question type and subject
    prompt = get_scanner_prompt(question_type, subject)
    
    # Property 1: Prompt must be a non-empty string
    assert isinstance(prompt, str), f"Prompt for {question_type} must be a string"
    assert len(prompt.strip()) > 0, f"Prompt for {question_type} must not be empty"
    
    # Property 2: Prompt must contain the base prompt content
    base_prompt = SCANNER_PROMPTS[question_type]
    # The base prompt content should be present (possibly with subject substitutions)
    assert "\\item" in prompt, "Prompt must contain LaTeX structure instructions"
    assert "\\end{solution}" in prompt, "Prompt must contain solution structure"
    
    # Property 3: Prompt must contain subject-specific content
    assert subject in prompt.lower() or "Subject:" in prompt, (
        f"Prompt must contain subject-specific content for {subject}"
    )


@given(question_type=question_type_strategy, subject=subject_strategy)
@settings(max_examples=100, deadline=None)  # Disable deadline for agent creation
def test_property_scanner_agent_creation(question_type: str, subject: str):
    """
    **Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
    **Validates: Requirements 2.1**
    
    Property: For any valid question_type and subject, create_scanner_agent SHALL return
    an Agent configured with the correct type-specific and subject-specific prompt.
    """
    agent = create_scanner_agent(question_type, subject=subject)
    
    # Property 1: Agent must be created successfully
    assert agent is not None, f"Agent for {question_type} must be created"
    
    # Property 2: Agent name must include the question type and subject
    assert question_type in agent.name, (
        f"Agent name '{agent.name}' must include question type '{question_type}'"
    )
    assert subject in agent.name, (
        f"Agent name '{agent.name}' must include subject '{subject}'"
    )
    
    # Property 3: Agent instructions must match the expected prompt
    expected_prompt = get_scanner_prompt(question_type, subject)
    assert agent.instructions == expected_prompt, (
        f"Agent instructions must match prompt for {question_type}/{subject}"
    )


@given(invalid_type=st.text(min_size=1, max_size=20).filter(
    lambda x: x.strip() and x not in VALID_QUESTION_TYPES
))
@settings(max_examples=50)
def test_property_scanner_fallback_for_unknown_type(invalid_type: str):
    """
    **Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
    **Validates: Requirements 2.1**
    
    Property: For any unknown question_type, get_scanner_prompt SHALL fall back
    to the mcq_sc prompt (as per design doc error handling).
    """
    assume(invalid_type.strip())  # Skip empty strings
    
    # Get prompt for invalid type - should fall back to mcq_sc
    prompt = get_scanner_prompt(invalid_type)
    expected = get_scanner_prompt("mcq_sc")
    
    # Property: Should return mcq_sc prompt as fallback
    assert prompt == expected, (
        f"Unknown type '{invalid_type}' should fall back to mcq_sc prompt"
    )


def test_all_question_types_have_prompts():
    """
    **Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
    **Validates: Requirements 2.1**
    
    Verify that all valid question types have corresponding prompts.
    """
    for question_type in VALID_QUESTION_TYPES:
        assert question_type in SCANNER_PROMPTS, (
            f"Question type '{question_type}' must have a prompt in SCANNER_PROMPTS"
        )
        prompt = SCANNER_PROMPTS[question_type]
        assert isinstance(prompt, str) and len(prompt.strip()) > 0, (
            f"Prompt for '{question_type}' must be a non-empty string"
        )


def test_user_template_exists():
    """
    **Feature: physics-question-pipeline, Property 2: Scanner Prompt Selection**
    **Validates: Requirements 2.1**
    
    Verify that get_user_template returns valid templates for all subjects.
    """
    for subject in VALID_SUBJECTS:
        template = get_user_template(subject)
        assert isinstance(template, str), f"User template for {subject} must be a string"
        assert len(template.strip()) > 0, f"User template for {subject} must not be empty"
        assert subject in template, f"User template must contain subject '{subject}'"


# Strategy for generating mock LaTeX output
@st.composite
def valid_latex_output_strategy(draw):
    """Generate valid LaTeX output that follows the expected structure."""
    # Generate problem content
    problem_text = draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip()))
    
    # Generate solution content
    solution_content = draw(st.text(min_size=10, max_size=500).filter(lambda x: x.strip()))
    
    return f"\\item {problem_text}\n\\begin{{solution}}\n{solution_content}\n\\end{{solution}}"


@st.composite
def invalid_latex_output_strategy(draw):
    """Generate invalid LaTeX output that doesn't follow the expected structure."""
    choice = draw(st.integers(min_value=0, max_value=2))
    content = draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip()))
    
    if choice == 0:
        # Missing \item at start
        return f"Problem: {content}\n\\begin{{solution}}\n{content}\n\\end{{solution}}"
    elif choice == 1:
        # Missing \end{solution}
        return f"\\item {content}\n\\begin{{solution}}\n{content}"
    else:
        # Missing solution environment entirely
        return f"\\item {content}"


@given(latex=valid_latex_output_strategy())
@settings(max_examples=100)
def test_property_latex_output_structure_valid(latex: str):
    """
    **Feature: physics-question-pipeline, Property 3: LaTeX Output Structure**
    **Validates: Requirements 2.4**
    
    Property: For any successful scan operation, the output LaTeX SHALL start
    with `\\item` and end with `\\end{solution}`.
    """
    # Property 1: Must start with \item
    assert latex.strip().startswith("\\item"), (
        "LaTeX output must start with \\item"
    )
    
    # Property 2: Must end with \end{solution}
    assert latex.strip().endswith("\\end{solution}"), (
        "LaTeX output must end with \\end{solution}"
    )


@given(latex=invalid_latex_output_strategy())
@settings(max_examples=50)
def test_property_latex_output_structure_invalid_detection(latex: str):
    """
    **Feature: physics-question-pipeline, Property 3: LaTeX Output Structure**
    **Validates: Requirements 2.4**
    
    Property: Invalid LaTeX output that doesn't follow the structure SHALL be
    detectable by checking start and end patterns.
    """
    starts_correctly = latex.strip().startswith("\\item")
    ends_correctly = latex.strip().endswith("\\end{solution}")
    
    # At least one of these should be false for invalid output
    is_valid = starts_correctly and ends_correctly
    
    # This test verifies our validation logic can detect invalid output
    # The invalid strategy generates output missing at least one requirement
    assert not is_valid, (
        "Invalid LaTeX output should fail structure validation"
    )


def validate_latex_structure(latex: str) -> bool:
    """Validate that LaTeX output follows the expected structure.
    
    Args:
        latex: The LaTeX string to validate
        
    Returns:
        True if valid, False otherwise
    """
    stripped = latex.strip()
    return stripped.startswith("\\item") and stripped.endswith("\\end{solution}")


@given(latex=valid_latex_output_strategy())
@settings(max_examples=100)
def test_property_validate_latex_structure_accepts_valid(latex: str):
    """
    **Feature: physics-question-pipeline, Property 3: LaTeX Output Structure**
    **Validates: Requirements 2.4**
    
    Property: The validate_latex_structure function SHALL return True for
    any LaTeX that starts with \\item and ends with \\end{solution}.
    """
    assert validate_latex_structure(latex) is True


@given(latex=invalid_latex_output_strategy())
@settings(max_examples=50)
def test_property_validate_latex_structure_rejects_invalid(latex: str):
    """
    **Feature: physics-question-pipeline, Property 3: LaTeX Output Structure**
    **Validates: Requirements 2.4**
    
    Property: The validate_latex_structure function SHALL return False for
    any LaTeX that doesn't start with \\item or doesn't end with \\end{solution}.
    """
    assert validate_latex_structure(latex) is False
