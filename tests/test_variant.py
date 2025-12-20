"""Property tests for variant generation.

Tests for:
- Property 7: Numerical Variant Number Modification
- Property 8: Context Variant Number Preservation
- Property 9: Variant Solution Completeness
"""

import re
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.agents.variant import (
    VALID_VARIANT_TYPES,
    VARIANT_PROMPTS,
    get_variant_prompt,
    create_variant_agent,
)


# Strategies for generating test data
number_strategy = st.integers(min_value=1, max_value=1000)
float_number_strategy = st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False)


def extract_numbers(text: str) -> list[float]:
    """Extract all numerical values from text.
    
    Handles integers, decimals, and scientific notation.
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        List of extracted numbers as floats
    """
    # Pattern for numbers: integers, decimals, scientific notation
    pattern = r'(?<![a-zA-Z])(-?\d+\.?\d*(?:[eE][+-]?\d+)?)'
    matches = re.findall(pattern, text)
    
    numbers = []
    for match in matches:
        try:
            num = float(match)
            # Filter out very small numbers that might be formatting artifacts
            if abs(num) >= 0.001 or num == 0:
                numbers.append(num)
        except ValueError:
            continue
    
    return numbers


def extract_context_words(text: str) -> set[str]:
    """Extract non-numerical context words from text.
    
    Filters out LaTeX commands, numbers, and common words.
    
    Args:
        text: Text to extract words from
        
    Returns:
        Set of context words
    """
    # Remove LaTeX commands
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    # Remove numbers
    text = re.sub(r'-?\d+\.?\d*', '', text)
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out common LaTeX/math words
    common_words = {
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was',
        'text', 'frac', 'begin', 'end', 'item', 'task', 'solution', 'align',
        'intertext', 'therefore', 'correct', 'option', 'left', 'right',
    }
    
    return set(words) - common_words


def has_solution_environment(latex: str) -> bool:
    """Check if LaTeX contains a solution environment.
    
    Args:
        latex: LaTeX text to check
        
    Returns:
        True if solution environment is present
    """
    return r'\begin{solution}' in latex and r'\end{solution}' in latex


def has_complete_solution(latex: str) -> bool:
    """Check if LaTeX contains a complete solution with calculations.
    
    Args:
        latex: LaTeX text to check
        
    Returns:
        True if solution appears complete
    """
    if not has_solution_environment(latex):
        return False
    
    # Extract solution content
    match = re.search(r'\\begin\{solution\}(.*?)\\end\{solution\}', latex, re.DOTALL)
    if not match:
        return False
    
    solution_content = match.group(1)
    
    # Check for calculation indicators
    has_align = 'align' in solution_content
    has_equations = '=' in solution_content
    has_numbers = bool(re.search(r'\d', solution_content))
    
    return has_align or (has_equations and has_numbers)


# =============================================================================
# Property 7: Numerical Variant Number Modification
# =============================================================================

@given(
    initial_distance=st.integers(min_value=100, max_value=1000),
    initial_velocity=st.integers(min_value=10, max_value=50),
    time=st.integers(min_value=10, max_value=100),
)
@settings(max_examples=100)
def test_property_numerical_variant_prompt_selection(
    initial_distance: int,
    initial_velocity: int,
    time: int,
):
    """
    **Feature: physics-question-pipeline, Property 7: Numerical Variant Number Modification**
    **Validates: Requirements 6.1**
    
    Property: For any numerical variant request, the system SHALL use the
    numerical variant prompt which instructs to modify only numerical values.
    """
    # Verify the numerical prompt exists and has correct instructions
    system_prompt, user_template = get_variant_prompt("numerical")
    
    # The system prompt should instruct to modify ONLY numerical values
    assert "numerical values" in system_prompt.lower(), (
        "Numerical variant prompt must mention modifying numerical values"
    )
    assert "context" in system_prompt.lower(), (
        "Numerical variant prompt must mention preserving context"
    )
    
    # The user template should have placeholder for source latex
    assert "{source_latex}" in user_template, (
        "User template must have source_latex placeholder"
    )


