"""Tests for TeX file parsing utilities.

Tests the TeX parsing functions extracted to vbagent/utils/tex_parser.py.
"""

import pytest
from pathlib import Path
from hypothesis import given, strategies as st

from vbagent.utils.tex_parser import (
    parse_tex_file,
    parse_tex_file_with_sections,
    extract_items,
    extract_answer,
)


class TestParseTexFile:
    """Tests for parse_tex_file function."""

    def test_parse_simple_tex_file(self, tmp_path):
        """Test reading simple TeX file content."""
        tex_file = tmp_path / "test.tex"
        content = "\\item Test problem\n\\begin{solution}\nTest solution\n\\end{solution}"
        tex_file.write_text(content)
        
        result = parse_tex_file(str(tex_file))
        assert result == content

    def test_parse_empty_file(self, tmp_path):
        """Test reading empty TeX file."""
        tex_file = tmp_path / "empty.tex"
        tex_file.write_text("")
        
        result = parse_tex_file(str(tex_file))
        assert result == ""

    def test_parse_multiline_file(self, tmp_path):
        """Test reading multiline TeX file."""
        tex_file = tmp_path / "multiline.tex"
        content = "Line 1\nLine 2\nLine 3\nLine 4"
        tex_file.write_text(content)
        
        result = parse_tex_file(str(tex_file))
        assert result == content
        assert result.count('\n') == 3

    def test_parse_file_with_unicode(self, tmp_path):
        """Test reading file with unicode characters."""
        tex_file = tmp_path / "unicode.tex"
        content = "\\item Problem with α, β, γ symbols"
        tex_file.write_text(content, encoding='utf-8')
        
        result = parse_tex_file(str(tex_file))
        assert "α" in result
        assert "β" in result
        assert "γ" in result

    def test_parse_file_not_found(self):
        """Test handling non-existent file."""
        with pytest.raises(FileNotFoundError):
            parse_tex_file("nonexistent.tex")

    def test_parse_file_with_special_chars(self, tmp_path):
        """Test reading file with special LaTeX characters."""
        tex_file = tmp_path / "special.tex"
        content = "\\item $x^2 + y^2 = z^2$ and \\frac{1}{2}"
        tex_file.write_text(content)
        
        result = parse_tex_file(str(tex_file))
        assert "$x^2 + y^2 = z^2$" in result
        assert "\\frac{1}{2}" in result


class TestParseTexFileWithSections:
    """Tests for parse_tex_file_with_sections function."""

    def test_parse_with_problem_and_solution(self, tmp_path):
        """Test extracting problem and solution sections."""
        tex_file = tmp_path / "test.tex"
        content = "\\item This is the problem\n\\begin{solution}\nThis is the solution\n\\end{solution}"
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == "This is the problem"
        assert solution == "This is the solution"

    def test_parse_with_no_solution(self, tmp_path):
        """Test parsing file without solution."""
        tex_file = tmp_path / "test.tex"
        content = "\\item This is the problem"
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == content
        assert solution == ""

    def test_parse_with_multiline_problem(self, tmp_path):
        """Test parsing multiline problem."""
        tex_file = tmp_path / "test.tex"
        content = """\\item This is a problem
        with multiple lines
        and some equations $x = y$
        \\begin{solution}
        Solution here
        \\end{solution}"""
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert "This is a problem" in problem
        assert "multiple lines" in problem
        assert "$x = y$" in problem
        assert solution == "Solution here"

    def test_parse_with_multiline_solution(self, tmp_path):
        """Test parsing multiline solution."""
        tex_file = tmp_path / "test.tex"
        content = """\\item Problem
        \\begin{solution}
        Step 1: First step
        Step 2: Second step
        Step 3: Final answer
        \\end{solution}"""
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == "Problem"
        assert "Step 1" in solution
        assert "Step 2" in solution
        assert "Step 3" in solution

    def test_parse_with_nested_environments(self, tmp_path):
        """Test parsing with nested environments in solution."""
        tex_file = tmp_path / "test.tex"
        content = """\\item Problem
        \\begin{solution}
        \\begin{align}
        x &= 1 \\\\
        y &= 2
        \\end{align}
        \\end{solution}"""
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == "Problem"
        assert "\\begin{align}" in solution
        assert "\\end{align}" in solution

    def test_parse_with_whitespace(self, tmp_path):
        """Test parsing with extra whitespace."""
        tex_file = tmp_path / "test.tex"
        content = """\\item   Problem with spaces   
        
        \\begin{solution}
        
        Solution with spaces
        
        \\end{solution}"""
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        # Should strip whitespace
        assert problem == "Problem with spaces"
        assert solution == "Solution with spaces"

    def test_parse_empty_solution(self, tmp_path):
        """Test parsing with empty solution environment."""
        tex_file = tmp_path / "test.tex"
        content = "\\item Problem\n\\begin{solution}\n\\end{solution}"
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == "Problem"
        assert solution == ""


