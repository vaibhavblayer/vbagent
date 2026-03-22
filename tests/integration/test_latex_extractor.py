"""Tests for LaTeX extraction functionality.

This module tests the enhanced LaTeX extraction capabilities including:
- Subitem extraction
- Multi-file project parsing
- Circular reference detection
- Directory extraction with filtering
"""

import pytest
from pathlib import Path
from vbagent.tex import (
    extract_subitems,
    parse_latex_project,
    extract_from_directory,
    CircularReferenceError,
)


class TestExtractSubitems:
    """Tests for extract_subitems function."""
    
    def test_extract_simple_subitems(self):
        """Test extraction of simple (a), (b), (c) subitems."""
        content = r"""
\item (a) First part of the question
\item (b) Second part of the question
\item (c) Third part of the question
"""
        subitems = extract_subitems(content)
        
        assert len(subitems) == 3
        assert "(a) First part of the question" in subitems[0]
        assert "(b) Second part of the question" in subitems[1]
        assert "(c) Third part of the question" in subitems[2]
    
    def test_extract_subitems_with_content(self):
        """Test extraction preserves all content including math."""
        content = r"""
\item (a) Calculate $F = ma$ where $m = 10$ kg
\item (b) Find velocity $v = \sqrt{2gh}$
"""
        subitems = extract_subitems(content)
        
        assert len(subitems) == 2
        assert "$F = ma$" in subitems[0]
        assert "$v = \\sqrt{2gh}$" in subitems[1]
    
    def test_extract_subitems_roman_numerals(self):
        """Test extraction with roman numeral labels."""
        content = r"""
\item (i) First part
\item (ii) Second part
\item (iii) Third part
"""
        subitems = extract_subitems(content)
        
        assert len(subitems) == 3
        assert "(i) First part" in subitems[0]
        assert "(ii) Second part" in subitems[1]
    
    def test_no_subitems_returns_original(self):
        """Test that content without subitems returns original."""
        content = r"\item This is a single question without subitems"
        subitems = extract_subitems(content)
        
        assert len(subitems) == 1
        assert subitems[0] == content
    
    def test_extract_subitems_with_whitespace(self):
        """Test extraction handles various whitespace patterns."""
        content = r"""
\item   (a)   First with extra spaces
\item(b)Second without spaces
\item  (c)  Third mixed
"""
        subitems = extract_subitems(content)
        
        assert len(subitems) == 3
        assert "(a)" in subitems[0]
        assert "(b)" in subitems[1]
        assert "(c)" in subitems[2]
    
    def test_extract_subitems_multiline_content(self):
        """Test extraction with multi-line subitem content."""
        content = r"""
\item (a) First part with
multiple lines of content
and equations $E = mc^2$

\item (b) Second part also
spans multiple lines
"""
        subitems = extract_subitems(content)
        
        assert len(subitems) == 2
        assert "multiple lines" in subitems[0]
        assert "spans multiple lines" in subitems[1]


