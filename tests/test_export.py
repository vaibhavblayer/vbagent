"""Unit tests for the export system."""

import pytest
from pathlib import Path
import tempfile
import shutil

from vbagent.export import Exporter, ExportMode, ExportResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample LaTeX files for testing."""
    files = []
    
    # Create some sample .tex files
    for i in range(3):
        file_path = temp_dir / f"question_{i+1}.tex"
        content = f"""\\item Question {i+1}
This is a sample physics question.

\\begin{{tasks}}(2)
\\task Option A
\\task Option B
\\task Option C
\\task Option D
\\end{{tasks}}
"""
        file_path.write_text(content)
        files.append(file_path)
    
    return files


class TestExporter:
    """Test cases for the Exporter class."""
    
    def test_export_flat_mode(self, sample_files, temp_dir):
        """Test flat export mode - all files in one directory."""
        output_dir = temp_dir / "output_flat"
        exporter = Exporter()
        
        result = exporter.export(
            files=sample_files,
            output_dir=output_dir,
            mode=ExportMode.FLAT
        )
        
        # Verify result
        assert isinstance(result, ExportResult)
        assert result.output_dir == output_dir
        assert result.file_count == 3
        assert result.mode == ExportMode.FLAT
        assert result.main_tex is None
        
        # Verify files were copied
        assert output_dir.exists()
        exported_files = list(output_dir.glob("*.tex"))
        assert len(exported_files) == 3
        
        # Verify content is preserved
        for original, exported in zip(sample_files, sorted(exported_files)):
            assert exported.read_text() == original.read_text()
    
    def test_export_flat_mode_name_conflicts(self, temp_dir):
        """Test flat mode handles name conflicts correctly."""
        # Create files with same name in different directories
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        file1 = dir1 / "question.tex"
        file2 = dir2 / "question.tex"
        file1.write_text("Question 1")
        file2.write_text("Question 2")
        
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        result = exporter.export(
            files=[file1, file2],
            output_dir=output_dir,
            mode=ExportMode.FLAT
        )
        
        # Verify both files were exported with different names
        assert result.file_count == 2
        exported_files = list(output_dir.glob("*.tex"))
        assert len(exported_files) == 2
        
        # One should be question.tex, the other question_1.tex
        names = {f.name for f in exported_files}
        assert "question.tex" in names
        assert "question_1.tex" in names
    
    def test_export_structured_mode(self, temp_dir):
        """Test structured export mode - organized subdirectories."""
        # Create files in different subdirectories
        questions_dir = temp_dir / "questions"
        solutions_dir = temp_dir / "solutions"
        diagrams_dir = temp_dir / "diagrams"
        
        questions_dir.mkdir()
        solutions_dir.mkdir()
        diagrams_dir.mkdir()
        
        q1 = questions_dir / "q1.tex"
        s1 = solutions_dir / "s1.tex"
        d1 = diagrams_dir / "d1.tex"
        
        q1.write_text("Question 1")
        s1.write_text("Solution 1")
        d1.write_text("Diagram 1")
        
        output_dir = temp_dir / "output_structured"
        exporter = Exporter()
        
        result = exporter.export(
            files=[q1, s1, d1],
            output_dir=output_dir,
            mode=ExportMode.STRUCTURED
        )
        
        # Verify result
        assert result.file_count == 3
        assert result.mode == ExportMode.STRUCTURED
        
        # Verify subdirectories were created
        assert (output_dir / "questions").exists()
        assert (output_dir / "solutions").exists()
        assert (output_dir / "diagrams").exists()
        
        # Verify files are in correct subdirectories
        assert (output_dir / "questions" / "q1.tex").exists()
        assert (output_dir / "solutions" / "s1.tex").exists()
        assert (output_dir / "diagrams" / "d1.tex").exists()
    
    def test_export_structured_mode_other_category(self, temp_dir):
        """Test structured mode puts unrecognized files in 'other' directory."""
        misc_dir = temp_dir / "misc"
        misc_dir.mkdir()
        
        file1 = misc_dir / "file1.tex"
        file1.write_text("Miscellaneous content")
        
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        result = exporter.export(
            files=[file1],
            output_dir=output_dir,
            mode=ExportMode.STRUCTURED
        )
        
        # Verify file is in 'other' subdirectory
        assert (output_dir / "other" / "file1.tex").exists()
    
    def test_export_project_mode(self, sample_files, temp_dir):
        """Test project export mode - main.tex with \\input{} references."""
        output_dir = temp_dir / "output_project"
        exporter = Exporter()
        
        result = exporter.export(
            files=sample_files,
            output_dir=output_dir,
            mode=ExportMode.PROJECT,
            title="Test DPP"
        )
        
        # Verify result
        assert result.file_count == 3
        assert result.mode == ExportMode.PROJECT
        assert result.main_tex is not None
        assert result.main_tex.exists()
        
        # Verify main.tex was created
        main_tex = output_dir / "main.tex"
        assert main_tex.exists()
        assert result.main_tex == main_tex
        
        # Verify main.tex content
        main_content = main_tex.read_text()
        assert "Test DPP" in main_content
        assert "\\documentclass" in main_content
        assert "\\begin{document}" in main_content
        assert "\\end{document}" in main_content
        
        # Verify input commands are present
        assert "\\input{question_001}" in main_content
        assert "\\input{question_002}" in main_content
        assert "\\input{question_003}" in main_content
        
        # Verify individual files were copied
        assert (output_dir / "question_001.tex").exists()
        assert (output_dir / "question_002.tex").exists()
        assert (output_dir / "question_003.tex").exists()
    
    def test_export_project_mode_custom_template(self, sample_files, temp_dir):
        """Test project mode with custom template."""
        custom_template = r"""\documentclass{{article}}
