"""Tests for LaTeX utility functions.

Tests the clean_latex_output function and other LaTeX utilities
extracted to vbagent/utils/latex.py.
"""

import pytest
from hypothesis import given, strategies as st

from vbagent.utils.latex import (
    clean_latex_output,
    validate_latex_syntax,
    format_latex_for_display,
    extract_preamble,
)


class TestCleanLatexOutput:
    """Tests for clean_latex_output function."""

    def test_clean_latex_code_block(self):
        """Test removing ```latex code blocks."""
        input_latex = "```latex\n\\begin{document}\nContent\n\\end{document}\n```"
        expected = "\\begin{document}\nContent\n\\end{document}"
        assert clean_latex_output(input_latex) == expected

    def test_clean_tex_code_block(self):
        """Test removing ```tex code blocks."""
        input_latex = "```tex\n\\section{Title}\n```"
        expected = "\\section{Title}"
        assert clean_latex_output(input_latex) == expected

    def test_clean_generic_code_block(self):
        """Test removing ``` code blocks without language."""
        input_latex = "```\n\\textbf{Bold}\n```"
        expected = "\\textbf{Bold}"
        assert clean_latex_output(input_latex) == expected

    def test_clean_case_insensitive(self):
        """Test case-insensitive language detection."""
        input_latex = "```LaTeX\n\\item Test\n```"
        expected = "\\item Test"
        assert clean_latex_output(input_latex) == expected

    def test_clean_whitespace(self):
        """Test trimming leading/trailing whitespace."""
        input_latex = "  \\section{Title}  "
        expected = "\\section{Title}"
        assert clean_latex_output(input_latex) == expected

    def test_clean_empty_string(self):
        """Test handling empty string."""
        assert clean_latex_output("") == ""

    def test_clean_none(self):
        """Test handling None."""
        assert clean_latex_output(None) is None

    def test_clean_no_code_blocks(self):
        """Test LaTeX without code blocks."""
        input_latex = "\\begin{document}\nContent\n\\end{document}"
        expected = "\\begin{document}\nContent\n\\end{document}"
        assert clean_latex_output(input_latex) == expected

    def test_clean_multiple_code_blocks(self):
        """Test handling multiple code block markers."""
        input_latex = "```latex\n```\n\\section{Title}\n```"
        # Should remove opening markers and closing marker
        result = clean_latex_output(input_latex)
        assert "```" not in result
        assert "\\section{Title}" in result

    def test_clean_code_block_with_newlines(self):
        """Test code blocks with various newline patterns."""
        input_latex = "```latex\n\n\\begin{document}\n\n```"
        result = clean_latex_output(input_latex)
        assert "```" not in result
        assert "\\begin{document}" in result

    @given(st.text(min_size=1))
    def test_property_no_code_blocks_in_output(self, latex_content):
        """Property: Output should never contain code block markers."""
        # Add code block markers
        input_latex = f"```latex\n{latex_content}\n```"
        result = clean_latex_output(input_latex)
        
        # Result should not contain code block markers
        assert "```latex" not in result.lower()
        assert not result.startswith("```")
        assert not result.endswith("```")

    @given(st.text())
    def test_property_idempotent(self, latex_content):
        """Property: Cleaning twice should give same result as cleaning once."""
        first_clean = clean_latex_output(latex_content)
        second_clean = clean_latex_output(first_clean)
        assert first_clean == second_clean


class TestValidateLatexSyntax:
    """Tests for validate_latex_syntax function."""

    def test_valid_simple_latex(self):
        """Test valid simple LaTeX."""
        latex = "\\begin{document}\\end{document}"
        is_valid, errors = validate_latex_syntax(latex)
        assert is_valid
        assert len(errors) == 0

    def test_unmatched_braces(self):
        """Test detection of unmatched braces."""
        latex = "\\textbf{Bold"
        is_valid, errors = validate_latex_syntax(latex)
        assert not is_valid
        assert any("brace" in err.lower() for err in errors)

    def test_unmatched_environment(self):
        """Test detection of unmatched environment."""
        latex = "\\begin{document}"
        is_valid, errors = validate_latex_syntax(latex)
        assert not is_valid
        assert any("document" in err for err in errors)

    def test_mismatched_environment(self):
        """Test detection of mismatched environment."""
        latex = "\\begin{document}\\end{itemize}"
        is_valid, errors = validate_latex_syntax(latex)
        assert not is_valid
        assert any("mismatch" in err.lower() for err in errors)

    def test_empty_string(self):
        """Test validation of empty string."""
        is_valid, errors = validate_latex_syntax("")
        assert is_valid
        assert len(errors) == 0

    def test_nested_environments(self):
        """Test validation of nested environments."""
        latex = "\\begin{document}\\begin{itemize}\\item Test\\end{itemize}\\end{document}"
        is_valid, errors = validate_latex_syntax(latex)
        assert is_valid
        assert len(errors) == 0