class TestParseLatexProject:
    """Tests for parse_latex_project function."""
    
    def test_parse_single_file(self, tmp_path):
        """Test parsing a single file without inputs."""
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 1
        assert str(main_tex.resolve()) in result
        assert "Hello" in result[str(main_tex.resolve())]
    
    def test_parse_with_input(self, tmp_path):
        """Test parsing with \\input{} reference."""
        chapter1 = tmp_path / "chapter1.tex"
        chapter1.write_text(r"Chapter 1 content")
        
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\documentclass{article}\input{chapter1}\end{document}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 2
        assert str(main_tex.resolve()) in result
        assert str(chapter1.resolve()) in result
        assert "Chapter 1 content" in result[str(chapter1.resolve())]
    
    def test_parse_with_include(self, tmp_path):
        """Test parsing with \\include{} reference."""
        chapter1 = tmp_path / "chapter1.tex"
        chapter1.write_text(r"Chapter 1 content")
        
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\documentclass{article}\include{chapter1}\end{document}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 2
        assert str(chapter1.resolve()) in result
    
    def test_parse_nested_inputs(self, tmp_path):
        """Test parsing with nested \\input{} references."""
        section1 = tmp_path / "section1.tex"
        section1.write_text(r"Section 1 content")
        
        chapter1 = tmp_path / "chapter1.tex"
        chapter1.write_text(r"Chapter 1\input{section1}")
        
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\input{chapter1}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 3
        assert str(main_tex.resolve()) in result
        assert str(chapter1.resolve()) in result
        assert str(section1.resolve()) in result
    
    def test_parse_with_subdirectory(self, tmp_path):
        """Test parsing with files in subdirectories."""
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        
        chapter1 = chapters_dir / "chapter1.tex"
        chapter1.write_text(r"Chapter 1 content")
        
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\input{chapters/chapter1}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 2
        assert str(chapter1.resolve()) in result
    
    def test_parse_without_tex_extension(self, tmp_path):
        """Test parsing handles files without .tex extension in \\input{}."""
        chapter1 = tmp_path / "chapter1.tex"
        chapter1.write_text(r"Chapter 1 content")
        
        main_tex = tmp_path / "main.tex"
        # Note: no .tex extension in \input{}
        main_tex.write_text(r"\input{chapter1}")
        
        result = parse_latex_project(main_tex)
        
        assert len(result) == 2
        assert str(chapter1.resolve()) in result
    
    def test_circular_reference_detection(self, tmp_path):
        """Test detection of circular \\input{} references."""
        file_a = tmp_path / "a.tex"
        file_b = tmp_path / "b.tex"
        
        file_a.write_text(r"\input{b}")
        file_b.write_text(r"\input{a}")
        
        with pytest.raises(CircularReferenceError) as exc_info:
            parse_latex_project(file_a)
        
        assert "Circular reference" in str(exc_info.value)
        assert len(exc_info.value.cycle_path) >= 2
    
    def test_self_reference_detection(self, tmp_path):
        """Test detection of file referencing itself."""
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\input{main}")
        
        with pytest.raises(CircularReferenceError):
            parse_latex_project(main_tex)
    
    def test_missing_file_error(self, tmp_path):
        """Test error when referenced file doesn't exist."""
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\input{nonexistent}")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_latex_project(main_tex)
        
        assert "nonexistent" in str(exc_info.value)
    
    def test_max_depth_exceeded(self, tmp_path):
        """Test error when max recursion depth is exceeded."""
        # Create a chain of files
        for i in range(15):
            file = tmp_path / f"file{i}.tex"
            if i < 14:
                file.write_text(f"\\input{{file{i+1}}}")
            else:
                file.write_text("End")
        
        main_tex = tmp_path / "file0.tex"
        
        with pytest.raises(ValueError, match="Maximum recursion depth"):
            parse_latex_project(main_tex, max_depth=10)
    
    def test_duplicate_input_handled(self, tmp_path):
        """Test that same file referenced multiple times is handled correctly."""
        common = tmp_path / "common.tex"
        common.write_text(r"Common content")
        
        chapter1 = tmp_path / "chapter1.tex"
        chapter1.write_text(r"\input{common}")
        
        chapter2 = tmp_path / "chapter2.tex"
        chapter2.write_text(r"\input{common}")
        
        main_tex = tmp_path / "main.tex"
        main_tex.write_text(r"\input{chapter1}\input{chapter2}")
        
        result = parse_latex_project(main_tex)
        
        # Should have 4 unique files
        assert len(result) == 4
        assert str(common.resolve()) in result