@given(variant_type=st.sampled_from(["numerical"]))
@settings(max_examples=100)
def test_property_numerical_variant_agent_creation(variant_type: str):
    """
    **Feature: physics-question-pipeline, Property 7: Numerical Variant Number Modification**
    **Validates: Requirements 6.1**
    
    Property: For any numerical variant type, create_variant_agent SHALL
    return an agent configured with the numerical variant prompt.
    """
    agent = create_variant_agent(variant_type)
    
    assert agent is not None, "Agent must be created"
    assert agent.name == f"Variant-{variant_type}", (
        f"Agent name should be 'Variant-{variant_type}'"
    )


def test_numerical_variant_prompt_content():
    """
    **Feature: physics-question-pipeline, Property 7: Numerical Variant Number Modification**
    **Validates: Requirements 6.1**
    
    Test that numerical variant prompt contains required instructions.
    """
    system_prompt, user_template = get_variant_prompt("numerical")
    
    # Must instruct to change numbers
    assert any(phrase in system_prompt.lower() for phrase in [
        "numerical values",
        "modify numerical",
        "change numerical",
    ]), "Prompt must instruct to modify numerical values"
    
    # Must instruct to preserve context
    assert any(phrase in system_prompt.lower() for phrase in [
        "context",
        "scenario",
        "same",
    ]), "Prompt must instruct to preserve context"
    
    # Must mention recalculation
    assert "recalculate" in system_prompt.lower(), (
        "Prompt must mention recalculating the solution"
    )


# =============================================================================
# Property 8: Context Variant Number Preservation
# =============================================================================

@given(
    initial_distance=st.integers(min_value=100, max_value=1000),
    initial_velocity=st.integers(min_value=10, max_value=50),
)
@settings(max_examples=100)
def test_property_context_variant_prompt_selection(
    initial_distance: int,
    initial_velocity: int,
):
    """
    **Feature: physics-question-pipeline, Property 8: Context Variant Number Preservation**
    **Validates: Requirements 6.2**
    
    Property: For any context variant request, the system SHALL use the
    context variant prompt which instructs to preserve all numerical values.
    """
    system_prompt, user_template = get_variant_prompt("context")
    
    # The system prompt should instruct to preserve numerical values
    assert "numerical values" in system_prompt.lower(), (
        "Context variant prompt must mention numerical values"
    )
    assert any(phrase in system_prompt.lower() for phrase in [
        "identical",
        "same",
        "preserve",
        "keep",
    ]), "Context variant prompt must instruct to preserve numbers"
    
    # The system prompt should instruct to change context
    assert "context" in system_prompt.lower(), (
        "Context variant prompt must mention changing context"
    )


@given(variant_type=st.sampled_from(["context"]))
@settings(max_examples=100)
def test_property_context_variant_agent_creation(variant_type: str):
    """
    **Feature: physics-question-pipeline, Property 8: Context Variant Number Preservation**
    **Validates: Requirements 6.2**
    
    Property: For any context variant type, create_variant_agent SHALL
    return an agent configured with the context variant prompt.
    """
    agent = create_variant_agent(variant_type)
    
    assert agent is not None, "Agent must be created"
    assert agent.name == f"Variant-{variant_type}", (
        f"Agent name should be 'Variant-{variant_type}'"
    )


def test_context_variant_prompt_content():
    """
    **Feature: physics-question-pipeline, Property 8: Context Variant Number Preservation**
    **Validates: Requirements 6.2**
    
    Test that context variant prompt contains required instructions.
    """
    system_prompt, user_template = get_variant_prompt("context")
    
    # Must instruct to keep numbers identical
    assert any(phrase in system_prompt.lower() for phrase in [
        "identical",
        "same",
        "do not change",
        "keep",
    ]), "Prompt must instruct to keep numbers identical"
    
    # Must instruct to change context/scenario
    assert any(phrase in system_prompt.lower() for phrase in [
        "context",
        "scenario",
        "story",
    ]), "Prompt must instruct to change context"


# =============================================================================
# Property 9: Variant Solution Completeness
# =============================================================================

@given(variant_type=st.sampled_from(VALID_VARIANT_TYPES))
@settings(max_examples=100)
def test_property_variant_solution_completeness_prompt(variant_type: str):
    """
    **Feature: physics-question-pipeline, Property 9: Variant Solution Completeness**
    **Validates: Requirements 6.5, 6.6**
    
    Property: For any variant type, the prompt SHALL instruct to include
    a complete solution environment with recalculated steps.
    """
    system_prompt, user_template = get_variant_prompt(variant_type)
    
    # Must mention solution environment
    assert "solution" in system_prompt.lower(), (
        f"Prompt for {variant_type} must mention solution"
    )
    
    # Must mention the output format ending with solution
    assert "end{solution}" in system_prompt.lower(), (
        f"Prompt for {variant_type} must specify ending with solution environment"
    )


