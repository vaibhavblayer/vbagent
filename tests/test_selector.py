"""Property tests for Random Selector.

Tests for random selection count constraint and problem context completeness.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.agents.selector import (
    ProblemContext,
    discover_problems,
    select_random,
    load_problem_context,
)


# =============================================================================
# Strategies for generating test data
# =============================================================================

# Problem IDs - alphanumeric with underscores
problem_id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip() and x[0].isalpha())

# LaTeX content
latex_content_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Zs"),
        blacklist_characters="\r\x00",
    ),
    min_size=1,
    max_size=200,
).filter(lambda x: x.strip())

# Variant types
variant_type_strategy = st.sampled_from(["numerical", "context", "conceptual", "conceptual_calculus"])


def create_test_output_dir(
    tmpdir: str,
    problem_ids: list[str],
    variant_types: list[str] | None = None,
) -> Path:
    """Create a test output directory structure with problems.
    
    Args:
        tmpdir: Temporary directory path
        problem_ids: List of problem IDs to create
        variant_types: Optional list of variant types to create for each problem
        
    Returns:
        Path to the output directory
    """
    output_dir = Path(tmpdir) / "agentic"
    scans_dir = output_dir / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    
    for problem_id in problem_ids:
        # Create main LaTeX file
        latex_path = scans_dir / f"{problem_id}.tex"
        latex_path.write_text(f"% Problem {problem_id}\n\\item Test problem content")
        
        # Create variants if specified
        if variant_types:
            for variant_type in variant_types:
                variant_dir = output_dir / "variants" / variant_type
                variant_dir.mkdir(parents=True, exist_ok=True)
                variant_path = variant_dir / f"{problem_id}.tex"
                variant_path.write_text(f"% Variant {variant_type} for {problem_id}\n\\item Variant content")
    
    return output_dir


# =============================================================================
# Property 1: Random Selection Count Constraint
# =============================================================================

@given(
    problem_ids=st.lists(problem_id_strategy, min_size=0, max_size=20, unique=True),
    requested_count=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=100)
def test_property_random_selection_count_constraint(
    problem_ids: list[str], requested_count: int
):
    """
    **Feature: qa-review-agent, Property 1: Random Selection Count Constraint**
    **Validates: Requirements 1.1, 1.3**
    
    Property: For any output directory with N problems and any requested count M,
    the Random Selector SHALL return exactly min(N, M) problems.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test output directory with problems
        output_dir = create_test_output_dir(tmpdir, problem_ids)
        
        # Select random problems
        selected = select_random(str(output_dir), requested_count)
        
        # Property: Should return exactly min(N, M) problems
        expected_count = min(len(problem_ids), requested_count)
        assert len(selected) == expected_count, (
            f"Expected {expected_count} problems, got {len(selected)}. "
            f"Available: {len(problem_ids)}, Requested: {requested_count}"
        )
        
        # Property: All selected problems should be from the available set
        for problem_id in selected:
            assert problem_id in problem_ids, (
                f"Selected problem '{problem_id}' not in available problems"
            )
        
        # Property: No duplicates in selection
        assert len(selected) == len(set(selected)), (
            f"Duplicate problems in selection: {selected}"
        )


# =============================================================================
# Property 2: Problem Context Completeness
# =============================================================================

@given(
    problem_id=problem_id_strategy,
    latex_content=latex_content_strategy,
    variant_types=st.lists(variant_type_strategy, min_size=0, max_size=4, unique=True),
)
@settings(max_examples=100)
def test_property_problem_context_completeness(
    problem_id: str, latex_content: str, variant_types: list[str]
):
    """
    **Feature: qa-review-agent, Property 2: Problem Context Completeness**
    **Validates: Requirements 1.2**
    
    Property: For any problem selected for review, the loaded ProblemContext
    SHALL contain non-empty latex_content and the variants dictionary SHALL
    contain entries for all variant files present in the problem directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "agentic"
        scans_dir = output_dir / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main LaTeX file with specific content
        latex_path = scans_dir / f"{problem_id}.tex"
        latex_path.write_text(latex_content)
        
        # Create variant files
        for variant_type in variant_types:
            variant_dir = output_dir / "variants" / variant_type
            variant_dir.mkdir(parents=True, exist_ok=True)
            variant_path = variant_dir / f"{problem_id}.tex"
            variant_path.write_text(f"% Variant {variant_type}\n\\item Variant content")
        
        # Load problem context
        context = load_problem_context(str(output_dir), problem_id)
        
        # Property: latex_content should be non-empty and match what we wrote
        assert context.latex_content, "latex_content should be non-empty"
        assert context.latex_content == latex_content, (
            f"latex_content mismatch: expected {repr(latex_content)}, "
            f"got {repr(context.latex_content)}"
        )
        
        # Property: variants dictionary should contain entries for all variant files
        assert len(context.variants) == len(variant_types), (
            f"Expected {len(variant_types)} variants, got {len(context.variants)}. "
            f"Expected types: {variant_types}, Got: {list(context.variants.keys())}"
        )
        
        for variant_type in variant_types:
            assert variant_type in context.variants, (
                f"Variant type '{variant_type}' not found in context.variants"
            )
            assert context.variants[variant_type], (
                f"Variant content for '{variant_type}' should be non-empty"
            )
            assert variant_type in context.variant_paths, (
                f"Variant path for '{variant_type}' not found in context.variant_paths"
            )
        
        # Property: problem_id should match
        assert context.problem_id == problem_id
        
        # Property: latex_path should be set
        assert context.latex_path
        assert Path(context.latex_path).exists()


# =============================================================================
# Additional unit tests for edge cases
# =============================================================================

def test_discover_problems_empty_directory():
    """Test discover_problems with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "agentic"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        problems = discover_problems(str(output_dir))
        assert problems == []


def test_discover_problems_no_scans_dir():
    """Test discover_problems when scans directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        problems = discover_problems(tmpdir)
        assert problems == []


def test_select_random_empty_directory():
    """Test select_random with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        selected = select_random(tmpdir, 5)
        assert selected == []


def test_load_problem_context_not_found():
    """Test load_problem_context raises error for missing problem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "agentic"
        scans_dir = output_dir / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        
        with pytest.raises(FileNotFoundError):
            load_problem_context(str(output_dir), "nonexistent_problem")
