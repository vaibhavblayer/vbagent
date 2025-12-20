"""Property tests for CLI process command and output persistence.

Tests for:
- Property 14: CLI Output Persistence
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.cli.process import (
    filter_items_by_range,
    extract_items_from_tex,
    extract_problem_solution,
    save_pipeline_result,
)
from vbagent.models.pipeline import PipelineResult
from vbagent.models.classification import ClassificationResult
from vbagent.models.idea import IdeaResult


# =============================================================================
# Test Data Strategies
# =============================================================================

# Strategy for valid file names (alphanumeric with underscores)
filename_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
    min_size=1,
    max_size=20,
).filter(lambda x: x and not x.startswith("_"))

# Strategy for valid directory names
dirname_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
    min_size=1,
    max_size=15,
).filter(lambda x: x and not x.startswith("_"))

# Strategy for LaTeX content
latex_content_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 \\{}[]()=+-*/^_$"),
    min_size=10,
    max_size=200,
)


def create_test_classification() -> ClassificationResult:
    """Create a test classification result."""
    return ClassificationResult(
        question_type="mcq_sc",
        difficulty="medium",
        topic="mechanics",
        subtopic="kinematics",
        has_diagram=False,
        diagram_type=None,
        num_options=4,
        estimated_marks=4,
        key_concepts=["velocity", "acceleration"],
        requires_calculus=False,
        confidence=0.95,
    )


def create_test_ideas() -> IdeaResult:
    """Create a test idea result."""
    return IdeaResult(
        concepts=["Newton's laws", "kinematics"],
        formulas=["v = u + at", "s = ut + 0.5at^2"],
        techniques=["substitution", "algebraic manipulation"],
        difficulty_factors=["multi-step calculation"],
    )


def create_test_pipeline_result(
    source_path: str = "test.png",
    latex: str = r"\item Test problem\n\begin{solution}\nSolution\n\end{solution}",
    tikz_code: str | None = None,
    ideas: IdeaResult | None = None,
    alternate_solutions: list[str] | None = None,
    variants: dict[str, str] | None = None,
) -> PipelineResult:
    """Create a test pipeline result."""
    return PipelineResult(
        source_path=source_path,
        classification=create_test_classification(),
        latex=latex,
        tikz_code=tikz_code,
        ideas=ideas,
        alternate_solutions=alternate_solutions or [],
        variants=variants or {},
    )


# =============================================================================
# Property 14: CLI Output Persistence
# =============================================================================

@given(dirname=dirname_strategy)
@settings(max_examples=100)
def test_property_cli_output_persistence_creates_directory(dirname: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, the system SHALL
    create the output directory if it doesn't exist.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        # Directory should not exist initially
        assert not output_dir.exists(), "Output directory should not exist initially"
        
        # Create a minimal pipeline result
        result = create_test_pipeline_result()
        
        # Save the result
        saved_files = save_pipeline_result(result, output_dir)
        
        # Directory should now exist
        assert output_dir.exists(), "Output directory should be created"
        assert output_dir.is_dir(), "Output path should be a directory"


@given(
    dirname=dirname_strategy,
    latex_content=latex_content_strategy,
)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_latex(dirname: str, latex_content: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, the LaTeX result
    SHALL be written to a file in the output directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        result = create_test_pipeline_result(latex=latex_content)
        saved_files = save_pipeline_result(result, output_dir)
        
        # LaTeX file should be saved
        assert "latex" in saved_files, "LaTeX file should be in saved files"
        
        latex_path = Path(saved_files["latex"])
        assert latex_path.exists(), "LaTeX file should exist"
        
        # Content should be saved (formatting may adjust whitespace)
        saved_content = latex_path.read_text()
        # The formatter may strip trailing whitespace, so compare stripped versions
        assert saved_content.strip() == latex_content.strip(), "Saved LaTeX content should match original (ignoring trailing whitespace)"


@given(dirname=dirname_strategy)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_classification(dirname: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, the classification
    result SHALL be written to a JSON file in the output directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        result = create_test_pipeline_result()
        saved_files = save_pipeline_result(result, output_dir)
        
        # Classification file should be saved
        assert "classification" in saved_files, "Classification file should be in saved files"
        
        class_path = Path(saved_files["classification"])
        assert class_path.exists(), "Classification file should exist"
        assert class_path.suffix == ".json", "Classification should be JSON"
        
        # Should be valid JSON
        import json
        content = json.loads(class_path.read_text())
        assert "question_type" in content, "Classification should have question_type"
        assert "difficulty" in content, "Classification should have difficulty"


@given(dirname=dirname_strategy)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_tikz_when_present(dirname: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, if TikZ code is
    generated, it SHALL be written to a file in the output directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        tikz_code = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"
        result = create_test_pipeline_result(tikz_code=tikz_code)
        saved_files = save_pipeline_result(result, output_dir)
        
        # TikZ file should be saved
        assert "tikz" in saved_files, "TikZ file should be in saved files"
        
        tikz_path = Path(saved_files["tikz"])
        assert tikz_path.exists(), "TikZ file should exist"
        
        # Content should match
        saved_content = tikz_path.read_text()
        assert saved_content == tikz_code, "Saved TikZ should match original"


@given(dirname=dirname_strategy)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_ideas_when_present(dirname: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, if ideas are
    extracted, they SHALL be written to a JSON file in the output directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        ideas = create_test_ideas()
        result = create_test_pipeline_result(ideas=ideas)
        saved_files = save_pipeline_result(result, output_dir)
        
        # Ideas file should be saved
        assert "ideas" in saved_files, "Ideas file should be in saved files"
        
        ideas_path = Path(saved_files["ideas"])
        assert ideas_path.exists(), "Ideas file should exist"
        assert ideas_path.suffix == ".json", "Ideas should be JSON"
        
        # Should be valid JSON with expected fields
        import json
        content = json.loads(ideas_path.read_text())
        assert "concepts" in content, "Ideas should have concepts"
        assert "formulas" in content, "Ideas should have formulas"


@given(
    dirname=dirname_strategy,
    variant_type=st.sampled_from(["numerical", "context", "conceptual", "calculus"]),
)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_variants(dirname: str, variant_type: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, if variants are
    generated, each variant SHALL be written to a separate file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        variant_latex = r"\item Variant problem\n\begin{solution}\nVariant solution\n\end{solution}"
        variants = {variant_type: variant_latex}
        result = create_test_pipeline_result(variants=variants)
        saved_files = save_pipeline_result(result, output_dir)
        
        # Variant file should be saved
        variant_key = f"variant_{variant_type}"
        assert variant_key in saved_files, f"Variant file for {variant_type} should be in saved files"
        
        variant_path = Path(saved_files[variant_key])
        assert variant_path.exists(), f"Variant file for {variant_type} should exist"
        
        # Content should match
        saved_content = variant_path.read_text()
        assert saved_content == variant_latex, "Saved variant should match original"


@given(dirname=dirname_strategy)
@settings(max_examples=100)
def test_property_cli_output_persistence_saves_full_result(dirname: str):
    """
    **Feature: physics-question-pipeline, Property 14: CLI Output Persistence**
    **Validates: Requirements 10.8**
    
    Property: For any command with -o/--output specified, the complete
    pipeline result SHALL be written to a JSON file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / dirname
        
        result = create_test_pipeline_result(
            ideas=create_test_ideas(),
            variants={"numerical": "variant content"},
        )
        saved_files = save_pipeline_result(result, output_dir)
        
        # Full result file should be saved
        assert "full_result" in saved_files, "Full result file should be in saved files"
        
        result_path = Path(saved_files["full_result"])
        assert result_path.exists(), "Full result file should exist"
        assert result_path.suffix == ".json", "Full result should be JSON"
        
        # Should be valid JSON with all fields
        import json
        content = json.loads(result_path.read_text())
        assert "source_path" in content
        assert "classification" in content
        assert "latex" in content
        assert "variants" in content