class TestFormatLatexForDisplay:
    """Tests for format_latex_for_display function."""

    def test_short_content(self):
        """Test formatting short content (no truncation)."""
        latex = "\\section{Title}\n\\textbf{Bold}"
        result = format_latex_for_display(latex, max_lines=10)
        assert result == latex

    def test_long_content_truncated(self):
        """Test truncation of long content."""
        lines = [f"Line {i}" for i in range(20)]
        latex = "\n".join(lines)
        result = format_latex_for_display(latex, max_lines=5)
        
        # Should contain first 4 lines and ellipsis
        assert "Line 0" in result
        assert "Line 3" in result
        assert "..." in result
        assert "Line 19" not in result

    def test_empty_string(self):
        """Test formatting empty string."""
        result = format_latex_for_display("")
        assert result == ""

    def test_exact_max_lines(self):
        """Test content with exactly max_lines."""
        lines = [f"Line {i}" for i in range(10)]
        latex = "\n".join(lines)
        result = format_latex_for_display(latex, max_lines=10)
        assert result == latex


class TestExtractPreamble:
    """Tests for extract_preamble function."""

    def test_extract_simple_preamble(self):
        """Test extracting simple preamble."""
        latex = "\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\nContent\n\\end{document}"
        preamble = extract_preamble(latex)
        assert "\\documentclass{article}" in preamble
        assert "\\usepackage{amsmath}" in preamble
        assert "\\begin{document}" not in preamble

    def test_no_preamble(self):
        """Test document without preamble."""
        latex = "\\begin{document}\nContent\n\\end{document}"
        preamble = extract_preamble(latex)
        assert preamble == ""

    def test_no_begin_document(self):
        """Test content without \\begin{document}."""
        latex = "\\documentclass{article}\n\\usepackage{amsmath}"
        preamble = extract_preamble(latex)
        assert preamble == ""

    def test_empty_string(self):
        """Test extracting from empty string."""
        preamble = extract_preamble("")
        assert preamble == ""

    def test_preamble_with_comments(self):
        """Test preamble with comments."""
        latex = "% Comment\n\\documentclass{article}\n% Another comment\n\\begin{document}\nContent"
        preamble = extract_preamble(latex)
        assert "% Comment" in preamble
        assert "\\documentclass{article}" in preamble
        assert "Content" not in preamble



class TestTexParser:
    """Tests for TeX file parsing utilities."""

    def test_parse_tex_file(self, tmp_path):
        """Test reading TeX file content."""
        from vbagent.tex import parse_tex_file
        
        # Create a temporary TeX file
        tex_file = tmp_path / "test.tex"
        content = "\\item Test problem\n\\begin{solution}\nTest solution\n\\end{solution}"
        tex_file.write_text(content)
        
        result = parse_tex_file(str(tex_file))
        assert result == content

    def test_parse_tex_file_with_sections(self, tmp_path):
        """Test extracting problem and solution sections."""
        from vbagent.tex import parse_tex_file_with_sections
        
        # Create a temporary TeX file
        tex_file = tmp_path / "test.tex"
        content = "\\item This is the problem\n\\begin{solution}\nThis is the solution\n\\end{solution}"
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        assert problem == "This is the problem"
        assert solution == "This is the solution"

    def test_parse_tex_file_with_sections_no_solution(self, tmp_path):
        """Test parsing file without solution."""
        from vbagent.tex import parse_tex_file_with_sections
        
        tex_file = tmp_path / "test.tex"
        content = "\\item This is the problem"
        tex_file.write_text(content)
        
        problem, solution = parse_tex_file_with_sections(str(tex_file))
        # When no solution is found, the entire content is returned as problem
        assert problem == content
        assert solution == ""

    def test_extract_items(self):
        """Test extracting items from content."""
        from vbagent.tex import extract_items
        
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
        from vbagent.tex import extract_items
        
        items = extract_items("")
        assert len(items) == 0

    def test_extract_items_no_items(self):
        """Test extracting items from content without items."""
        from vbagent.tex import extract_items
        
        content = "Some content without items"
        items = extract_items(content)
        assert len(items) == 0

    def test_extract_answer_mcq_single(self):
        """Test extracting single MCQ answer."""
        from vbagent.tex import extract_answer
        
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

    def test_extract_answer_mcq_multiple(self):
        """Test extracting multiple correct MCQ answers."""
        from vbagent.tex import extract_answer
        
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

    def test_extract_answer_integer(self):
        """Test extracting integer answer."""
        from vbagent.tex import extract_answer
        
        content = "The answer is \\ansint{42}"
        answer = extract_answer(content)
        assert answer == "42"

    def test_extract_answer_none(self):
        """Test extracting answer when none present."""
        from vbagent.tex import extract_answer
        
        content = "Some problem without answer markers"
        answer = extract_answer(content)
        assert answer is None

    def test_extract_answer_with_comments(self):
        """Test extracting answer with comments in content."""
        from vbagent.tex import extract_answer
        
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