class TestExtractItems:
    """Tests for extract_items function."""

    def test_extract_multiple_items(self):
        """Test extracting multiple items from content."""
        content = """
        \\item First problem
        Some content
        \\item Second problem
        More content
        \\item Third problem
        """
        
        items = extract_items(content)
        assert len(items) == 3
        assert "First problem" in items[0]
        assert "Second problem" in items[1]
        assert "Third problem" in items[2]

    def test_extract_items_empty(self):
        """Test extracting items from empty content."""
        items = extract_items("")
        assert len(items) == 0

    def test_extract_items_no_items(self):
        """Test extracting items from content without items."""
        content = "Some content without items"
        items = extract_items(content)
        assert len(items) == 0

    def test_extract_single_item(self):
        """Test extracting single item."""
        content = "\\item Only one problem here"
        items = extract_items(content)
        assert len(items) == 1
        assert "Only one problem" in items[0]

    def test_extract_items_with_solutions(self):
        """Test extracting items that contain solutions."""
        content = """
        \\item Problem 1
        \\begin{solution}
        Solution 1
        \\end{solution}
        \\item Problem 2
        \\begin{solution}
        Solution 2
        \\end{solution}
        """
        
        items = extract_items(content)
        assert len(items) == 2
        assert "Problem 1" in items[0]
        assert "Solution 1" in items[0]
        assert "Problem 2" in items[1]
        assert "Solution 2" in items[1]

    def test_extract_items_with_nested_environments(self):
        """Test extracting items with nested environments."""
        content = """
        \\item Problem with equation
        \\begin{align}
        x &= 1
        \\end{align}
        \\item Another problem
        """
        
        items = extract_items(content)
        assert len(items) == 2
        assert "\\begin{align}" in items[0]

    def test_extract_items_preserves_content(self):
        """Test that extraction preserves all content between items."""
        content = """
        \\item Problem 1
        Line 1
        Line 2
        Line 3
        \\item Problem 2
        """
        
        items = extract_items(content)
        assert len(items) == 2
        assert "Line 1" in items[0]
        assert "Line 2" in items[0]
        assert "Line 3" in items[0]

    def test_extract_items_with_itemize(self):
        """Test extracting items that contain itemize environments."""
        content = """
        \\item Problem with list
        \\begin{itemize}
        \\item Sub-item 1
        \\item Sub-item 2
        \\end{itemize}
        \\item Next problem
        """
        
        items = extract_items(content)
        # Should extract main items, not sub-items
        assert len(items) == 2
        assert "Sub-item 1" in items[0]