# =============================================================================
# Additional Unit Tests for Process Module
# =============================================================================

def test_extract_items_from_tex_basic():
    """Test basic item extraction from TeX content."""
    content = r"""
\item First problem
\begin{solution}
Solution 1
\end{solution}

\item Second problem
\begin{solution}
Solution 2
\end{solution}
"""
    items = extract_items_from_tex(content)
    
    assert len(items) == 2
    assert "First problem" in items[0]
    assert "Second problem" in items[1]


def test_extract_items_from_tex_empty():
    """Test item extraction from empty content."""
    items = extract_items_from_tex("")
    assert items == []


def test_extract_items_from_tex_no_items():
    """Test item extraction from content without items."""
    content = "Just some text without any items"
    items = extract_items_from_tex(content)
    assert items == []


def test_filter_items_by_range_basic():
    """Test basic range filtering."""
    items = ["A", "B", "C", "D", "E"]
    
    # Range 2-4 (1-based inclusive)
    filtered = filter_items_by_range(items, (2, 4))
    assert filtered == ["B", "C", "D"]


def test_filter_items_by_range_none():
    """Test that None range returns all items."""
    items = ["A", "B", "C"]
    filtered = filter_items_by_range(items, None)
    assert filtered == items


def test_filter_items_by_range_out_of_bounds():
    """Test range filtering with out-of-bounds values."""
    items = ["A", "B", "C"]
    
    # Range extends beyond list
    filtered = filter_items_by_range(items, (2, 10))
    assert filtered == ["B", "C"]
    
    # Range starts beyond list
    filtered = filter_items_by_range(items, (10, 15))
    assert filtered == []


