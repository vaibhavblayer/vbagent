"""Example usage of the new multi-stage classification system.

This demonstrates how to use the taxonomy classifier, difficulty assessor,
and metadata enricher with the new architecture.
"""

from vbagent import (
    classify_taxonomy,
    assess_difficulty,
    enrich_metadata,
    get_config,
)

# Example LaTeX problem
latex_problem = r"""
A block of mass $m = 5$ kg is placed on a rough inclined plane making an angle 
$\theta = 30°$ with the horizontal. The coefficient of static friction between 
the block and the plane is $\mu_s = 0.4$. Will the block slide down the plane?
"""

latex_solution = r"""
For the block to remain stationary, the static friction must balance the component 
of weight along the plane.

Forces:
- Weight component along plane: $mg\sin\theta = 5 \times 10 \times \sin 30° = 25$ N
- Normal force: $N = mg\cos\theta = 5 \times 10 \times \cos 30° = 43.3$ N
- Maximum static friction: $f_{max} = \mu_s N = 0.4 \times 43.3 = 17.3$ N

Since $mg\sin\theta = 25$ N $> f_{max} = 17.3$ N, the block will slide down.
"""

def example_taxonomy_only():
    """Example: Classify taxonomy only (Stage 4)"""
    print("=" * 60)
    print("Example 1: Taxonomy Classification Only")
    print("=" * 60)
    
    taxonomy = classify_taxonomy(
        latex_problem=latex_problem,
        latex_solution=latex_solution,
        question_type="subjective",
        key_concepts=["friction", "inclined plane"],
        requires_calculus=False,
        subject="physics"
    )
    
    print(f"\nChapter: {taxonomy.chapter}")
    print(f"Topic: {taxonomy.topic}")
    print(f"Subtopic: {taxonomy.subtopic}")
    print(f"Key Concepts: {', '.join(taxonomy.key_concepts)}")
    print(f"Prerequisites: {', '.join(taxonomy.prerequisite_concepts)}")
    print(f"Cognitive Level: {taxonomy.cognitive_level}")
    print(f"Confidence: {taxonomy.confidence:.2f}")


def example_difficulty_only():
    """Example: Assess difficulty only (Stage 5)"""
    print("\n" + "=" * 60)
    print("Example 2: Difficulty Assessment Only")
    print("=" * 60)
    
    # Note: The existing difficulty assessor requires PrimaryClassification
    # This example shows the comprehensive output structure
    
    print("\nDifficulty Assessment uses the comprehensive v2.0 model:")
    print("  - difficulty: easy/medium/hard")
    print("  - difficulty_score: 0-10")
    print("  - difficulty_reasoning: detailed explanation")
    print("  - difficulty_factors: nested object")
    print("    - concept_complexity, calculation_complexity, multi_step, etc.")
    print("  - problem_structure: nested object")
    print("    - has_given_data, has_find_statement, has_constraints, is_multi_part")
    print("  - exam_relevance: nested object")
    print("    - jee_main, jee_advanced, neet (0.0-1.0 scores)")
    print("  - expected_solve_time_minutes, expected_error_rate")
    print("  - prerequisite_concepts, common_mistakes")
    print("  - solution_approach, required_formulas")
    print("  - learning_objectives, tags_auto")
    print("  - cognitive_level (Bloom's taxonomy)")
    
    print("\nThis is much more comprehensive than a simple difficulty assessment!")


def example_parallel_enrichment():
    """Example: Run both stages in parallel (default)"""
    print("\n" + "=" * 60)
    print("Example 3: Parallel Metadata Enrichment")
    print("=" * 60)
    
    print("\nRunning Stage 4 and Stage 5 in parallel...")
    print("Stage 4: Taxonomy Classification (gpt-5-nano)")
    print("Stage 5: Difficulty Assessment (gpt-5.1, comprehensive v2.0 model)")
    
    # Uncomment to run actual API call:
    # metadata = enrich_metadata(
    #     latex_problem=latex_problem,
    #     latex_solution=latex_solution,
    #     question_type="subjective",
    #     key_concepts=["friction", "inclined plane"],
    #     requires_calculus=False,
    #     subject="physics",
    #     parallel=True
    # )
    
    print("\nOutput structure:")
    print("  taxonomy:")
    print("    - chapter, topic, subtopic")
    print("    - key_concepts, prerequisite_concepts, related_topics")
    print("    - cognitive_level, exam_relevance")
    print("  difficulty:")
    print("    - difficulty, difficulty_score, difficulty_reasoning")
    print("    - difficulty_factors (nested)")
    print("    - problem_structure (nested)")
    print("    - exam_relevance (nested with JEE/NEET scores)")
    print("    - expected_solve_time_minutes, expected_error_rate")
    print("    - prerequisite_concepts, common_mistakes")
    print("    - solution_approach, required_formulas")
    print("    - learning_objectives, tags_auto")
    
    print("\nThe to_dict() method flattens this for database storage")


def example_config():
    """Example: Check configuration"""
    print("\n" + "=" * 60)
    print("Example 4: Configuration")
    print("=" * 60)
    
    config = get_config()
    
    print(f"\nTaxonomy enabled: {config.enable_taxonomy}")
    print(f"Difficulty enabled: {config.enable_difficulty}")
    print(f"Run in parallel: {config.run_metadata_parallel}")
    print(f"\nTaxonomy classifier model: {config.taxonomy_classifier.model}")
    print(f"Taxonomy reasoning: {config.taxonomy_classifier.reasoning_effort}")
    print(f"Taxonomy confidence threshold: {config.taxonomy_confidence_threshold}")
    print(f"\nDifficulty assessor model: {config.difficulty_assessor.model}")
    print(f"Difficulty reasoning: {config.difficulty_assessor.reasoning_effort}")


if __name__ == "__main__":
    # Note: These examples require OPENAI_API_KEY environment variable
    # Uncomment to run (will make actual API calls)
    
    # example_taxonomy_only()
    example_difficulty_only()
    # example_parallel_enrichment()
    example_config()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nNote: Uncomment function calls to run actual API examples")
    print("(requires OPENAI_API_KEY environment variable)")
    print("\nDifficultyAssessment uses the comprehensive v2.0 model")
    print("with nested structures for factors, structure, and exam relevance.")
