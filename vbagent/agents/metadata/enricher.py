"""Parallel execution of Stage 4 (Taxonomy) and Stage 5 (Difficulty).

Runs both metadata enrichment agents simultaneously for efficiency.
Uses the existing comprehensive difficulty assessor from classification pipeline.
"""

import asyncio
from typing import Optional

from vbagent.agents.classification.taxonomy_classifier import classify_taxonomy
from vbagent.agents.classification.difficulty_assessor import assess_difficulty
from vbagent.models.classification import (
    DifficultyAssessment,
    PrimaryClassification,
)
from vbagent.models.metadata import TaxonomyClassification, EnrichedMetadata
from vbagent.config import get_config


async def _classify_taxonomy_async(
    latex_problem: str,
    latex_solution: Optional[str],
    tikz_code: Optional[str],
    question_type: Optional[str],
    key_concepts: Optional[list[str]],
    requires_calculus: bool,
    subject: Optional[str],
) -> TaxonomyClassification:
    """Async wrapper for taxonomy classification."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        classify_taxonomy,
        latex_problem,
        latex_solution,
        tikz_code,
        question_type,
        key_concepts,
        requires_calculus,
        subject,
    )


async def _assess_difficulty_async(
    latex_content: str,
    primary: PrimaryClassification,
    tikz_code: Optional[str],
    subject: Optional[str],
) -> DifficultyAssessment:
    """Async wrapper for difficulty assessment."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        assess_difficulty,
        latex_content,
        primary,
        None,  # diagram - not available in this flow
        tikz_code,
        subject,
        False,  # show_spinner - disable for parallel execution
    )


async def enrich_metadata_parallel(
    latex_problem: str,
    latex_solution: Optional[str] = None,
    tikz_code: Optional[str] = None,
    question_type: Optional[str] = None,
    key_concepts: Optional[list[str]] = None,
    requires_calculus: bool = False,
    subject: Optional[str] = None,
) -> EnrichedMetadata:
    """Run Stage 4 and Stage 5 in parallel.
    
    Args:
        latex_problem: LaTeX problem statement
        latex_solution: LaTeX solution (optional)
        tikz_code: TikZ diagram code (optional)
        question_type: Question type from Stage 1 (optional)
        key_concepts: Key concepts from Stage 1 (optional)
        requires_calculus: Whether problem requires calculus
        subject: Subject name (defaults to config)
        
    Returns:
        EnrichedMetadata with both taxonomy and difficulty
    """
    if subject is None:
        subject = get_config().subject
    
    # Combine problem and solution for difficulty assessment
    latex_content = latex_problem
    if latex_solution:
        latex_content += f"\n\n**Solution:**\n{latex_solution}"
    
    # Create a minimal PrimaryClassification for difficulty assessor
    # (it expects this object)
    primary = PrimaryClassification(
        subject=subject,
        question_type=question_type or "subjective",
        chapter="",  # Will be filled by taxonomy
        topic="",    # Will be filled by taxonomy
        subtopic="",
        has_diagram=bool(tikz_code),
        key_concepts=key_concepts or [],
        requires_calculus=requires_calculus,
        classified_from="latex",
    )
    
    # Run both stages in parallel
    taxonomy_task = _classify_taxonomy_async(
        latex_problem,
        latex_solution,
        tikz_code,
        question_type,
        key_concepts,
        requires_calculus,
        subject,
    )
    
    difficulty_task = _assess_difficulty_async(
        latex_content,
        primary,
        tikz_code,
        subject,
    )
    
    # Wait for both to complete
    taxonomy, difficulty = await asyncio.gather(taxonomy_task, difficulty_task)
    
    return EnrichedMetadata(taxonomy=taxonomy, difficulty=difficulty)