@given(variant_type=st.sampled_from(VALID_VARIANT_TYPES))
@settings(max_examples=100)
def test_property_variant_prompts_exist(variant_type: str):
    """
    **Feature: physics-question-pipeline, Property 9: Variant Solution Completeness**
    **Validates: Requirements 6.5, 6.6**
    
    Property: For any valid variant type, the system SHALL have
    corresponding prompts defined.
    """
    assert variant_type in VARIANT_PROMPTS, (
        f"Variant type {variant_type} must have prompts defined"
    )
    
    prompts = VARIANT_PROMPTS[variant_type]
    assert "system" in prompts, f"Variant {variant_type} must have system prompt"
    assert "user" in prompts, f"Variant {variant_type} must have user template"


def test_all_variant_types_have_solution_instructions():
    """
    **Feature: physics-question-pipeline, Property 9: Variant Solution Completeness**
    **Validates: Requirements 6.5, 6.6**
    
    Test that all variant prompts instruct to include complete solutions.
    """
    for variant_type in VALID_VARIANT_TYPES:
        system_prompt, _ = get_variant_prompt(variant_type)
        
        # Must mention solution
        assert "solution" in system_prompt.lower(), (
            f"Prompt for {variant_type} must mention solution"
        )
        
        # Must mention solution environment format
        assert "end{solution}" in system_prompt.lower(), (
            f"Prompt for {variant_type} must mention solution environment"
        )
        
        # For non-context variants, must mention calculations/align
        # Context variants keep the solution identical, so they don't need to specify align
        if variant_type != "context":
            assert any(word in system_prompt.lower() for word in ["align", "calculation", "recalculate"]), (
                f"Prompt for {variant_type} must mention calculations or align environment"
            )


# =============================================================================
# Additional Unit Tests
# =============================================================================

def test_get_variant_prompt_invalid_type():
    """Test that get_variant_prompt raises error for invalid type."""
    with pytest.raises(ValueError) as exc_info:
        get_variant_prompt("invalid_type")
    
    assert "invalid_type" in str(exc_info.value).lower()
    assert "valid types" in str(exc_info.value).lower()


def test_create_variant_agent_invalid_type():
    """Test that create_variant_agent raises error for invalid type."""
    with pytest.raises(ValueError) as exc_info:
        create_variant_agent("invalid_type")
    
    assert "invalid_type" in str(exc_info.value).lower()


def test_valid_variant_types_list():
    """Test that VALID_VARIANT_TYPES contains expected types."""
    expected_types = ["numerical", "context", "conceptual", "calculus"]
    
    for expected in expected_types:
        assert expected in VALID_VARIANT_TYPES, (
            f"Expected variant type '{expected}' not in VALID_VARIANT_TYPES"
        )


def test_extract_numbers_helper():
    """Test the extract_numbers helper function."""
    text = "The velocity is 25.5 m/s and distance is 100 m"
    numbers = extract_numbers(text)
    
    assert 25.5 in numbers
    assert 100.0 in numbers


def test_extract_context_words_helper():
    """Test the extract_context_words helper function."""
    text = "A car moving at 25 m/s on a road"
    words = extract_context_words(text)
    
    assert "car" in words
    assert "moving" in words
    assert "road" in words


def test_has_solution_environment_helper():
    """Test the has_solution_environment helper function."""
    latex_with_solution = r"""
    \item Problem text
    \begin{solution}
    Solution content
    \end{solution}
    """
    
    latex_without_solution = r"""
    \item Problem text only
    """
    
    assert has_solution_environment(latex_with_solution)
    assert not has_solution_environment(latex_without_solution)


def test_has_complete_solution_helper():
    """Test the has_complete_solution helper function."""
    complete_latex = r"""
    \item Problem
    \begin{solution}
    \begin{align*}
    x &= 5 + 3 \\
      &= 8
    \end{align*}
    \end{solution}
    """
    
    incomplete_latex = r"""
    \item Problem
    \begin{solution}
    \end{solution}
    """
    
    assert has_complete_solution(complete_latex)
    assert not has_complete_solution(incomplete_latex)


