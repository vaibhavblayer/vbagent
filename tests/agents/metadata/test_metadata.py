"""Unit tests for metadata system."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from vbagent.metadata import MetadataStore, QuestionMetadata
from vbagent.metadata.store import MetadataExtractor


class TestQuestionMetadata:
    """Test QuestionMetadata dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metadata = QuestionMetadata(
            file_path="/path/to/question.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="medium",
            question_type="mcq_sc",
            tags=["motion", "graphs"],
            usage_count=5,
        )
        
        result = metadata.to_dict()
        
        assert result["file_path"] == "/path/to/question.tex"
        assert result["chapter"] == "Mechanics"
        assert result["topic"] == "Kinematics"
        assert result["difficulty"] == "medium"
        assert result["question_type"] == "mcq_sc"
        assert result["tags"] == ["motion", "graphs"]
        assert result["usage_count"] == 5
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "file_path": "/path/to/question.tex",
            "chapter": "Mechanics",
            "topic": "Kinematics",
            "difficulty": "medium",
            "question_type": "mcq_sc",
            "tags": ["motion", "graphs"],
            "usage_count": 5,
            "last_used": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        metadata = QuestionMetadata.from_dict(data)
        
        assert metadata.file_path == "/path/to/question.tex"
        assert metadata.chapter == "Mechanics"
        assert metadata.topic == "Kinematics"
        assert metadata.difficulty == "medium"
        assert metadata.question_type == "mcq_sc"
        assert metadata.tags == ["motion", "graphs"]
        assert metadata.usage_count == 5


class TestMetadataExtractor:
    """Test metadata extraction from LaTeX files."""
    
    def test_extract_from_comments(self, tmp_path):
        """Test extraction of metadata from comments."""
        tex_file = tmp_path / "question.tex"
        tex_file.write_text("""
% chapter: Mechanics
% topic: Kinematics
% difficulty: medium
% type: mcq_sc
% tags: motion, acceleration, graphs

\\item A car moves with velocity $v = 20$ m/s.
\\begin{tasks}(2)
    \\task $10$ m
    \\task $20$ m
\\end{tasks}
""")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract(tex_file)
        
        assert metadata.chapter == "Mechanics"
        assert metadata.topic == "Kinematics"
        assert metadata.difficulty == "medium"
        assert metadata.question_type == "mcq_sc"
        assert metadata.tags == ["motion", "acceleration", "graphs"]
    
    def test_infer_question_type_mcq_sc(self, tmp_path):
        """Test inference of MCQ single correct type."""
        tex_file = tmp_path / "question.tex"
        tex_file.write_text("""
\\item A car moves with velocity $v = 20$ m/s.
\\begin{tasks}(2)
    \\task $10$ m
    \\task $20$ m
\\end{tasks}
""")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract(tex_file)
        
        assert metadata.question_type == "mcq_sc"
    
    def test_infer_question_type_mcq_mc(self, tmp_path):
        """Test inference of MCQ multiple correct type."""
        tex_file = tmp_path / "question.tex"
        tex_file.write_text("""
\\item Select one or more correct answers.
\\begin{tasks}(2)
    \\task $10$ m
    \\task $20$ m
\\end{tasks}
""")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract(tex_file)
        
        assert metadata.question_type == "mcq_mc"
    
    def test_infer_question_type_subjective(self, tmp_path):
        """Test inference of subjective type."""
        tex_file = tmp_path / "question.tex"
        tex_file.write_text("""
\\item Derive the equation of motion for a particle.
\\begin{solution}
The equation is $F = ma$.
\\end{solution}
""")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract(tex_file)
        
        assert metadata.question_type == "subjective"
    
    def test_infer_difficulty(self, tmp_path):
        """Test difficulty inference from content."""
        # Easy question (few math expressions)
        tex_file = tmp_path / "easy.tex"
        tex_file.write_text("\\item What is $F = ma$?")
        
        extractor = MetadataExtractor()
        metadata = extractor.extract(tex_file)
        
        assert metadata.difficulty in ["easy", "medium", "hard"]