def enrich_metadata_sync(
    latex_problem: str,
    latex_solution: Optional[str] = None,
    tikz_code: Optional[str] = None,
    question_type: Optional[str] = None,
    key_concepts: Optional[list[str]] = None,
    requires_calculus: bool = False,
    subject: Optional[str] = None,
) -> EnrichedMetadata:
    """Synchronous wrapper for parallel metadata enrichment.
    
    Args:
        Same as enrich_metadata_parallel
        
    Returns:
        EnrichedMetadata with both taxonomy and difficulty
    """
    return asyncio.run(
        enrich_metadata_parallel(
            latex_problem,
            latex_solution,
            tikz_code,
            question_type,
            key_concepts,
            requires_calculus,
            subject,
        )
    )


def enrich_metadata_sequential(
    latex_problem: str,
    latex_solution: Optional[str] = None,
    tikz_code: Optional[str] = None,
    question_type: Optional[str] = None,
    key_concepts: Optional[list[str]] = None,
    requires_calculus: bool = False,
    subject: Optional[str] = None,
) -> EnrichedMetadata:
    """Run Stage 4 then Stage 5 sequentially (Stage 5 can use taxonomy).
    
    Args:
        Same as enrich_metadata_parallel
        
    Returns:
        EnrichedMetadata with both taxonomy and difficulty
    """
    if subject is None:
        subject = get_config().subject
    
    # Stage 4: Taxonomy
    taxonomy = classify_taxonomy(
        latex_problem,
        latex_solution,
        tikz_code,
        question_type,
        key_concepts,
        requires_calculus,
        subject,
    )
    
    # Combine problem and solution for difficulty assessment
    latex_content = latex_problem
    if latex_solution:
        latex_content += f"\n\n**Solution:**\n{latex_solution}"
    
    # Create PrimaryClassification with taxonomy results
    primary = PrimaryClassification(
        subject=subject,
        question_type=question_type or "subjective",
        chapter=taxonomy.chapter,
        topic=taxonomy.topic,
        subtopic=taxonomy.subtopic,
        has_diagram=bool(tikz_code),
        key_concepts=taxonomy.key_concepts,
        requires_calculus=requires_calculus,
        classified_from="latex",
    )
    
    # Stage 5: Difficulty (with taxonomy context)
    difficulty = assess_difficulty(
        latex_content,
        primary,
        None,  # diagram
        tikz_code,
        subject,
        show_spinner=False,
    )
    
    return EnrichedMetadata(taxonomy=taxonomy, difficulty=difficulty)


def enrich_metadata(
    latex_problem: str,
    latex_solution: Optional[str] = None,
    tikz_code: Optional[str] = None,
    question_type: Optional[str] = None,
    key_concepts: Optional[list[str]] = None,
    requires_calculus: bool = False,
    subject: Optional[str] = None,
    parallel: Optional[bool] = None,
) -> EnrichedMetadata:
    """Enrich metadata with taxonomy and difficulty.
    
    Args:
        latex_problem: LaTeX problem statement
        latex_solution: LaTeX solution (optional)
        tikz_code: TikZ diagram code (optional)
        question_type: Question type from Stage 1 (optional)
        key_concepts: Key concepts from Stage 1 (optional)
        requires_calculus: Whether problem requires calculus
        subject: Subject name (defaults to config)
        parallel: Run in parallel (defaults to config.run_metadata_parallel)
        
    Returns:
        EnrichedMetadata with both taxonomy and difficulty
    """
    if parallel is None:
        parallel = get_config().run_metadata_parallel
    
    if parallel:
        return enrich_metadata_sync(
            latex_problem,
            latex_solution,
            tikz_code,
            question_type,
            key_concepts,
            requires_calculus,
            subject,
        )
    else:
        return enrich_metadata_sequential(
            latex_problem,
            latex_solution,
            tikz_code,
            question_type,
            key_concepts,
            requires_calculus,
            subject,
        )


__all__ = [
    "enrich_metadata",
    "enrich_metadata_sync",
    "enrich_metadata_parallel",
    "enrich_metadata_sequential",
]