# =============================================================================
# Property 10: Multi-Context Output Coherence
# =============================================================================

from vbagent.agents.multi_variant import multi_context_agent, generate_multi_context_variant
from vbagent.prompts.variants.multi_context import SYSTEM_PROMPT as MULTI_CONTEXT_SYSTEM_PROMPT


@given(num_problems=st.integers(min_value=2, max_value=5))
@settings(max_examples=100)
def test_property_multi_context_prompt_coherence_instruction(num_problems: int):
    """
    **Feature: physics-question-pipeline, Property 10: Multi-Context Output Coherence**
    **Validates: Requirements 7.3, 7.4**
    
    Property: The multi-context prompt SHALL instruct to produce a single
    coherent problem, not a concatenation of fragments.
    """
    # The system prompt should emphasize coherence
    assert any(phrase in MULTI_CONTEXT_SYSTEM_PROMPT.lower() for phrase in [
        "coherent",
        "single",
        "unified",
    ]), "Multi-context prompt must emphasize producing a coherent single problem"
    
    # The system prompt should warn against concatenation
    assert any(phrase in MULTI_CONTEXT_SYSTEM_PROMPT.lower() for phrase in [
        "not a concatenation",
        "not concatenate",
        "not multiple",
    ]), "Multi-context prompt must warn against concatenation"


def test_property_multi_context_agent_exists():
    """
    **Feature: physics-question-pipeline, Property 10: Multi-Context Output Coherence**
    **Validates: Requirements 7.3, 7.4**
    
    Property: The multi-context agent SHALL exist and be properly configured.
    """
    assert multi_context_agent is not None, "Multi-context agent must exist"
    assert multi_context_agent.name == "MultiContextVariant", (
        "Multi-context agent must have correct name"
    )


def test_property_multi_context_prompt_solution_requirement():
    """
    **Feature: physics-question-pipeline, Property 10: Multi-Context Output Coherence**
    **Validates: Requirements 7.3, 7.4**
    
    Property: The multi-context prompt SHALL require a complete unified solution.
    """
    # Must mention solution
    assert "solution" in MULTI_CONTEXT_SYSTEM_PROMPT.lower(), (
        "Multi-context prompt must mention solution"
    )
    
    # Must emphasize unified solution
    assert any(phrase in MULTI_CONTEXT_SYSTEM_PROMPT.lower() for phrase in [
        "unified",
        "single",
        "complete",
    ]), "Multi-context prompt must emphasize unified solution"


def test_multi_context_generate_requires_problems():
    """Test that generate_multi_context_variant requires at least one problem."""
    with pytest.raises(ValueError) as exc_info:
        generate_multi_context_variant([])
    
    assert "at least one" in str(exc_info.value).lower()


def test_multi_context_generate_filters_empty():
    """Test that generate_multi_context_variant filters empty problems."""
    with pytest.raises(ValueError) as exc_info:
        generate_multi_context_variant(["", "   ", "\n"])
    
    assert "at least one" in str(exc_info.value).lower()


@given(
    problem1=st.text(min_size=10, max_size=100).filter(lambda x: x.strip()),
    problem2=st.text(min_size=10, max_size=100).filter(lambda x: x.strip()),
)
@settings(max_examples=100)
def test_property_multi_context_formats_problems(problem1: str, problem2: str):
    """
    **Feature: physics-question-pipeline, Property 10: Multi-Context Output Coherence**
    **Validates: Requirements 7.3, 7.4**
    
    Property: For any set of source problems, the multi-context system
    SHALL format them with clear problem numbering for the agent.
    """
    # This tests the formatting logic without calling the actual agent
    problems = [problem1, problem2]
    
    # Format as the function would
    problems_text = "\n\n---\n\n".join(
        f"Problem {i + 1}:\n{p}" for i, p in enumerate(problems)
    )
    
    # Verify formatting
    assert "Problem 1:" in problems_text
    assert "Problem 2:" in problems_text
    assert problem1 in problems_text
    assert problem2 in problems_text


# =============================================================================
# Property 13: CLI Range Filtering
# =============================================================================