def test_extract_problem_solution_basic():
    """Test basic problem/solution extraction."""
    content = r"""
\item A ball is thrown upward with velocity 20 m/s.
\begin{solution}
Using v = u - gt, we get t = 2s.
\end{solution}
"""
    problem, solution = extract_problem_solution(content)
    
    assert "ball is thrown" in problem
    assert "v = u - gt" in solution


def test_extract_problem_solution_no_solution():
    """Test extraction when no solution environment exists."""
    content = r"\item Just a problem without solution"
    problem, solution = extract_problem_solution(content)
    
    assert "Just a problem" in problem
    assert solution == ""


def test_save_pipeline_result_creates_all_files():
    """Test that save_pipeline_result creates all expected files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        
        result = create_test_pipeline_result(
            tikz_code=r"\begin{tikzpicture}\end{tikzpicture}",
            ideas=create_test_ideas(),
            alternate_solutions=["Alt solution 1", "Alt solution 2"],
            variants={"numerical": "num variant", "context": "ctx variant"},
        )
        
        saved_files = save_pipeline_result(result, output_dir)
        
        # Check all expected files
        assert "classification" in saved_files
        assert "latex" in saved_files
        assert "tikz" in saved_files
        assert "ideas" in saved_files
        assert "alternates" in saved_files
        assert "variant_numerical" in saved_files
        assert "variant_context" in saved_files
        assert "full_result" in saved_files
        
        # Verify all files exist
        for file_path in saved_files.values():
            assert Path(file_path).exists(), f"File should exist: {file_path}"


def test_save_pipeline_result_alternates_combined():
    """Test that alternate solutions are combined with separators."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        
        alternates = ["Solution A", "Solution B", "Solution C"]
        result = create_test_pipeline_result(alternate_solutions=alternates)
        
        saved_files = save_pipeline_result(result, output_dir)
        
        alt_path = Path(saved_files["alternates"])
        content = alt_path.read_text()
        
        # All solutions should be present
        for alt in alternates:
            assert alt in content
        
        # Separators should be present
        assert "% --- Alternate Solution ---" in content


