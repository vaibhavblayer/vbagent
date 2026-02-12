"""Helper functions for populating database records with agent metadata."""

from typing import Optional
from vbagent.models.classification_v2 import (
    DiagramAnalysis,
    DifficultyAssessment,
    ClassificationResult,
)
from vbagent.database.store import QuestionRecord


def populate_diagram_metadata(
    record: QuestionRecord,
    diagram: DiagramAnalysis
) -> QuestionRecord:
    """Populate record with Agent 2 (Diagram Analysis) metadata.
    
    Args:
        record: QuestionRecord to update
        diagram: DiagramAnalysis from Agent 2
        
    Returns:
        Updated QuestionRecord
    """
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
    """Populate record with Agent 3 (Difficulty Assessment) metadata.
    
    Args:
        record: QuestionRecord to update
        difficulty: DifficultyAssessment from Agent 3
        
    Returns:
        Updated QuestionRecord
    """
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


def populate_from_classification_result(
    record: QuestionRecord,
    classification: ClassificationResult
) -> QuestionRecord:
    """Populate record from complete ClassificationResult (v2).
    
    Args:
        record: QuestionRecord to update
        classification: Complete ClassificationResult with all agent data
        
    Returns:
        Updated QuestionRecord
    """
    # Basic classification
    record.subject = classification.subject if hasattr(classification, 'subject') else record.subject
    record.question_type = classification.question_type
    record.chapter = classification.chapter
    record.topic = classification.topic
    record.subtopic = classification.subtopic
    record.has_diagram = classification.has_diagram
    record.num_options = classification.num_options
    record.key_concepts = classification.key_concepts
    record.requires_calculus = classification.requires_calculus
    record.confidence = classification.confidence
    
    # Agent 2 metadata (if available)
    if classification.diagram_category:
        record.diagram_category = classification.diagram_category
        record.diagram_complexity = classification.diagram_complexity
        record.diagram_elements = classification.diagram_elements
        record.suggested_tikz_agent = classification.suggested_tikz_agent
        
        if classification.tikz_requirements:
            record.tikz_libraries = classification.tikz_requirements.libraries
    
    # Agent 3 metadata (if available)
    if classification.difficulty:
        record.difficulty = classification.difficulty
        record.difficulty_score = classification.difficulty_score
        record.difficulty_reasoning = classification.difficulty_reasoning
        record.expected_solve_time_minutes = classification.expected_solve_time_minutes
        record.expected_error_rate = classification.expected_error_rate
        record.prerequisite_concepts = classification.prerequisite_concepts
        record.common_mistakes = classification.common_mistakes
        record.cognitive_level = classification.cognitive_level
        record.solution_approach = classification.solution_approach
        record.required_formulas = classification.required_formulas
        record.learning_objectives = classification.learning_objectives
        record.tags_auto = classification.tags_auto
        
        if classification.exam_relevance:
            record.exam_relevance = {
                'jee_main': classification.exam_relevance.jee_main,
                'jee_advanced': classification.exam_relevance.jee_advanced,
                'neet': classification.exam_relevance.neet,
            }
    
    return record
