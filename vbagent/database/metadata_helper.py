"""Helper functions for populating database records with agent metadata."""

from typing import Optional
from vbagent.models.classification import (
    DiagramAnalysis,
    DifficultyAssessment,
    ClassificationResult,
)
from vbagent.models.metadata import TaxonomyClassification
from vbagent.database.store import QuestionRecord


def populate_diagram_metadata(
    record: QuestionRecord,
    diagram: DiagramAnalysis
) -> QuestionRecord:
    """Populate record with Agent 2 (Diagram Analysis) metadata."""
    record.diagram_category = diagram.diagram_category
    record.diagram_complexity = diagram.diagram_complexity
    record.diagram_elements = diagram.diagram_elements
    record.suggested_tikz_agent = diagram.suggested_tikz_agent

    if diagram.tikz_requirements:
        record.tikz_libraries = diagram.tikz_requirements.libraries

    return record


def populate_difficulty_metadata(
    record: QuestionRecord,
    difficulty: DifficultyAssessment
) -> QuestionRecord:
    """Populate record with Agent 3 (Difficulty Assessment) metadata."""
    record.difficulty = difficulty.difficulty
    record.difficulty_score = difficulty.difficulty_score
    record.difficulty_reasoning = difficulty.difficulty_reasoning
    record.expected_solve_time_minutes = difficulty.expected_solve_time_minutes
    record.expected_error_rate = difficulty.expected_error_rate
    record.prerequisite_concepts = difficulty.prerequisite_concepts
    record.common_mistakes = difficulty.common_mistakes
    record.cognitive_level = difficulty.cognitive_level
    record.solution_approach = difficulty.solution_approach
    record.required_formulas = difficulty.required_formulas
    record.learning_objectives = difficulty.learning_objectives
    record.tags_auto = difficulty.tags_auto

    if difficulty.exam_relevance:
        record.exam_relevance = {
            'jee_main': difficulty.exam_relevance.jee_main,
            'jee_advanced': difficulty.exam_relevance.jee_advanced,
            'neet': difficulty.exam_relevance.neet,
        }

    return record


def populate_taxonomy_metadata(
    record: QuestionRecord,
    taxonomy: TaxonomyClassification
) -> QuestionRecord:
    """Populate record with Stage 4 (Taxonomy) metadata."""
    record.chapter = taxonomy.chapter
    record.topic = taxonomy.topic
    record.subtopic = taxonomy.subtopic
    record.key_concepts = taxonomy.key_concepts or []
    return record


def populate_from_classification_result(
    record: QuestionRecord,
    classification: ClassificationResult,
    difficulty: Optional[DifficultyAssessment] = None,
    taxonomy: Optional[TaxonomyClassification] = None,
) -> QuestionRecord:
    """Populate record from ClassificationResult + optional difficulty/taxonomy.

    Args:
        record: QuestionRecord to update
        classification: Classification with core + diagram data
        difficulty: Optional DifficultyAssessment from Agent 3
        taxonomy: Optional TaxonomyClassification from Stage 4
    """
    # Core classification (Agent 1/4)
    record.subject = classification.subject
    record.question_type = classification.question_type
    record.has_diagram = classification.has_diagram
    record.confidence = classification.confidence

    # Agent 2 diagram metadata (if available)
    if classification.diagram_category:
        record.diagram_category = classification.diagram_category
        record.diagram_complexity = classification.diagram_complexity
        record.diagram_elements = classification.diagram_elements or []
        record.suggested_tikz_agent = classification.suggested_tikz_agent
        record.diagram_type = classification.diagram_type

        if classification.tikz_requirements:
            record.tikz_libraries = classification.tikz_requirements.libraries or []

    # Agent 3 difficulty (if provided)
    if difficulty:
        populate_difficulty_metadata(record, difficulty)

    # Stage 4 taxonomy (if provided)
    if taxonomy:
        populate_taxonomy_metadata(record, taxonomy)

    return record