class TestExtractFromDirectory:
    """Tests for extract_from_directory function."""
    
    def test_extract_all_tex_files(self, tmp_path):
        """Test extracting all .tex files from directory."""
        (tmp_path / "file1.tex").write_text("Content 1")
        (tmp_path / "file2.tex").write_text("Content 2")
        (tmp_path / "file3.txt").write_text("Not tex")
        
        files = extract_from_directory(tmp_path)
        
        assert len(files) == 2
        assert all(f.suffix == ".tex" for f in files)
    
    def test_extract_recursive(self, tmp_path):
        """Test recursive extraction from subdirectories."""
        (tmp_path / "file1.tex").write_text("Content 1")
        
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.tex").write_text("Content 2")
        
        files = extract_from_directory(tmp_path, recursive=True)
        
        assert len(files) == 2
    
    def test_extract_non_recursive(self, tmp_path):
        """Test non-recursive extraction (only top level)."""
        (tmp_path / "file1.tex").write_text("Content 1")
        
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.tex").write_text("Content 2")
        
        files = extract_from_directory(tmp_path, recursive=False)
        
        assert len(files) == 1
        assert files[0].name == "file1.tex"
    
    def test_extract_with_subdirectory_filter(self, tmp_path):
        """Test extraction with subdirectory filter."""
        (tmp_path / "file1.tex").write_text("Content 1")
        
        scans_dir = tmp_path / "scans"
        scans_dir.mkdir()
        (scans_dir / "scan1.tex").write_text("Scan 1")
        (scans_dir / "scan2.tex").write_text("Scan 2")
        
        variants_dir = tmp_path / "variants"
        variants_dir.mkdir()
        (variants_dir / "variant1.tex").write_text("Variant 1")
        
        # Extract only from scans subdirectory
        files = extract_from_directory(tmp_path, subdirectory="scans")
        
        assert len(files) == 2
        assert all("scans" in str(f) for f in files)
    
    def test_extract_nonexistent_subdirectory(self, tmp_path):
        """Test extraction with nonexistent subdirectory returns empty list."""
        (tmp_path / "file1.tex").write_text("Content 1")
        
        files = extract_from_directory(tmp_path, subdirectory="nonexistent")
        
        assert len(files) == 0
    
    def test_extract_custom_pattern(self, tmp_path):
        """Test extraction with custom glob pattern."""
        (tmp_path / "file1.tex").write_text("Content 1")
        (tmp_path / "file2.tex").write_text("Content 2")
        (tmp_path / "test1.tex").write_text("Test 1")
        
        files = extract_from_directory(tmp_path, pattern="test*.tex")
        
        assert len(files) == 1
        assert files[0].name == "test1.tex"
    
    def test_extract_sorted_output(self, tmp_path):
        """Test that extracted files are sorted."""
        (tmp_path / "c.tex").write_text("C")
        (tmp_path / "a.tex").write_text("A")
        (tmp_path / "b.tex").write_text("B")
        
        files = extract_from_directory(tmp_path)
        
        assert len(files) == 3
        assert files[0].name == "a.tex"
        assert files[1].name == "b.tex"
        assert files[2].name == "c.tex"
    
    def test_extract_directory_not_found(self, tmp_path):
        """Test error when directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        
        with pytest.raises(FileNotFoundError):
            extract_from_directory(nonexistent)
    
    def test_extract_not_a_directory(self, tmp_path):
        """Test error when path is not a directory."""
        file_path = tmp_path / "file.tex"
        file_path.write_text("Content")
        
        with pytest.raises(ValueError, match="Not a directory"):
            extract_from_directory(file_path)


class TestCircularReferenceError:
    """Tests for CircularReferenceError exception."""
    
    def test_error_message_includes_cycle(self):
        """Test that error message includes the cycle path."""
        cycle = ["/path/a.tex", "/path/b.tex", "/path/a.tex"]
        error = CircularReferenceError(cycle)
        
        assert "Circular reference" in str(error)
        assert "/path/a.tex" in str(error)
        assert "/path/b.tex" in str(error)
        assert "->" in str(error)
    
    def test_cycle_path_attribute(self):
        """Test that cycle_path attribute is accessible."""
        cycle = ["/path/a.tex", "/path/b.tex", "/path/a.tex"]
        error = CircularReferenceError(cycle)
        
        assert error.cycle_path == cycle