class TestMetadataStore:
    """Test metadata storage and querying."""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary metadata store."""
        db_path = tmp_path / "test.db"
        with MetadataStore(db_path) as store:
            yield store
    
    def test_upsert_and_get(self, store):
        """Test inserting and retrieving metadata."""
        metadata = QuestionMetadata(
            file_path="/path/to/question.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="medium",
            question_type="mcq_sc",
            tags=["motion", "graphs"],
        )
        
        store.upsert(metadata)
        
        result = store.get_by_path("/path/to/question.tex")
        
        assert result is not None
        assert result.chapter == "Mechanics"
        assert result.topic == "Kinematics"
        assert result.difficulty == "medium"
        assert result.question_type == "mcq_sc"
        assert result.tags == ["motion", "graphs"]
    
    def test_upsert_updates_existing(self, store):
        """Test that upsert updates existing records."""
        metadata1 = QuestionMetadata(
            file_path="/path/to/question.tex",
            chapter="Mechanics",
            topic="Kinematics",
        )
        
        store.upsert(metadata1)
        
        metadata2 = QuestionMetadata(
            file_path="/path/to/question.tex",
            chapter="Mechanics",
            topic="Dynamics",  # Changed
        )
        
        store.upsert(metadata2)
        
        result = store.get_by_path("/path/to/question.tex")
        
        assert result.topic == "Dynamics"
    
    def test_query_by_topic(self, store):
        """Test querying by topic."""
        store.upsert(QuestionMetadata(
            file_path="/path/to/q1.tex",
            topic="Kinematics",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q2.tex",
            topic="Dynamics",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q3.tex",
            topic="Kinematics",
        ))
        
        results = store.query(topic="Kinematics")
        
        assert len(results) == 2
        assert all(r.topic == "Kinematics" for r in results)
    
    def test_query_by_difficulty(self, store):
        """Test querying by difficulty."""
        store.upsert(QuestionMetadata(
            file_path="/path/to/q1.tex",
            difficulty="easy",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q2.tex",
            difficulty="medium",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q3.tex",
            difficulty="easy",
        ))
        
        results = store.query(difficulty="easy")
        
        assert len(results) == 2
        assert all(r.difficulty == "easy" for r in results)
    
    def test_query_by_multiple_filters(self, store):
        """Test querying with multiple filters."""
        store.upsert(QuestionMetadata(
            file_path="/path/to/q1.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="easy",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q2.tex",
            chapter="Mechanics",
            topic="Dynamics",
            difficulty="easy",
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q3.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="medium",
        ))
        
        results = store.query(
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="easy",
        )
        
        assert len(results) == 1
        assert results[0].file_path == "/path/to/q1.tex"
    
    def test_query_by_tags(self, store):
        """Test querying by tags."""
        store.upsert(QuestionMetadata(
            file_path="/path/to/q1.tex",
            tags=["motion", "graphs"],
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q2.tex",
            tags=["motion", "acceleration"],
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q3.tex",
            tags=["graphs", "velocity"],
        ))
        
        results = store.query(tags=["motion"])
        
        assert len(results) == 2
        
        results = store.query(tags=["motion", "graphs"])
        
        assert len(results) == 1
        assert results[0].file_path == "/path/to/q1.tex"
    
    def test_query_with_limit(self, store):
        """Test query limit."""
        for i in range(10):
            store.upsert(QuestionMetadata(
                file_path=f"/path/to/q{i}.tex",
                topic="Kinematics",
            ))
        
        results = store.query(topic="Kinematics", limit=5)
        
        assert len(results) == 5
    
    def test_update_usage(self, store):
        """Test updating usage statistics."""
        metadata = QuestionMetadata(
            file_path="/path/to/question.tex",
            usage_count=0,
        )
        
        store.upsert(metadata)
        
        store.update_usage("/path/to/question.tex")
        
        result = store.get_by_path("/path/to/question.tex")
        
        assert result.usage_count == 1
        assert result.last_used is not None
        
        store.update_usage("/path/to/question.tex")
        
        result = store.get_by_path("/path/to/question.tex")
        
        assert result.usage_count == 2
    
    def test_get_statistics(self, store):
        """Test getting aggregate statistics."""
        store.upsert(QuestionMetadata(
            file_path="/path/to/q1.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="easy",
            question_type="mcq_sc",
            usage_count=5,
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q2.tex",
            chapter="Mechanics",
            topic="Dynamics",
            difficulty="medium",
            question_type="mcq_mc",
            usage_count=3,
        ))
        store.upsert(QuestionMetadata(
            file_path="/path/to/q3.tex",
            chapter="Thermodynamics",
            topic="Heat Transfer",
            difficulty="hard",
            question_type="subjective",
            usage_count=0,
        ))
        
        stats = store.get_statistics()
        
        assert stats["total_questions"] == 3
        assert stats["by_chapter"]["Mechanics"] == 2
        assert stats["by_chapter"]["Thermodynamics"] == 1
        assert stats["by_difficulty"]["easy"] == 1
        assert stats["by_difficulty"]["medium"] == 1
        assert stats["by_difficulty"]["hard"] == 1
        assert stats["by_topic"]["Kinematics"] == 1
        assert stats["by_topic"]["Dynamics"] == 1
        assert stats["by_type"]["mcq_sc"] == 1
        assert stats["by_type"]["mcq_mc"] == 1
        assert stats["by_type"]["subjective"] == 1
        assert len(stats["most_used"]) == 2  # Only questions with usage > 0
        assert len(stats["least_used"]) == 1  # Questions with usage = 0
    
    def test_index_directory(self, tmp_path, store):
        """Test indexing a directory of LaTeX files."""
        # Create test files
        questions_dir = tmp_path / "questions"
        questions_dir.mkdir()
        
        (questions_dir / "q1.tex").write_text("""
