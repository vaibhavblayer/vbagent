"""Integration tests for supporting systems (metadata, DPP, LaTeX, export)."""

import pytest
from pathlib import Path
import tempfile
import shutil
from vbagent.metadata import MetadataStore, QuestionMetadata
from vbagent.dpp import DPPBuilder
from vbagent.export import Exporter, ExportMode
from vbagent.tex import parse_latex_project, extract_from_directory


class TestSupportingSystemsIntegration:
    """Integration tests verifying that supporting systems work together."""
    
    @pytest.fixture
    def temp_question_bank(self):
        """Create a temporary question bank with sample questions."""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample questions with metadata
        questions = [
            {
                "filename": "mechanics_easy_1.tex",
                "content": """% chapter: Mechanics
% topic: Kinematics
% difficulty: easy
% question_type: mcq_sc
% tags: velocity, displacement

\\begin{question}
A car travels 100 m in 10 s. What is its average velocity?
\\begin{choices}
\\item 5 m/s
\\item 10 m/s
\\item 15 m/s
\\item 20 m/s
\\end{choices}
\\end{question}
"""
            },
            {
                "filename": "mechanics_medium_1.tex",
                "content": """% chapter: Mechanics
% topic: Dynamics
% difficulty: medium
% question_type: subjective
% tags: force, acceleration

\\begin{question}
A block of mass 5 kg is pushed with a force of 20 N. Calculate the acceleration.
\\end{question}
"""
            },
            {
                "filename": "mechanics_hard_1.tex",
                "content": """% chapter: Mechanics
% topic: Energy
% difficulty: hard
% question_type: subjective
% tags: energy, work

\\begin{question}
Derive the work-energy theorem from Newton's second law.
\\end{question}
"""
            },
            {
                "filename": "thermodynamics_easy_1.tex",
                "content": """% chapter: Thermodynamics
% topic: Heat Transfer
% difficulty: easy
% question_type: mcq_sc
% tags: heat, temperature

\\begin{question}
What is the SI unit of heat?
\\begin{choices}
\\item Joule
\\item Watt
\\item Kelvin
\\item Calorie
\\end{choices}
\\end{question}
"""
            },
            {
                "filename": "thermodynamics_medium_1.tex",
                "content": """% chapter: Thermodynamics
% topic: Laws of Thermodynamics
% difficulty: medium
% question_type: subjective
% tags: entropy, thermodynamics

\\begin{question}
State and explain the second law of thermodynamics.
\\end{question}
"""
            }
        ]
        
        for q in questions:
            file_path = temp_dir / q["filename"]
            file_path.write_text(q["content"])
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def metadata_store(self, temp_question_bank):
        """Create a metadata store with indexed questions."""
        db_path = temp_question_bank / "metadata.db"
        store = MetadataStore(db_path)
        store.index_directory(temp_question_bank, recursive=False)
        return store
    
    def test_metadata_to_dpp_integration(self, temp_question_bank, metadata_store):
        """Test creating a DPP from indexed metadata."""
        # Create DPP builder
        builder = DPPBuilder(metadata_store)
        
        # Create a DPP with 3 questions
        output_dir = temp_question_bank / "dpp_output"
        result = builder.create_dpp(
            count=3,
            strategy="balanced",
            output_path=output_dir
        )
        
        # Verify DPP was created
        assert result is not None
        assert len(result.questions) == 3
        assert result.main_tex_path.exists()
        assert result.strategy_used == "balanced"
        
        # Verify main.tex contains the questions
        main_tex_content = result.main_tex_path.read_text()
        assert "\\begin{document}" in main_tex_content
        assert "\\end{document}" in main_tex_content
        
        # Verify usage statistics were updated
        for question in result.questions:
            metadata = metadata_store.get_by_path(question.file_path)
            assert metadata is not None
            assert metadata.usage_count >= 1
            assert metadata.last_used is not None
    
    def test_dpp_to_export_integration(self, temp_question_bank, metadata_store):
        """Test exporting a DPP in different formats."""
        # Create a DPP
        builder = DPPBuilder(metadata_store)
        dpp_output_dir = temp_question_bank / "dpp_output"
        dpp_result = builder.create_dpp(
            count=3,
            strategy="random",
            output_path=dpp_output_dir
        )
        
        # Export in flat mode
        exporter = Exporter()
        export_dir_flat = temp_question_bank / "export_flat"
        export_result_flat = exporter.export(
            files=[dpp_result.main_tex_path],
            output_dir=export_dir_flat,
            mode=ExportMode.FLAT
        )
        
        assert export_result_flat.output_dir.exists()
        assert export_result_flat.file_count == 1
        assert export_result_flat.mode == ExportMode.FLAT
        
        # Export in project mode
        export_dir_project = temp_question_bank / "export_project"
        
        # Get all question files from DPP
        question_files = [Path(q.file_path) for q in dpp_result.questions]
        
        export_result_project = exporter.export(
            files=question_files,
            output_dir=export_dir_project,
            mode=ExportMode.PROJECT,
            title="Physics DPP"
        )
        
        assert export_result_project.output_dir.exists()
        assert export_result_project.file_count == len(question_files)
        assert export_result_project.mode == ExportMode.PROJECT
        assert export_result_project.main_tex is not None
        assert export_result_project.main_tex.exists()
        
        # Verify main.tex has proper structure
        main_tex_content = export_result_project.main_tex.read_text()
        assert "\\documentclass" in main_tex_content
        assert "\\begin{document}" in main_tex_content
        assert "\\input{" in main_tex_content
        assert "\\end{document}" in main_tex_content
    
    def test_latex_extraction_with_dpp(self, temp_question_bank, metadata_store):
        """Test LaTeX extraction on a generated DPP."""
        # Create a DPP
        builder = DPPBuilder(metadata_store)
        dpp_output_dir = temp_question_bank / "dpp_output"
        dpp_result = builder.create_dpp(
            count=2,
            strategy="topic_coverage",
            output_path=dpp_output_dir
        )
        
        # Parse the LaTeX project
        parsed_files = parse_latex_project(dpp_result.main_tex_path)
        
        # Verify parsing worked
        assert len(parsed_files) > 0
        # The key might have /private prefix on macOS, so find the actual key
        main_tex_str = str(dpp_result.main_tex_path)
        actual_key = None
        for key in parsed_files.keys():
            if main_tex_str in key or key.endswith(main_tex_str.split('/')[-1]):
                actual_key = key
                break
        
        assert actual_key is not None, f"Could not find main.tex in parsed files. Keys: {list(parsed_files.keys())}"
        
        # Verify main.tex content
        main_content = parsed_files[actual_key]
        assert "\\documentclass" in main_content
        assert "\\begin{document}" in main_content
    
    def test_metadata_query_to_export_integration(self, temp_question_bank, metadata_store):
        """Test querying metadata and exporting the results."""
        # Query for mechanics questions
        mechanics_questions = metadata_store.query(chapter="Mechanics")
        
        assert len(mechanics_questions) == 3
        
        # Export the mechanics questions
        exporter = Exporter()
        export_dir = temp_question_bank / "mechanics_export"
        
        question_files = [Path(q.file_path) for q in mechanics_questions]
        
        export_result = exporter.export(
            files=question_files,
            output_dir=export_dir,
            mode=ExportMode.STRUCTURED
        )
        
        assert export_result.output_dir.exists()
        assert export_result.file_count == 3
        assert export_result.mode == ExportMode.STRUCTURED
        
        # Verify files were exported
        exported_files = list(export_dir.rglob("*.tex"))
        assert len(exported_files) == 3
    
    def test_full_workflow_integration(self, temp_question_bank):
        """Test complete workflow: index → query → DPP → export."""
        # Step 1: Index the question bank
        db_path = temp_question_bank / "metadata.db"
        store = MetadataStore(db_path)
        indexed_count = store.index_directory(temp_question_bank, recursive=False)
        
        assert indexed_count == 5
        
        # Step 2: Query for specific questions
        easy_questions = store.query(difficulty="easy")
        assert len(easy_questions) == 2
        
        # Step 3: Create a DPP with balanced strategy
        builder = DPPBuilder(store)
        dpp_output_dir = temp_question_bank / "dpp_output"
        dpp_result = builder.create_dpp(
            count=3,
            strategy="balanced",
            output_path=dpp_output_dir
        )
        
        assert len(dpp_result.questions) == 3
        assert dpp_result.main_tex_path.exists()
        
        # Step 4: Export the DPP in project mode
        exporter = Exporter()
        export_dir = temp_question_bank / "final_export"
        
        export_result = exporter.export(
            files=[dpp_result.main_tex_path],
            output_dir=export_dir,
            mode=ExportMode.PROJECT,
            title="Final DPP"
        )
        
        assert export_result.output_dir.exists()
        assert export_result.main_tex is not None
        
        # Step 5: Verify the exported project can be parsed
        parsed_files = parse_latex_project(export_result.main_tex)
        assert len(parsed_files) > 0
        
        # Step 6: Verify usage statistics were updated
        for question in dpp_result.questions:
            metadata = store.get_by_path(question.file_path)
            assert metadata is not None
            assert metadata.usage_count >= 1
    
    def test_directory_extraction_integration(self, temp_question_bank):
        """Test extracting files from directory and exporting them."""
        # Extract all .tex files from the question bank
        tex_files = extract_from_directory(
            temp_question_bank,
            pattern="*.tex",
            recursive=False
        )
        
        assert len(tex_files) == 5
        
        # Export them in structured mode
        exporter = Exporter()
        export_dir = temp_question_bank / "structured_export"
        
        export_result = exporter.export(
            files=tex_files,
            output_dir=export_dir,
            mode=ExportMode.STRUCTURED
        )
        
        assert export_result.output_dir.exists()
        assert export_result.file_count == 5
        
        # Verify subdirectories were created (files go to "other" since parent is temp dir)
        assert (export_dir / "other").exists()
    
    def test_error_handling_integration(self, temp_question_bank, metadata_store):
        """Test error handling across systems."""
        builder = DPPBuilder(metadata_store)
        
        # Test insufficient questions
        with pytest.raises(ValueError, match="Insufficient questions"):
            builder.create_dpp(
                count=100,  # More than available
                strategy="balanced"
            )
        
        # Test invalid strategy
        with pytest.raises(ValueError, match="Unknown strategy"):
            builder.create_dpp(
                count=2,
                strategy="invalid_strategy"
            )
        
        # Test export with non-existent file
        exporter = Exporter()
        with pytest.raises(FileNotFoundError):
            exporter.export(
                files=[Path("nonexistent.tex")],
                output_dir=temp_question_bank / "export",
                mode=ExportMode.FLAT
            )
    
    def test_statistics_after_multiple_dpps(self, temp_question_bank, metadata_store):
        """Test that statistics are correctly maintained across multiple DPP creations."""
        builder = DPPBuilder(metadata_store)
        
        # Create first DPP
        dpp1 = builder.create_dpp(
            count=2,
            strategy="random",
            output_path=temp_question_bank / "dpp1"
        )
        
        # Create second DPP
        dpp2 = builder.create_dpp(
            count=2,
            strategy="random",
            output_path=temp_question_bank / "dpp2"
        )
        
        # Get statistics
        stats = metadata_store.get_statistics()
        
        assert stats["total_questions"] == 5
        # Check that some questions have been used
        assert len(stats["most_used"]) >= 2  # At least 2 questions used
        
        # Verify individual question usage
        all_questions = metadata_store.query()
        total_usage = sum(q.usage_count for q in all_questions)
        assert total_usage >= 4