class TestExtractAnswer:
    """Tests for extract_answer function."""

    def test_extract_mcq_single_answer(self):
        """Test extracting single MCQ answer."""
        content = """
        \\begin{tasks}(4)
        \\task Option A
        \\task Option B \\ans
        \\task Option C
        \\task Option D
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "B"

    def test_extract_mcq_multiple_answers(self):
        """Test extracting multiple correct MCQ answers."""
        content = """
        \\begin{tasks}(4)
        \\task Option A \\ans
        \\task Option B
        \\task Option C \\ans
        \\task Option D
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "A,C"

    def test_extract_mcq_first_option(self):
        """Test extracting answer when first option is correct."""
        content = """
        \\begin{tasks}(4)
        \\task Option A \\ans
        \\task Option B
        \\task Option C
        \\task Option D
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "A"

    def test_extract_mcq_last_option(self):
        """Test extracting answer when last option is correct."""
        content = """
        \\begin{tasks}(4)
        \\task Option A
        \\task Option B
        \\task Option C
        \\task Option D \\ans
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "D"

    def test_extract_integer_answer(self):
        """Test extracting integer answer."""
        content = "The answer is \\ansint{42}"
        answer = extract_answer(content)
        assert answer == "42"

    def test_extract_integer_answer_with_spaces(self):
        """Test extracting integer answer with spaces."""
        content = "The answer is \\ansint{ 42 }"
        answer = extract_answer(content)
        assert answer == "42"

    def test_extract_negative_integer(self):
        """Test extracting negative integer answer."""
        content = "The answer is \\ansint{-42}"
        answer = extract_answer(content)
        assert answer == "-42"

    def test_extract_answer_none(self):
        """Test extracting answer when none present."""
        content = "Some problem without answer markers"
        answer = extract_answer(content)
        assert answer is None

    def test_extract_answer_with_comments(self):
        """Test extracting answer with comments in content."""
        content = """
        \\begin{tasks}(4)
        \\task Option A % This is wrong
        \\task Option B \\ans % This is correct
        \\task Option C
        \\task Option D
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "B"

    def test_extract_answer_ignores_commented_ans(self):
        """Test that commented \\ans markers are ignored."""
        content = """
        \\begin{tasks}(4)
        \\task Option A % \\ans (commented out)
        \\task Option B \\ans
        \\task Option C
        \\task Option D
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        # Should only find B, not A
        assert answer == "B"

    def test_extract_answer_no_tasks_environment(self):
        """Test extracting answer without tasks environment."""
        content = "\\task Option A \\ans"
        answer = extract_answer(content)
        assert answer is None

    def test_extract_answer_empty_tasks(self):
        """Test extracting answer from empty tasks environment."""
        content = "\\begin{tasks}(4)\\end{tasks}"
        answer = extract_answer(content)
        assert answer is None

    def test_extract_answer_all_correct(self):
        """Test extracting when all options are marked correct."""
        content = """
        \\begin{tasks}(4)
        \\task Option A \\ans
        \\task Option B \\ans
        \\task Option C \\ans
        \\task Option D \\ans
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "A,B,C,D"

    def test_extract_answer_with_newlines(self):
        """Test extracting answer with various newline patterns."""
        content = """
        \\begin{tasks}(4)
        
        \\task Option A
        
        \\task Option B
        \\ans
        
        \\task Option C
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        assert answer == "B"

    def test_extract_integer_in_context(self):
        """Test extracting integer answer within problem context."""
        content = """
        Calculate the value of x.
        
        Given: x + 5 = 10
        
        \\ansint{5}
        """
        
        answer = extract_answer(content)
        assert answer == "5"

    def test_extract_answer_priority(self):
        """Test that integer answer takes priority over MCQ."""
        content = """
        \\ansint{42}
        \\begin{tasks}(4)
        \\task Option A \\ans
        \\task Option B
        \\end{tasks}
        """
        
        answer = extract_answer(content)
        # Integer should be found first
        assert answer == "42"


class TestTexParserIntegration:
    """Integration tests for TeX parser utilities."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: parse file, extract sections, extract answer."""
        tex_file = tmp_path / "problem.tex"
        content = """\\item Calculate the sum.
        
        \\begin{tasks}(4)
        \\task 10
        \\task 15 \\ans
        \\task 20
        \\task 25
        \\end{tasks}
        
        \\begin{solution}
        The sum is 5 + 10 = 15.
        \\end{solution}"""
        
        tex_file.write_text(content)
        
        # Parse file
        full_content = parse_tex_file(str(tex_file))
        assert "Calculate the sum" in full_content
        
        # Extract sections
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert "Calculate the sum" in problem
        assert "The sum is 5 + 10 = 15" in solution
        
        # Extract answer
        answer = extract_answer(problem)
        assert answer == "B"

    def test_multiple_problems_workflow(self, tmp_path):
        """Test workflow with multiple problems in one file."""
        tex_file = tmp_path / "problems.tex"
        content = """
        \\item Problem 1
        \\ansint{10}
        
        \\item Problem 2
        \\begin{tasks}(2)
        \\task A \\ans
        \\task B
        \\end{tasks}
        
        \\item Problem 3
        \\ansint{20}
        """
        
        tex_file.write_text(content)
        
        # Parse file
        full_content = parse_tex_file(str(tex_file))
        
        # Extract items
        items = extract_items(full_content)
        assert len(items) == 3
        
        # Extract answers from each item
        answer1 = extract_answer(items[0])
        answer2 = extract_answer(items[1])
        answer3 = extract_answer(items[2])
        
        assert answer1 == "10"
        assert answer2 == "A"
        assert answer3 == "20"

    @given(st.text(min_size=1, max_size=100))
    def test_property_extract_items_preserves_content(self, content):
        """Property: Extracted items should preserve original content."""
        # Add item markers
        marked_content = f"\\item {content}"
        
        items = extract_items(marked_content)
        
        if items:
            # Content should be in the extracted item
            assert content in items[0] or content.strip() in items[0]

    @given(st.integers(min_value=-1000, max_value=1000))
    def test_property_integer_answer_roundtrip(self, value):
        """Property: Integer answers should roundtrip correctly."""
        content = f"\\ansint{{{value}}}"
        
        answer = extract_answer(content)
        
        assert answer == str(value)
