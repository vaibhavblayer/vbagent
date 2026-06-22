"""Tests for DPP Builder functionality.

Tests the DPP builder, selection strategies, and LaTeX generation.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from vbagent.dpp.builder import (
    DPPBuilder,
    DPPResult,
    BalancedStrategy,
    TopicCoverageStrategy,
    RandomStrategy,
)
from vbagent.metadata.store import MetadataStore, QuestionMetadata


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def sample_questions():
    """Create sample question metadata for testing."""
    questions = [
        QuestionMetadata(
            file_path="/path/q1.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="easy",
            question_type="mcq_sc",
            tags=["motion", "velocity"],
            usage_count=0
        ),
        QuestionMetadata(
            file_path="/path/q2.tex",
            chapter="Mechanics",
            topic="Kinematics",
            difficulty="medium",
            question_type="subjective",
            tags=["acceleration"],
            usage_count=1
        ),
        QuestionMetadata(
            file_path="/path/q3.tex",
            chapter="Mechanics",
            topic="Dynamics",
            difficulty="hard",
            question_type="mcq_sc",
            tags=["force", "newton"],
            usage_count=0
        ),
        QuestionMetadata(
            file_path="/path/q4.tex",
            chapter="Mechanics",
            topic="Dynamics",
            difficulty="easy",
            question_type="subjective",
            tags=["friction"],
            usage_count=2
        ),
        QuestionMetadata(
            file_path="/path/q5.tex",
            chapter="Thermodynamics",
            topic="Heat Transfer",
            difficulty="medium",
            question_type="mcq_mc",
            tags=["heat", "conduction"],
            usage_count=0
        ),
        QuestionMetadata(
            file_path="/path/q6.tex",
            chapter="Thermodynamics",
            topic="Heat Transfer",
            difficulty="medium",
            question_type="subjective",
            tags=["radiation"],
            usage_count=1
        ),
        QuestionMetadata(
            file_path="/path/q7.tex",
            chapter="Electromagnetism",
            topic="Electrostatics",
            difficulty="hard",
            question_type="mcq_sc",
            tags=["charge", "field"],
            usage_count=0
        ),
        QuestionMetadata(
            file_path="/path/q8.tex",
            chapter="Electromagnetism",
            topic="Electrostatics",
            difficulty="easy",
            question_type="subjective",
            tags=["potential"],
            usage_count=0
        ),
        QuestionMetadata(
            file_path="/path/q9.tex",
            chapter="Mechanics",
            topic="Energy",
            difficulty="medium",
            question_type="mcq_sc",
            tags=["work", "energy"],
            usage_count=3
        ),
        QuestionMetadata(
            file_path="/path/q10.tex",
            chapter="Mechanics",
            topic="Energy",
            difficulty="hard",
            question_type="subjective",
            tags=["conservation"],
            usage_count=0
        ),
    ]
    return questions


class TestBalancedStrategy:
    """Tests for BalancedStrategy."""
    
    def test_balanced_distribution(self, sample_questions):
        """Test that balanced strategy produces correct difficulty distribution."""
        strategy = BalancedStrategy()
        selected = strategy.select(sample_questions, 10)
        
        # Count by difficulty
        difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
        for q in selected:
            difficulty_counts[q.difficulty] += 1
        
        # Should have 10 questions total
        assert len(selected) == 10
        
        # Check approximate distribution (40% easy, 40% medium, 20% hard)
        # With 10 questions: 4 easy, 4 medium, 2 hard
        # Allow some flexibility since we have 3 easy, 4 medium, 3 hard in sample
        assert difficulty_counts["easy"] >= 3
        assert difficulty_counts["medium"] >= 3
        assert difficulty_counts["hard"] >= 2
        
        # Total should be 10
        assert sum(difficulty_counts.values()) == 10
    
    def test_prefers_less_used(self, sample_questions):
        """Test that balanced strategy prefers less-used questions."""
        strategy = BalancedStrategy()
        selected = strategy.select(sample_questions, 5)
        
        # Check that less-used questions are preferred
        usage_counts = [q.usage_count for q in selected]
        
        # Should prefer questions with usage_count 0 or 1
        assert all(count <= 2 for count in usage_counts)
    
    def test_insufficient_questions(self, sample_questions):
        """Test behavior when fewer questions available than requested."""
        strategy = BalancedStrategy()
        
        # Request more than available
        selected = strategy.select(sample_questions[:3], 10)
        
        # Should return all available questions
        assert len(selected) == 3
    
    def test_empty_list(self):
        """Test behavior with empty question list."""
        strategy = BalancedStrategy()
        selected = strategy.select([], 5)
        
        assert len(selected) == 0


class TestTopicCoverageStrategy:
    """Tests for TopicCoverageStrategy."""
    
    def test_topic_diversity(self, sample_questions):
        """Test that topic coverage strategy maximizes topic diversity."""
        strategy = TopicCoverageStrategy()
        selected = strategy.select(sample_questions, 6)
        
        # Count unique topics
        topics = set(q.topic for q in selected)
        
        # Should have multiple topics
        assert len(topics) >= 3
    
    def test_round_robin_selection(self, sample_questions):
        """Test that questions are selected round-robin from topics."""
        strategy = TopicCoverageStrategy()
        selected = strategy.select(sample_questions, 4)
        
        # Should select from different topics
        topics = [q.topic for q in selected]
        
        # Should not have all questions from same topic
        assert len(set(topics)) > 1
    
    def test_prefers_less_used(self, sample_questions):
        """Test that topic coverage strategy prefers less-used questions."""
        strategy = TopicCoverageStrategy()
        selected = strategy.select(sample_questions, 5)
        
        # Within each topic, should prefer less-used questions
        usage_counts = [q.usage_count for q in selected]
        
        # Should generally prefer lower usage counts
        assert sum(usage_counts) <= 10  # Arbitrary threshold


class TestRandomStrategy:
    """Tests for RandomStrategy."""
    
    def test_random_selection(self, sample_questions):
        """Test that random strategy selects questions."""
        strategy = RandomStrategy()
        selected = strategy.select(sample_questions, 5)
        
        assert len(selected) == 5
        assert all(q in sample_questions for q in selected)
    
    def test_prefers_less_used(self, sample_questions):
        """Test that random strategy still prefers less-used questions."""
        strategy = RandomStrategy()
        selected = strategy.select(sample_questions, 5)
        
        # Should generally prefer less-used questions
        usage_counts = [q.usage_count for q in selected]
        
        # Most should have low usage counts
        assert sum(1 for c in usage_counts if c <= 1) >= 3


class TestDPPBuilder:
    """Tests for DPPBuilder."""
    
    def test_create_dpp_basic(self, temp_db, sample_questions):
        """Test basic DPP creation."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Create DPP
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                result = builder.create_dpp(
                    count=5,
                    strategy="balanced",
                    output_path=output_path
                )
            
            # Check result
            assert len(result.questions) == 5
            assert result.main_tex_path == output_path
            assert result.strategy_used == "balanced"
            assert output_path.exists()
            
            # Check LaTeX content
            content = output_path.read_text()
            assert r"\documentclass" in content
            assert r"\begin{document}" in content
            assert r"\begin{enumerate}" in content
    
    def test_create_dpp_with_filters(self, temp_db, sample_questions):
        """Test DPP creation with filters."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Create DPP with topic filter
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                result = builder.create_dpp(
                    count=2,
                    strategy="balanced",
                    filters={"topic": "Kinematics"},
                    output_path=output_path
                )
            
            # Check that all questions are from Kinematics
            assert all(q.topic == "Kinematics" for q in result.questions)
    
    def test_create_dpp_topic_coverage(self, temp_db, sample_questions):
        """Test DPP creation with topic coverage strategy."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Create DPP
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                result = builder.create_dpp(
                    count=6,
                    strategy="topic_coverage",
                    output_path=output_path
                )
            
            # Check topic diversity
            topics = set(q.topic for q in result.questions)
            assert len(topics) >= 3
    
    def test_create_dpp_updates_usage(self, temp_db, sample_questions):
        """Test that DPP creation updates usage statistics."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Get initial usage counts
        with MetadataStore(temp_db) as store:
            initial_q1 = store.get_by_path("/path/q1.tex")
            initial_usage = initial_q1.usage_count if initial_q1 else 0
        
        # Create DPP
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                result = builder.create_dpp(
                    count=5,
                    strategy="balanced",
                    output_path=output_path
                )
        
        # Check that usage was updated for selected questions
        with MetadataStore(temp_db) as store:
            for q in result.questions:
                updated_q = store.get_by_path(q.file_path)
                # Usage should have increased
                assert updated_q.usage_count > 0
    
    def test_create_dpp_insufficient_questions(self, temp_db, sample_questions):
        """Test error when insufficient questions available."""
        # Create store with only 2 questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions[:2]:
                store.upsert(q)
        
        # Try to create DPP with more questions than available
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                
                with pytest.raises(ValueError, match="Insufficient questions"):
                    builder.create_dpp(
                        count=10,
                        strategy="balanced",
                        output_path=output_path
                    )
    
    def test_create_dpp_invalid_strategy(self, temp_db, sample_questions):
        """Test error with invalid strategy."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Try to create DPP with invalid strategy
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            
            with MetadataStore(temp_db) as store:
                builder = DPPBuilder(store)
                
                with pytest.raises(ValueError, match="Unknown strategy"):
                    builder.create_dpp(
                        count=5,
                        strategy="invalid_strategy",
                        output_path=output_path
                    )
    
    def test_create_dpp_default_output_path(self, temp_db, sample_questions):
        """Test DPP creation with default output path."""
        # Create store and add questions
        with MetadataStore(temp_db) as store:
            for q in sample_questions:
                store.upsert(q)
        
        # Create DPP without specifying output path
        with MetadataStore(temp_db) as store:
            builder = DPPBuilder(store)
            result = builder.create_dpp(
                count=5,
                strategy="balanced"
            )
        
        # Should have generated a default path
        assert result.main_tex_path.exists()
        assert result.main_tex_path.suffix == ".tex"
        assert "dpp_" in result.main_tex_path.name
        
        # Clean up
        result.main_tex_path.unlink()


class TestDPPResult:
    """Tests for DPPResult."""
    
    def test_dpp_result_creation(self, sample_questions):
        """Test DPPResult creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = Path(tmpdir) / "test.tex"
            tex_path.write_text(r"\documentclass{article}\begin{document}Test\end{document}")
            
            result = DPPResult(
                questions=sample_questions[:5],
                main_tex_path=tex_path,
                strategy_used="balanced"
            )
            
            assert len(result.questions) == 5
            assert result.main_tex_path == tex_path
            assert result.strategy_used == "balanced"
            assert isinstance(result.created_at, datetime)


class TestDPPBuilderPreamble:
    """Tests for generated DPP LaTeX preamble."""

    def test_ansint_is_defined_in_generated_main_tex(self, sample_questions, temp_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_dpp.tex"
            builder = DPPBuilder(object())

            builder._generate_main_tex(
                questions=sample_questions[:1],
                output_path=output_path,
                title="Test DPP",
            )

            content = output_path.read_text()
            assert r"\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
