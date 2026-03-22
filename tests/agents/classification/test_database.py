"""Tests for database integration."""

import pytest
import tempfile
from pathlib import Path

from vbagent.database.store import QuestionDatabase, QuestionRecord
from vbagent.database.metadata_helper import (
    populate_from_classification_result,
    populate_diagram_metadata,
    populate_difficulty_metadata,
)
from vbagent.models.classification import (
    ClassificationResult,
    DiagramAnalysis,
    DifficultyAssessment,
)


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


def test_database_creation(temp_db):
    """Test database creation."""
    with QuestionDatabase(temp_db) as db:
        assert db.conn is not None


def test_insert_and_retrieve(temp_db):
    """Test inserting and retrieving records."""
    with QuestionDatabase(temp_db) as db:
        record = QuestionRecord(
            file_path="test.tex",
            question_type="mcq_sc",
            subject="physics",
            problem_latex="Test problem"
        )
        
        record_id = db.insert(record)
        assert record_id > 0
        
        retrieved = db.get_by_id(record_id)
        assert retrieved is not None
        assert retrieved.file_path == "test.tex"


def test_agent2_metadata_storage(temp_db):
    """Test storing Agent 2 metadata."""
    with QuestionDatabase(temp_db) as db:
        record = QuestionRecord(
            file_path="test.tex",
            problem_latex="Test",
            diagram_category="mechanics",
            diagram_complexity="simple",
            diagram_elements=["force", "vector"],
            suggested_tikz_agent="fbd",
            tikz_libraries=["arrows.meta"]
        )
        
        record_id = db.insert(record)
        retrieved = db.get_by_id(record_id)
        
        assert retrieved.diagram_category == "mechanics"
        assert retrieved.suggested_tikz_agent == "fbd"
        assert len(retrieved.diagram_elements) == 2


def test_agent3_metadata_storage(temp_db):
    """Test storing Agent 3 metadata."""
    with QuestionDatabase(temp_db) as db:
        record = QuestionRecord(
            file_path="test.tex",
            problem_latex="Test",
            difficulty_score=5.5,
            difficulty_reasoning="Test reasoning",
            expected_solve_time_minutes=5,
            prerequisite_concepts=["Newton's laws"],
            common_mistakes=["Sign errors"],
            cognitive_level="apply"
        )
        
        record_id = db.insert(record)
        retrieved = db.get_by_id(record_id)
        
        assert retrieved.difficulty_score == 5.5
        assert retrieved.cognitive_level == "apply"
        assert len(retrieved.prerequisite_concepts) == 1


def test_populate_from_classification(temp_db):
    """Test populating record from classification."""
    classification = ClassificationResult(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True,
        diagram_category="mechanics",
    )
    
    record = QuestionRecord(
        file_path="test.tex",
        problem_latex="Test"
    )
    
    record = populate_from_classification_result(record, classification)
    
    assert record.subject == "physics"
    assert record.diagram_category == "mechanics"


def test_backward_compatibility(temp_db):
    """Test backward compatibility with old records."""
    with QuestionDatabase(temp_db) as db:
        # Insert record without new fields
        record = QuestionRecord(
            file_path="old.tex",
            question_type="mcq_sc",
            problem_latex="Old problem"
        )
        
        record_id = db.insert(record)
        retrieved = db.get_by_id(record_id)
        
        # New fields should be None or empty
        assert retrieved.diagram_category is None
        assert retrieved.difficulty_score is None
        assert len(retrieved.prerequisite_concepts) == 0
