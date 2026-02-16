"""Models for Stage 4 (Taxonomy) and combined metadata.

Stage 5 (Difficulty) uses the comprehensive DifficultyAssessment from classification.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from vbagent.models.classification import DifficultyAssessment


# Stage 4: Taxonomy Classification
class TaxonomyClassification(BaseModel):
    """Output from Stage 4: Taxonomy Classifier (uses structured output)"""
    model_config = ConfigDict(extra='forbid')
    
    chapter: str = Field(description="Chapter from predefined taxonomy")
    topic: str = Field(description="Topic from predefined taxonomy")
    subtopic: str = Field(description="Subtopic from predefined taxonomy")
    key_concepts: list[str] = Field(
        default_factory=list,
        description="Refined list of key concepts"
    )
    prerequisite_concepts: list[str] = Field(
        default_factory=list,
        description="Concepts student should know beforehand"
    )
    related_topics: list[str] = Field(
        default_factory=list,
        description="Related topics from curriculum"
    )
    cognitive_level: Literal[
        "remember", "understand", "apply",
        "analyze", "evaluate", "create"
    ] = Field(default="apply", description="Bloom's taxonomy level")
    exam_relevance: list[str] = Field(
        default_factory=list,
        description="Relevant exams (JEE Main, JEE Advanced, NEET, etc.)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="Confidence in classification"
    )
    classified_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


# Combined metadata (Stage 4 + Stage 5)
class EnrichedMetadata(BaseModel):
    """Combined output from Stage 4 and Stage 5.
    
    Uses the comprehensive DifficultyAssessment from classification.
    """
    model_config = ConfigDict(extra='forbid')
    
    taxonomy: TaxonomyClassification
    difficulty: DifficultyAssessment
    
    def to_dict(self) -> dict:
        """Convert to flat dictionary for database storage"""
        return {
            # Taxonomy fields
            "chapter": self.taxonomy.chapter,
            "topic": self.taxonomy.topic,
            "subtopic": self.taxonomy.subtopic,
            "key_concepts": self.taxonomy.key_concepts,
            "prerequisite_concepts": self.taxonomy.prerequisite_concepts,
            "related_topics": self.taxonomy.related_topics,
            "cognitive_level": self.taxonomy.cognitive_level,
            "exam_relevance": self.taxonomy.exam_relevance,
            
            # Difficulty fields (comprehensive from v2)
            "difficulty": self.difficulty.difficulty,
            "difficulty_score": self.difficulty.difficulty_score,
            "difficulty_reasoning": self.difficulty.difficulty_reasoning,
            "expected_solve_time_minutes": self.difficulty.expected_solve_time_minutes,
            "expected_error_rate": self.difficulty.expected_error_rate,
            "common_mistakes": self.difficulty.common_mistakes,
            "solution_approach": self.difficulty.solution_approach,
            "required_formulas": self.difficulty.required_formulas,
            "learning_objectives": self.difficulty.learning_objectives,
            "tags_auto": self.difficulty.tags_auto,
            
            # Difficulty factors (nested)
            "difficulty_factors": {
                "concept_complexity": self.difficulty.difficulty_factors.concept_complexity,
                "calculation_complexity": self.difficulty.difficulty_factors.calculation_complexity,
                "multi_step": self.difficulty.difficulty_factors.multi_step,
                "requires_visualization": self.difficulty.difficulty_factors.requires_visualization,
                "formula_complexity": self.difficulty.difficulty_factors.formula_complexity,
                "diagram_complexity": self.difficulty.difficulty_factors.diagram_complexity,
            },
            
            # Problem structure (nested)
            "problem_structure": {
                "has_given_data": self.difficulty.problem_structure.has_given_data,
                "has_find_statement": self.difficulty.problem_structure.has_find_statement,
                "has_constraints": self.difficulty.problem_structure.has_constraints,
                "is_multi_part": self.difficulty.problem_structure.is_multi_part,
            },
            
            # Exam relevance (nested)
            "exam_relevance_scores": {
                "jee_main": self.difficulty.exam_relevance.jee_main,
                "jee_advanced": self.difficulty.exam_relevance.jee_advanced,
                "neet": self.difficulty.exam_relevance.neet,
            },
        }


__all__ = [
    "TaxonomyClassification",
    "EnrichedMetadata",
]
