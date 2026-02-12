"""Example: Using the Multi-Agent Classification Pipeline

This example demonstrates how to use the new multi-agent classification
system with all 7 agents.
"""

from vbagent.agents.classification import (
    get_pipeline,
    classify_from_image,
    analyze_diagram,
    assess_difficulty,
    validate_tikz,
)


def example_1_basic_classification():
    """Example 1: Basic image classification (Agent 1)"""
    print("=" * 60)
    print("Example 1: Basic Image Classification")
    print("=" * 60)
    
    # Classify an image
    primary = classify_from_image("question.png", subject="physics")
    
    print(f"Question Type: {primary.question_type}")
    print(f"Topic: {primary.topic}")
    print(f"Subtopic: {primary.subtopic}")
    print(f"Has Diagram: {primary.has_diagram}")
    print(f"Key Concepts: {', '.join(primary.key_concepts)}")
    print(f"Estimated Time: {primary.time_estimate_minutes} min")
    print()


def example_2_diagram_analysis():
    """Example 2: Diagram analysis (Agent 2)"""
    print("=" * 60)
    print("Example 2: Diagram Analysis")
    print("=" * 60)
    
    # First classify
    primary = classify_from_image("question.png")
    
    # Then analyze diagram if present
    if primary.has_diagram:
        diagram = analyze_diagram("question.png", primary)
        
        print(f"Diagram Type: {diagram.diagram_type}")
        print(f"Category: {diagram.diagram_category}")
        print(f"Complexity: {diagram.diagram_complexity}")
        print(f"Suggested Agent: {diagram.suggested_tikz_agent}")
        print(f"TikZ Libraries: {', '.join(diagram.tikz_requirements.libraries)}")
        print(f"Complexity Score: {diagram.tikz_requirements.complexity_score}/10")
    print()


def example_3_difficulty_assessment():
    """Example 3: Difficulty assessment after scan (Agent 3)"""
    print("=" * 60)
    print("Example 3: Difficulty Assessment")
    print("=" * 60)
    
    # Assume we have LaTeX content from scanning
    latex_content = r"""
    \item A block of mass $m = 2$ kg is placed on a frictionless incline
    at angle $\theta = 30°$. Find the acceleration of the block.
    """
    
    primary = classify_from_image("question.png")
    
    # Assess difficulty
    difficulty = assess_difficulty(latex_content, primary)
    
    print(f"Difficulty: {difficulty.difficulty} ({difficulty.difficulty_score}/10)")
    print(f"Solve Time: {difficulty.expected_solve_time_minutes} min")
    print(f"Cognitive Level: {difficulty.cognitive_level}")
    print(f"Error Rate: {difficulty.expected_error_rate:.1%}")
    print(f"\nReasoning: {difficulty.difficulty_reasoning}")
    print(f"\nPrerequisites: {', '.join(difficulty.prerequisite_concepts)}")
    print(f"\nCommon Mistakes:")
    for mistake in difficulty.common_mistakes:
        print(f"  • {mistake}")
    print()


def example_4_tikz_validation():
    """Example 4: TikZ validation and fixing (Agent 7)"""
    print("=" * 60)
    print("Example 4: TikZ Validation")
    print("=" * 60)
    
    # Sample TikZ code with errors
    tikz_code = r"""
    \begin{tikzpicture}
        \draw (0,0) -- (2,0)  % Missing semicolon
        \draw[->] (0,0) -- (1,1);
        \node at (1,0.5) {Force}
    \end{tikzpicture}
    """
    
    # Validate and fix
    validation = validate_tikz(tikz_code, auto_fix=True, compile_test=False)
    
    print(f"Valid: {validation.is_valid}")
    print(f"Status: {validation.compilation_status}")
    print(f"Errors Found: {len(validation.errors_found)}")
    
    if validation.errors_found:
        print("\nErrors:")
        for error in validation.errors_found:
            print(f"  • Line {error.line}: {error.message}")
    
    if validation.fixes_applied:
        print("\nFixes Applied:")
        for fix in validation.fixes_applied:
            print(f"  • {fix.description}")
    
    if validation.fixed_tikz_code:
        print("\nFixed Code:")
        print(validation.fixed_tikz_code)
    print()


def example_5_complete_pipeline():
    """Example 5: Complete pipeline with all agents"""
    print("=" * 60)
    print("Example 5: Complete Pipeline")
    print("=" * 60)
    
    pipeline = get_pipeline()
    
    # Step 1: Classify from image
    print("Step 1: Classification...")
    primary = pipeline.classify_from_image("question.png")
    print(f"  ✓ Type: {primary.question_type}, Topic: {primary.topic}")
    
    # Step 2: Analyze diagram (if present)
    diagram = None
    if primary.has_diagram:
        print("Step 2: Diagram Analysis...")
        diagram = pipeline.analyze_diagram("question.png", None, primary)
        print(f"  ✓ Type: {diagram.diagram_type}, Agent: {diagram.suggested_tikz_agent}")
    
    # Step 3: Scan to LaTeX (simulated)
    print("Step 3: Scanning...")
    latex_content = "\\item Sample problem..."
    print(f"  ✓ LaTeX extracted")
    
    # Step 4: Assess difficulty
    print("Step 4: Difficulty Assessment...")
    difficulty = pipeline.assess_difficulty(None, latex_content, primary, diagram)
    print(f"  ✓ Difficulty: {difficulty.difficulty} ({difficulty.difficulty_score}/10)")
    
    # Step 5: Validate TikZ (if generated)
    if diagram:
        print("Step 5: TikZ Validation...")
        tikz_code = "\\begin{tikzpicture}...\\end{tikzpicture}"
        validation = pipeline.validate_tikz_code(tikz_code, auto_fix=True)
        print(f"  ✓ Valid: {validation.is_valid}")
    
    print("\n✅ Pipeline complete!")
    print()


def example_6_cli_usage():
    """Example 6: CLI usage examples"""
    print("=" * 60)
    print("Example 6: CLI Usage")
    print("=" * 60)
    
    print("Basic scan with difficulty assessment:")
    print("  $ vbagent scan -i question.png --assess-difficulty")
    print()
    
    print("Scan with diagram analysis:")
    print("  $ vbagent scan -i question.png --analyze-diagram")
    print()
    
    print("Full pipeline with all agents:")
    print("  $ vbagent process -i question.png \\")
    print("      --assess-difficulty \\")
    print("      --analyze-diagram \\")
    print("      --validate-tikz \\")
    print("      --ideas --alternate")
    print()
    
    print("Batch processing with new agents:")
    print("  $ vbagent process -i images/Problem_1.png -r 1 10 \\")
    print("      --assess-difficulty \\")
    print("      --parallel 3")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Multi-Agent Classification System Examples")
    print("=" * 60 + "\n")
    
    # Note: These examples assume you have actual image files
    # For demonstration, we show the structure
    
    print("Available Examples:")
    print("  1. Basic Classification (Agent 1)")
    print("  2. Diagram Analysis (Agent 2)")
    print("  3. Difficulty Assessment (Agent 3)")
    print("  4. TikZ Validation (Agent 7)")
    print("  5. Complete Pipeline (All Agents)")
    print("  6. CLI Usage Examples")
    print()
    
    # Uncomment to run specific examples:
    # example_1_basic_classification()
    # example_2_diagram_analysis()
    # example_3_difficulty_assessment()
    # example_4_tikz_validation()
    # example_5_complete_pipeline()
    example_6_cli_usage()