\title{{{title}}}
\begin{{document}}
\maketitle
Custom preamble here.
{content}
\end{{document}}
"""
        
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        result = exporter.export(
            files=sample_files,
            output_dir=output_dir,
            mode=ExportMode.PROJECT,
            template=custom_template,
            title="Custom Title"
        )
        
        # Verify custom template was used
        main_content = result.main_tex.read_text()
        assert "Custom preamble here." in main_content
        assert "Custom Title" in main_content
    
    def test_export_empty_files_list(self, temp_dir):
        """Test that exporting empty files list raises ValueError."""
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        with pytest.raises(ValueError, match="Files list cannot be empty"):
            exporter.export(
                files=[],
                output_dir=output_dir,
                mode=ExportMode.FLAT
            )
    
    def test_export_nonexistent_file(self, temp_dir):
        """Test that exporting nonexistent file raises FileNotFoundError."""
        nonexistent = temp_dir / "nonexistent.tex"
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            exporter.export(
                files=[nonexistent],
                output_dir=output_dir,
                mode=ExportMode.FLAT
            )
    
    def test_export_creates_output_directory(self, sample_files, temp_dir):
        """Test that export creates output directory if it doesn't exist."""
        output_dir = temp_dir / "nested" / "output"
        assert not output_dir.exists()
        
        exporter = Exporter()
        result = exporter.export(
            files=sample_files,
            output_dir=output_dir,
            mode=ExportMode.FLAT
        )
        
        # Verify directory was created
        assert output_dir.exists()
        assert result.file_count == 3
    
    def test_export_result_to_dict(self, sample_files, temp_dir):
        """Test ExportResult.to_dict() method."""
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        result = exporter.export(
            files=sample_files,
            output_dir=output_dir,
            mode=ExportMode.PROJECT,
            title="Test"
        )
        
        result_dict = result.to_dict()
        
        # Verify dictionary structure
        assert "output_dir" in result_dict
        assert "file_count" in result_dict
        assert "mode" in result_dict
        assert "main_tex" in result_dict
        assert "created_at" in result_dict
        
        assert result_dict["file_count"] == 3
        assert result_dict["mode"] == "project"
        assert result_dict["main_tex"] is not None
    
    def test_export_with_metadata(self, sample_files, temp_dir):
        """Test export_with_metadata method."""
        output_dir = temp_dir / "output"
        exporter = Exporter()
        
        # Create files with metadata
        files_with_metadata = [
            (sample_files[0], {"difficulty": "easy", "topic": "mechanics"}),
            (sample_files[1], {"difficulty": "medium", "topic": "thermodynamics"}),
            (sample_files[2], {"difficulty": "hard", "topic": "electromagnetism"}),
        ]
        
        result = exporter.export_with_metadata(
            files_with_metadata=files_with_metadata,
            output_dir=output_dir,
            mode=ExportMode.FLAT
        )
        
        # Verify export worked
        assert result.file_count == 3
        assert result.mode == ExportMode.FLAT


class TestExportMode:
    """Test cases for ExportMode enum."""
    
    def test_export_mode_values(self):
        """Test ExportMode enum values."""
        assert ExportMode.FLAT.value == "flat"
        assert ExportMode.STRUCTURED.value == "structured"
        assert ExportMode.PROJECT.value == "project"
    
    def test_export_mode_from_string(self):
        """Test creating ExportMode from string."""
        assert ExportMode("flat") == ExportMode.FLAT
        assert ExportMode("structured") == ExportMode.STRUCTURED
        assert ExportMode("project") == ExportMode.PROJECT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