def test_save_pipeline_result_nested_directory():
    """Test that save_pipeline_result creates nested directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "deep" / "nested" / "output"
        
        result = create_test_pipeline_result()
        saved_files = save_pipeline_result(result, output_dir)
        
        assert output_dir.exists()
        assert (output_dir / "classification.json").exists()


# =============================================================================
# Tests for Organized Directory Structure
# =============================================================================

from vbagent.cli.process import save_pipeline_result_organized, get_base_name


def test_get_base_name_from_image():
    """Test extracting base name from image path."""
    assert get_base_name("images/problem_1.png") == "problem_1"
    assert get_base_name("path/to/Question_5.jpg") == "Question_5"
    assert get_base_name("test.tex") == "test"


def test_save_organized_creates_scans_directory():
    """Test that organized save creates scans directory with correct file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(source_path="images/problem_1.png")
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        assert "scan" in saved
        scan_path = Path(saved["scan"])
        assert scan_path.exists()
        assert scan_path.parent.name == "scans"
        assert scan_path.name == "problem_1.tex"


def test_save_organized_creates_classifications_directory():
    """Test that organized save creates classifications directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(source_path="images/problem_1.png")
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        assert "classification" in saved
        class_path = Path(saved["classification"])
        assert class_path.exists()
        assert class_path.parent.name == "classifications"
        assert class_path.name == "problem_1.json"


def test_save_organized_creates_variants_subdirectories():
    """Test that organized save creates variant type subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        variants = {
            "numerical": "numerical variant content",
            "context": "context variant content",
        }
        result = create_test_pipeline_result(
            source_path="images/problem_1.png",
            variants=variants,
        )
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        # Check numerical variant
        assert "variant_numerical" in saved
        num_path = Path(saved["variant_numerical"])
        assert num_path.exists()
        assert num_path.parent.name == "numerical"
        assert num_path.parent.parent.name == "variants"
        assert num_path.name == "problem_1.tex"
        
        # Check context variant
        assert "variant_context" in saved
        ctx_path = Path(saved["variant_context"])
        assert ctx_path.exists()
        assert ctx_path.parent.name == "context"
        assert ctx_path.parent.parent.name == "variants"
        assert ctx_path.name == "problem_1.tex"


def test_save_organized_creates_alternates_directory():
    """Test that organized save creates alternates directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(
            source_path="images/problem_1.png",
            alternate_solutions=["Alt 1", "Alt 2"],
        )
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        assert "alternates" in saved
        alt_path = Path(saved["alternates"])
        assert alt_path.exists()
        assert alt_path.parent.name == "alternates"
        assert alt_path.name == "problem_1.tex"


def test_save_organized_creates_ideas_directory():
    """Test that organized save creates ideas directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(
            source_path="images/problem_1.png",
            ideas=create_test_ideas(),
        )
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        assert "ideas" in saved
        ideas_path = Path(saved["ideas"])
        assert ideas_path.exists()
        assert ideas_path.parent.name == "ideas"
        assert ideas_path.name == "problem_1.json"


def test_save_organized_creates_tikz_directory():
    """Test that organized save creates tikz directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(
            source_path="images/problem_1.png",
            tikz_code=r"\begin{tikzpicture}\end{tikzpicture}",
        )
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        assert "tikz" in saved
        tikz_path = Path(saved["tikz"])
        assert tikz_path.exists()
        assert tikz_path.parent.name == "tikz"
        assert tikz_path.name == "problem_1.tex"


def test_save_organized_full_structure():
    """Test complete organized directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "agentic"
        
        result = create_test_pipeline_result(
            source_path="images/problem_1.png",
            tikz_code=r"\begin{tikzpicture}\end{tikzpicture}",
            ideas=create_test_ideas(),
            alternate_solutions=["Alt solution"],
            variants={
                "numerical": "num",
                "context": "ctx",
                "conceptual": "con",
                "calculus": "calc",
            },
        )
        saved = save_pipeline_result_organized(result, base_dir, "problem_1")
        
        # Verify directory structure
        assert (base_dir / "scans" / "problem_1.tex").exists()
        assert (base_dir / "classifications" / "problem_1.json").exists()
        assert (base_dir / "tikz" / "problem_1.tex").exists()
        assert (base_dir / "ideas" / "problem_1.json").exists()
        assert (base_dir / "alternates" / "problem_1.tex").exists()
        assert (base_dir / "variants" / "numerical" / "problem_1.tex").exists()
        assert (base_dir / "variants" / "context" / "problem_1.tex").exists()
        assert (base_dir / "variants" / "conceptual" / "problem_1.tex").exists()
        assert (base_dir / "variants" / "calculus" / "problem_1.tex").exists()