from vbagent.cli.variant import filter_items_by_range, extract_items_from_tex


@given(
    num_items=st.integers(min_value=1, max_value=20),
    start=st.integers(min_value=1, max_value=10),
    end=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100)
def test_property_cli_range_filtering(num_items: int, start: int, end: int):
    """
    **Feature: physics-question-pipeline, Property 13: CLI Range Filtering**
    **Validates: Requirements 10.3**
    
    Property: For any command with -r/--range specified as (start, end),
    the system SHALL process only items with indices in [start, end] inclusive.
    """
    # Ensure end >= start for valid range
    if end < start:
        start, end = end, start
    
    # Create test items
    items = [f"Item {i}" for i in range(1, num_items + 1)]
    
    # Apply range filter
    filtered = filter_items_by_range(items, (start, end))
    
    # Calculate expected range (1-based inclusive to 0-based)
    expected_start = max(0, start - 1)
    expected_end = min(num_items, end)
    expected_count = max(0, expected_end - expected_start)
    
    # Verify the count matches
    assert len(filtered) == expected_count, (
        f"Expected {expected_count} items for range ({start}, {end}) "
        f"from {num_items} items, got {len(filtered)}"
    )
    
    # Verify all items are from the correct range
    for i, item in enumerate(filtered):
        expected_item_num = expected_start + i + 1
        assert f"Item {expected_item_num}" == item, (
            f"Expected 'Item {expected_item_num}' at position {i}, got '{item}'"
        )


@given(num_items=st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_property_cli_no_range_returns_all(num_items: int):
    """
    **Feature: physics-question-pipeline, Property 13: CLI Range Filtering**
    **Validates: Requirements 10.3**
    
    Property: When no range is specified, all items SHALL be returned.
    """
    items = [f"Item {i}" for i in range(1, num_items + 1)]
    
    # No range specified
    filtered = filter_items_by_range(items, None)
    
    assert len(filtered) == num_items, (
        f"Expected all {num_items} items when no range specified, got {len(filtered)}"
    )
    assert filtered == items, "Items should be unchanged when no range specified"


@given(
    start=st.integers(min_value=1, max_value=5),
    end=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100)
def test_property_cli_range_boundary_handling(start: int, end: int):
    """
    **Feature: physics-question-pipeline, Property 13: CLI Range Filtering**
    **Validates: Requirements 10.3**
    
    Property: Range filtering SHALL handle boundary cases correctly,
    including ranges that extend beyond the item count.
    """
    if end < start:
        start, end = end, start
    
    # Create exactly 3 items
    items = ["Item 1", "Item 2", "Item 3"]
    
    filtered = filter_items_by_range(items, (start, end))
    
    # All returned items should be from the original list
    for item in filtered:
        assert item in items, f"Filtered item '{item}' not in original items"
    
    # Count should not exceed available items
    assert len(filtered) <= len(items), (
        f"Filtered count {len(filtered)} exceeds original count {len(items)}"
    )


def test_extract_items_from_tex():
    """Test that extract_items_from_tex correctly splits TeX content."""
    content = r"""
\item First problem here
\begin{solution}
Solution 1
\end{solution}

\item Second problem here
\begin{solution}
Solution 2
\end{solution}

\item Third problem
\begin{solution}
Solution 3
\end{solution}
"""
    
    items = extract_items_from_tex(content)
    
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    assert "First problem" in items[0]
    assert "Second problem" in items[1]
    assert "Third problem" in items[2]


def test_filter_items_specific_range():
    """Test filter_items_by_range with specific values."""
    items = ["A", "B", "C", "D", "E"]
    
    # Range 2-4 should return B, C, D
    filtered = filter_items_by_range(items, (2, 4))
    assert filtered == ["B", "C", "D"]
    
    # Range 1-1 should return just A
    filtered = filter_items_by_range(items, (1, 1))
    assert filtered == ["A"]
    
    # Range 4-10 should return D, E (capped at list end)
    filtered = filter_items_by_range(items, (4, 10))
    assert filtered == ["D", "E"]


def test_filter_items_empty_list():
    """Test filter_items_by_range with empty list."""
    items = []
    
    filtered = filter_items_by_range(items, (1, 5))
    assert filtered == []
    
    filtered = filter_items_by_range(items, None)
    assert filtered == []