% chapter: Mechanics
% topic: Kinematics
% difficulty: easy

\\item Question 1
""")
        
        (questions_dir / "q2.tex").write_text("""
% chapter: Mechanics
% topic: Dynamics
% difficulty: medium

\\item Question 2
""")
        
        (questions_dir / "q3.tex").write_text("""
% chapter: Thermodynamics
% topic: Heat Transfer
% difficulty: hard

\\item Question 3
""")
        
        count = store.index_directory(questions_dir)
        
        assert count == 3
        
        # Verify all files were indexed
        results = store.query()
        assert len(results) == 3
        
        # Verify metadata was extracted
        q1 = store.get_by_path(str(questions_dir / "q1.tex"))
        assert q1.chapter == "Mechanics"
        assert q1.topic == "Kinematics"
        assert q1.difficulty == "easy"
    
    def test_index_directory_recursive(self, tmp_path, store):
        """Test recursive directory indexing."""
        # Create nested structure
        questions_dir = tmp_path / "questions"
        mechanics_dir = questions_dir / "mechanics"
        mechanics_dir.mkdir(parents=True)
        
        (mechanics_dir / "q1.tex").write_text("\\item Question 1")
        (questions_dir / "q2.tex").write_text("\\item Question 2")
        
        count = store.index_directory(questions_dir, recursive=True)
        
        assert count == 2
    
    def test_index_directory_non_recursive(self, tmp_path, store):
        """Test non-recursive directory indexing."""
        # Create nested structure
        questions_dir = tmp_path / "questions"
        mechanics_dir = questions_dir / "mechanics"
        mechanics_dir.mkdir(parents=True)
        
        (mechanics_dir / "q1.tex").write_text("\\item Question 1")
        (questions_dir / "q2.tex").write_text("\\item Question 2")
        
        count = store.index_directory(questions_dir, recursive=False)
        
        assert count == 1  # Only q2.tex in root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