# =============================================================================
# Tests for Image Range Generation
# =============================================================================

from vbagent.cli.process import generate_image_paths_from_range


def test_generate_image_paths_underscore_pattern():
    """Test image path generation with underscore pattern."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test images
        for i in range(1, 6):
            (Path(tmpdir) / f"Problem_{i}.png").touch()
        
        template = str(Path(tmpdir) / "Problem_3.png")
        paths = generate_image_paths_from_range(template, (1, 5))
        
        assert len(paths) == 5
        assert all("Problem_" in p for p in paths)
        assert "Problem_1.png" in paths[0]
        assert "Problem_5.png" in paths[4]


def test_generate_image_paths_no_separator():
    """Test image path generation without separator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test images
        for i in range(1, 4):
            (Path(tmpdir) / f"question{i}.png").touch()
        
        template = str(Path(tmpdir) / "question2.png")
        paths = generate_image_paths_from_range(template, (1, 3))
        
        assert len(paths) == 3
        assert "question1.png" in paths[0]
        assert "question3.png" in paths[2]


def test_generate_image_paths_zero_padded():
    """Test image path generation with zero-padded numbers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test images with zero padding
        for i in range(1, 4):
            (Path(tmpdir) / f"img_{i:02d}.png").touch()
        
        template = str(Path(tmpdir) / "img_02.png")
        paths = generate_image_paths_from_range(template, (1, 3))
        
        assert len(paths) == 3
        assert "img_01.png" in paths[0]
        assert "img_03.png" in paths[2]


def test_generate_image_paths_missing_files():
    """Test that missing files are skipped with warning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only some images
        (Path(tmpdir) / "Problem_1.png").touch()
        (Path(tmpdir) / "Problem_3.png").touch()
        
        template = str(Path(tmpdir) / "Problem_1.png")
        paths = generate_image_paths_from_range(template, (1, 3))
        
        # Only existing files should be returned
        assert len(paths) == 2
        assert "Problem_1.png" in paths[0]
        assert "Problem_3.png" in paths[1]


def test_generate_image_paths_no_number():
    """Test that paths without numbers return original path."""
    paths = generate_image_paths_from_range("images/test.png", (1, 5))
    assert paths == ["images/test.png"]


# =============================================================================
# Tests for LaTeX Formatting
# =============================================================================

from vbagent.cli.process import format_latex, insert_tikz_into_latex


def test_insert_tikz_into_latex_basic():
    """Test basic TikZ insertion replacing placeholder."""
    latex = r"""\item A block floats in water.
\begin{center}
    \input{diagram}
\end{center}
\begin{tasks}(2)
\task Option A
\task Option B \ans
\end{tasks}"""
    
    tikz_code = r"""\begin{tikzpicture}
\draw (0,0) rectangle (2,2);
\end{tikzpicture}"""
    
    result = insert_tikz_into_latex(latex, tikz_code)
    
    # Placeholder should be replaced
    assert r"\input{diagram}" not in result
    # TikZ code should be present
    assert r"\draw (0,0) rectangle (2,2)" in result
    # Other content should be preserved
    assert r"\item A block floats in water" in result
    assert r"\task Option A" in result


def test_insert_tikz_into_latex_no_placeholder():
    """Test that LaTeX without placeholder is unchanged."""
    latex = r"""\item A simple problem without diagram.
\begin{tasks}(2)
\task Option A
\task Option B
\end{tasks}"""
    
    tikz_code = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"
    
    result = insert_tikz_into_latex(latex, tikz_code)
    
    # Original should be unchanged
    assert result == latex


