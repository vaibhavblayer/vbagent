"""Individual pipeline stage functions.

Each function represents one stage of the processing pipeline,
extracted from the monolithic process_image() for composability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vbagent.models.classification import (
        PrimaryClassification,
        DiagramAnalysis,
        DifficultyAssessment,
        ClassificationResult,
    )
    from vbagent.models.content import IdeaResult
    from vbagent.cache import PipelineCache










def generate_solution_orchestrated(
    image_path: str,
    primary: "PrimaryClassification",
    problem_latex: str = "",
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> str:
    """Generate solution using subject-specific agent + diagram dispatch.

    Args:
        image_path: Path to question image.
        primary: Classification result.
        problem_latex: Scanned problem LaTeX (if already available).
        cache: Optional pipeline cache.
        problem_id: Problem ID for caching.
        console: Rich console.

    Returns:
        Combined problem + solution LaTeX with answer marking.
    """
    from vbagent.agents.orchestration.solution_orchestrator import create_solution_orchestrator

    solution_cached = cache and problem_id and cache.has(problem_id, "solution")

    if solution_cached:
        if console:
            console.print("[dim]Loading cached solution...[/dim]")
        return cache.get(problem_id, "solution")

    if console:
        console.print("[bold green]Generating solution...[/bold green]")

    orchestrator = create_solution_orchestrator(console=console)
    result = orchestrator.run(
        problem_latex=problem_latex,
        subject=primary.subject,
        question_type=primary.question_type,
        chapter=primary.chapter,
        topic=primary.topic,
        has_diagram=primary.has_diagram,
        image_path=image_path,
    )

    if console:
        meta = result.metadata
        diag_info = f", {meta.get('diagrams_rendered', 0)} diagram(s)" if meta.get('diagrams_rendered') else ""
        console.print(f"[green]✓[/green] Solution complete ({primary.subject}{diag_info})")

    if cache and problem_id:
        cache.set(problem_id, "solution", result.latex)

    return result.latex








def assess_difficulty_stage(
    latex: str,
    primary: "PrimaryClassification",
    diagram_analysis: Optional["DiagramAnalysis"],
    console=None,
) -> "DifficultyAssessment":
    """Stage 3b: Assess difficulty."""
    from vbagent.agents.classification import assess_difficulty as assess_difficulty_agent

    if console:
        with console.status("[bold green]Assessing difficulty..."):
            result = assess_difficulty_agent(latex, primary, diagram_analysis, show_spinner=False)
        console.print(f"[cyan]Difficulty:[/cyan] {result.difficulty} ({result.difficulty_score}/10)")
        console.print(f"[cyan]Cognitive Level:[/cyan] {result.cognitive_level}")
        console.print(f"[cyan]Estimated Time:[/cyan] {result.expected_solve_time_minutes} min")
    else:
        result = assess_difficulty_agent(latex, primary, diagram_analysis, show_spinner=False)
    return result


def extract_ideas_stage(
    problem: str,
    solution: str,
    full_content: Optional[str] = None,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> tuple[Optional["IdeaResult"], Optional[str]]:
    """Stage 4: Extract ideas from problem/solution.

    Returns (IdeaResult for JSON/concepts, idea_latex for inline append).
    Both paths use the same underlying agent — the LaTeX path is the
    single source of truth for the ``\\begin{idea}`` block.
    """
    from vbagent.agents.content_generation.idea import (
        extract_ideas,
        generate_idea_latex,
        has_idea_environment,
    )
    from vbagent.cli.common import _get_panel

    # --- JSON ideas (for concepts aggregation) ---
    ideas = None
    if cache and problem_id and cache.has(problem_id, "ideas"):
        if console:
            console.print("[dim]Loading cached ideas...[/dim]")
        from vbagent.models.content import IdeaResult
        cached_ideas = cache.get(problem_id, "ideas")
        if cached_ideas is None:
            if console:
                console.print("[dim yellow]Cache returned None, regenerating ideas...[/dim yellow]")
        else:
            ideas = IdeaResult(**cached_ideas)
    
    if ideas is None:
        if console:
            with console.status("[bold green]Stage 4: Extracting ideas..."):
                ideas = extract_ideas(problem, solution)
        else:
            ideas = extract_ideas(problem, solution)
        if cache and problem_id:
            cache.set(problem_id, "ideas", ideas.model_dump())

    # --- LaTeX idea block (single source of truth for inline append) ---
    idea_latex = None
    content_for_latex = full_content or (problem + "\n\n" + solution)
    if not has_idea_environment(content_for_latex):
        # Check cache first
        if cache and problem_id and cache.has(problem_id, "idea_latex"):
            if console:
                console.print("[dim]Loading cached idea block...[/dim]")
            idea_latex = cache.get(problem_id, "idea_latex")
        else:
            try:
                if console:
                    with console.status("[bold green]Generating idea block..."):
                        idea_latex = generate_idea_latex(content_for_latex)
                else:
                    idea_latex = generate_idea_latex(content_for_latex)
                if cache and problem_id and idea_latex:
                    cache.set(problem_id, "idea_latex", idea_latex)
            except Exception as e:
                if console:
                    console.print(f"[dim yellow]  ⚠ idea LaTeX generation skipped: {e}[/dim yellow]")

    if console and ideas:
        ideas_text = f"[bold]Concepts:[/bold] {', '.join(ideas.concepts)}\n"
        ideas_text += f"[bold]Formulas:[/bold] {', '.join(ideas.formulas)}\n"
        ideas_text += f"[bold]Techniques:[/bold] {', '.join(ideas.techniques)}\n"
        ideas_text += f"[bold]Difficulty Factors:[/bold] {', '.join(ideas.difficulty_factors)}"
        console.print(_get_panel(ideas_text, title="Extracted Ideas", border_style="yellow"))

    return ideas, idea_latex


def generate_alternate_stage(
    problem: str,
    solution: str,
    ideas: Optional["IdeaResult"],
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> list[str]:
    """Stage 5: Generate alternate solutions."""
    from vbagent.agents.content_generation.alternate import generate_alternate
    from vbagent.cli.common import _get_panel

    if cache and problem_id and cache.has(problem_id, "alternate"):
        if console:
            console.print("[dim]Loading cached alternate...[/dim]")
        return [cache.get(problem_id, "alternate")]

    if console:
        with console.status("[bold green]Stage 5: Generating alternate solution..."):
            alt = generate_alternate(problem, solution, ideas)
    else:
        alt = generate_alternate(problem, solution, ideas)

    if cache and problem_id:
        cache.set(problem_id, "alternate", alt)

    if console:
        console.print(_get_panel(alt, title="Alternate Solution", border_style="magenta"))

    return [alt]


def generate_variants_stage(
    latex: str,
    variant_types: list[str],
    ideas: Optional["IdeaResult"],
    classification: "ClassificationResult",
    use_context: bool = True,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> dict[str, str]:
    """Stage 6: Generate problem variants."""
    from vbagent.agents.variants.variant import generate_variant
    from vbagent.cli.common import _get_panel

    variants = {}
    for vtype in variant_types:
        cache_key = f"variant_{vtype}"
        if cache and problem_id and cache.has(problem_id, cache_key):
            if console:
                console.print(f"[dim]Loading cached {vtype} variant...[/dim]")
            variants[vtype] = cache.get(problem_id, cache_key)
        else:
            if console:
                with console.status(f"[bold green]Stage 6: Generating {vtype} variant..."):
                    variant_latex = generate_variant(
                        latex, vtype, ideas, use_context=use_context, classification=classification,
                    )
            else:
                variant_latex = generate_variant(
                    latex, vtype, ideas, use_context=use_context, classification=classification,
                )
            variants[vtype] = variant_latex
            if cache and problem_id:
                cache.set(problem_id, cache_key, variant_latex)

        if console:
            console.print(_get_panel(variants[vtype], title=f"{vtype.title()} Variant", border_style="green"))

    return variants


# ============================================================================
# Unified stages (new architecture — fewer API calls)
# ============================================================================


def classify_unified(
    image_path: str,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
):
    """Stage 1 (unified): Classify + analyze diagram in a single API call.

    Returns:
        UnifiedClassificationResult
    """
    from vbagent.agents.classification.unified_classifier import (
        UnifiedClassificationResult,
        classify_and_analyze,
    )

    if cache and problem_id and cache.has(problem_id, "classification"):
        if console:
            console.print("[dim]Loading cached classification...[/dim]")
        cached_data = cache.get(problem_id, "classification")
        if cached_data is None:
            # Cache returned None despite has() check - regenerate
            if console:
                console.print("[dim yellow]Cache returned None, regenerating...[/dim yellow]")
        else:
            return UnifiedClassificationResult(**cached_data)

    if console:
        with console.status("[bold green]Stage 1: Classifying & analyzing..."):
            result = classify_and_analyze(image_path, show_spinner=False)
    else:
        result = classify_and_analyze(image_path, show_spinner=False)

    if cache and problem_id:
        cache.set(problem_id, "classification", result.model_dump())

    return result


def run_problem_orchestrator(
    image_path: str,
    classification,
    use_context: bool = True,
    cache=None,
    problem_id: Optional[str] = None,
    console=None,
):
    """Stage 2 (unified): Run ProblemOrchestrator for scan + TikZ.

    Returns:
        ProblemResult
    """
    from vbagent.agents.orchestration.problem_orchestrator import ProblemOrchestrator

    orchestrator = ProblemOrchestrator(use_context=use_context, console=console)
    return orchestrator.run(
        image_path=image_path,
        classification=classification,
        cache=cache,
        problem_id=problem_id,
    )