def test_insert_tikz_into_latex_wraps_in_center():
    """Test that TikZ code without center env gets wrapped."""
    latex = r"""\item Problem
\begin{center}
    \input{diagram}
\end{center}"""
    
    # TikZ code without center environment
    tikz_code = r"""\begin{tikzpicture}
\draw (0,0) circle (1);
\end{tikzpicture}"""
    
    result = insert_tikz_into_latex(latex, tikz_code)
    
    # Should have center environment
    assert r"\begin{center}" in result
    assert r"\end{center}" in result
    assert r"\draw (0,0) circle (1)" in result


def test_insert_tikz_into_latex_option_diagrams():
    """Test that option diagram definitions are inserted before tasks."""
    latex = r"""\item Which graph shows the correct relationship?
% OPTIONS_DIAGRAMS: 4 options with different curves
\begin{tasks}(2)
    \task \OptionA
    \task \OptionB \ans
    \task \OptionC
    \task \OptionD
\end{tasks}"""
    
    tikz_code = r"""\pgfmathsetmacro{\axisWidth}{2.5}
\def\OptionA{\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}}
\def\OptionB{\begin{tikzpicture}\draw (0,0) -- (1,2);\end{tikzpicture}}
\def\OptionC{\begin{tikzpicture}\draw (0,0) -- (2,1);\end{tikzpicture}}
\def\OptionD{\begin{tikzpicture}\draw (0,0) -- (2,2);\end{tikzpicture}}"""
    
    result = insert_tikz_into_latex(latex, tikz_code)
    
    # Option definitions should be present
    assert r"\def\OptionA" in result
    assert r"\def\OptionB" in result
    # Definitions should come before tasks
    assert result.index(r"\def\OptionA") < result.index(r"\begin{tasks}")
    # OPTIONS_DIAGRAMS comment should be removed
    assert "OPTIONS_DIAGRAMS" not in result
    # Original task content preserved
    assert r"\task \OptionA" in result
    assert r"\task \OptionB \ans" in result


def test_format_latex_basic_indentation():
    """Test that format_latex adds proper indentation to environments."""
    input_latex = r"""\item Test problem
\begin{solution}
\begin{align*}
x &= 1\\
y &= 2
\end{align*}
\end{solution}"""
    
    formatted = format_latex(input_latex)
    lines = formatted.split('\n')
    
    # \item should be at root level
    assert lines[0] == r"\item Test problem"
    # \begin{solution} should be at root level
    assert lines[1] == r"\begin{solution}"
    # Content inside solution should be indented (4 spaces)
    assert lines[2].startswith("    ")  # \begin{align*} indented once
    # Content inside align* should be indented (8 spaces = 2 levels)
    assert "x &= 1" in lines[3]  # Content preserved


def test_format_latex_preserves_content():
    """Test that format_latex preserves all content."""
    input_latex = r"""\item A ball is thrown
\begin{tasks}(2)
\task Option A
\task Option B \ans
\end{tasks}
\begin{solution}
Answer is B
\end{solution}"""
    
    formatted = format_latex(input_latex)
    
    # All content should be preserved
    assert r"\item A ball is thrown" in formatted
    assert r"\task Option A" in formatted
    assert r"\task Option B \ans" in formatted
    assert "Answer is B" in formatted


def test_format_latex_empty_input():
    """Test that format_latex handles empty input."""
    assert format_latex("") == ""
    assert format_latex(None) is None


def test_format_latex_nested_environments():
    """Test formatting with nested environments."""
    input_latex = r"""\begin{center}
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\end{tikzpicture}
\end{center}"""
    
    formatted = format_latex(input_latex)
    lines = formatted.split('\n')
    
    # tikzpicture should be indented inside center
    assert "    " in lines[1]  # \begin{tikzpicture} indented
    assert "        " in lines[2]  # \draw indented twice
