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


_QUESTION_ROUTING_CONTRACT_VERSION = 1
_QUESTION_CLASSIFICATION_CONTRACT_VERSION = 6
_MATCH_SOLUTION_REPAIR_CONTRACT_VERSION = 1
_SUBJECTIVE_MULTIPART_SOLUTION_CONTRACT_VERSION = 1










def generate_solution_orchestrated(
    image_path: str,
    primary: "PrimaryClassification",
    problem_latex: str = "",
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
    return_result: bool = False,
    generate_diagrams: bool = True,
    classification_fingerprint: Optional[str] = None,
):
    """Generate solution using subject-specific agent + diagram dispatch.

    Args:
        image_path: Path to question image.
        primary: Classification result.
        problem_latex: Scanned problem LaTeX (if already available).
        cache: Optional pipeline cache.
        problem_id: Problem ID for caching.
        console: Rich console.
        return_result: Return the detailed SolutionResult instead of only
            the final LaTeX. Existing callers keep the string behavior.
        generate_diagrams: Whether to dispatch solution diagram agents.
        classification_fingerprint: Final-classification dependency key used
            to validate image-pipeline solution caches.

    Returns:
        Combined problem + solution LaTeX with answer marking.
    """
    from vbagent.agents.orchestration.solution_orchestrator import (
        SolutionResult,
        create_solution_orchestrator,
    )
    from vbagent.agents.content_generation.solution.structure import (
        has_multipart_subjective_problem,
    )

    multipart_subjective = (
        primary.question_type == "subjective"
        and has_multipart_subjective_problem(problem_latex)
    )

    solution_cached = bool(
        cache and problem_id and cache.has(problem_id, "solution")
    )
    if solution_cached and classification_fingerprint is not None:
        cached_fingerprint = cache.get_stage_data(
            problem_id,
            "solution",
        ).get("classification_fingerprint")
        if cached_fingerprint != classification_fingerprint:
            solution_cached = False
            if console:
                console.print(
                    "[dim]Refreshing solution for the current "
                    "classification...[/dim]"
                )

    if solution_cached:
        if console:
            console.print("[dim]Loading cached solution...[/dim]")
        cached_latex = cache.get(problem_id, "solution")
        cached_data = cache.get_stage_data(problem_id, "solution")
        cached_recommended = bool(
            cached_data.get("alternate_solution_recommended", False)
        )
        cached_hint = cached_data.get("alternate_solution_hint")
        cached_answer_type = cached_data.get("answer_type", "subjective")
        cached_answer_value = cached_data.get("answer_value")
        cached_final_answer = cached_data.get("final_answer_latex")
        if not cached_final_answer and cached_latex:
            from vbagent.tex import extract_answer_details
            extracted = extract_answer_details(cached_latex)
            if extracted and extracted.kind == "subjective":
                cached_final_answer = extracted.value

        stale_subjective_cache = (
            primary.question_type == "subjective"
            and cached_answer_type == "subjective"
            and not cached_final_answer
        )
        stale_match_cache = (
            primary.question_type == "match"
            and cached_data.get("match_solution_repair_contract_version")
            != _MATCH_SOLUTION_REPAIR_CONTRACT_VERSION
        )
        stale_multipart_subjective_cache = (
            multipart_subjective
            and cached_data.get(
                "subjective_multipart_solution_contract_version"
            )
            != _SUBJECTIVE_MULTIPART_SOLUTION_CONTRACT_VERSION
        )
        if stale_subjective_cache:
            if console:
                console.print(
                    "[dim yellow]Cached solution has no subjective final "
                    "answer; regenerating...[/dim yellow]"
                )
        elif stale_match_cache:
            if console:
                console.print(
                    "[dim yellow]Cached match solution predates option repair; "
                    "regenerating...[/dim yellow]"
                )
        elif stale_multipart_subjective_cache:
            if console:
                console.print(
                    "[dim yellow]Cached multipart subjective solution predates "
                    "structured part formatting; regenerating...[/dim yellow]"
                )
        elif not return_result:
            return cached_latex
        else:
            if not cached_recommended:
                cached_hint = None
            return SolutionResult(
                latex=cached_latex or "",
                answer_type=cached_answer_type,
                answer_value=cached_answer_value,
                final_answer_latex=cached_final_answer,
                alternate_solution_recommended=cached_recommended,
                alternate_solution_hint=cached_hint,
                metadata={
                    **cached_data,
                    "final_answer_latex": cached_final_answer,
                    "alternate_solution_decision_available": (
                        "alternate_solution_recommended" in cached_data
                    ),
                },
            )

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
        generate_diagrams=generate_diagrams,
    )

    if console:
        meta = result.metadata
        diag_info = f", {meta.get('diagrams_rendered', 0)} diagram(s)" if meta.get('diagrams_rendered') else ""
        console.print(f"[green]OK[/green] Solution complete ({primary.subject}{diag_info})")

    if cache and problem_id:
        cache.set(
            problem_id,
            "solution",
            result.latex,
            stage_data={
                "answer_type": result.answer_type,
                "answer_value": result.answer_value,
                "match_solution_repair_contract_version": (
                    _MATCH_SOLUTION_REPAIR_CONTRACT_VERSION
                    if primary.question_type == "match"
                    else None
                ),
                "subjective_multipart_solution_contract_version": (
                    _SUBJECTIVE_MULTIPART_SOLUTION_CONTRACT_VERSION
                    if multipart_subjective
                    else None
                ),
                "match_option_repaired": result.metadata.get(
                    "match_option_repaired", False
                ),
                "final_answer_latex": result.final_answer_latex,
                "alternate_solution_recommended": result.alternate_solution_recommended,
                "alternate_solution_hint": result.alternate_solution_hint,
                "classification_fingerprint": classification_fingerprint,
            },
        )

    return result if return_result else result.latex








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
            result = assess_difficulty_agent(latex, primary, diagram_analysis, show_spinner=True)
        console.print(f"[cyan]Difficulty:[/cyan] {result.difficulty} ({result.difficulty_score}/10)")
        console.print(f"[cyan]Cognitive Level:[/cyan] {result.cognitive_level}")
        console.print(f"[cyan]Estimated Time:[/cyan] {result.expected_solve_time_minutes} min")
    else:
        result = assess_difficulty_agent(latex, primary, diagram_analysis, show_spinner=True)
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
                    console.print(f"[dim yellow]  WARN idea LaTeX generation skipped: {e}[/dim yellow]")

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
    alternate_hint: Optional[str] = None,
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
            alt = generate_alternate(problem, solution, ideas, hint=alternate_hint)
    else:
        alt = generate_alternate(problem, solution, ideas, hint=alternate_hint)

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
# Canonical question-processing stages
# ============================================================================


def classify_question(
    image_path: str,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
):
    """Stage 1: Route generically, then run subject-specific analysis.

    Returns:
        QuestionClassification
    """
    from vbagent.agents.classification.question_classifier import (
        QuestionClassification,
        QuestionRoutingClassification,
        classify_question_route,
        classify_question_image,
    )

    if cache and problem_id and cache.has(problem_id, "classification"):
        stage_data = cache.get_stage_data(problem_id, "classification")
        cache_is_current = stage_data.get(
            "contract_version"
        ) == _QUESTION_CLASSIFICATION_CONTRACT_VERSION
        if cache_is_current:
            if console:
                console.print("[dim]Loading cached classification...[/dim]")
            cached_data = cache.get(problem_id, "classification")
            if cached_data is not None:
                return QuestionClassification(**cached_data)
            if console:
                console.print(
                    "[dim yellow]Cache returned None, regenerating...[/dim yellow]"
                )
        elif console:
            console.print(
                "[dim]Refreshing subject-specific classification for the "
                "current contract...[/dim]"
            )

    routing = None
    if cache and problem_id and cache.has(problem_id, "routing"):
        routing_data = cache.get_stage_data(problem_id, "routing")
        routing_is_current = routing_data.get(
            "contract_version"
        ) == _QUESTION_ROUTING_CONTRACT_VERSION
        if routing_is_current:
            cached_routing = cache.get(problem_id, "routing")
            if cached_routing is not None:
                routing = QuestionRoutingClassification(**cached_routing)
                if console:
                    console.print("[dim]Loading cached generic routing...[/dim]")
        elif console:
            console.print(
                "[dim]Refreshing generic subject/type routing for the current "
                "contract...[/dim]"
            )

    if routing is None:
        if console:
            with console.status(
                "[bold green]Stage 1a: Routing subject & type..."
            ):
                routing = classify_question_route(
                    image_path,
                    show_spinner=True,
                )
        else:
            routing = classify_question_route(
                image_path,
                show_spinner=True,
            )
        if cache and problem_id:
            cache.set(
                problem_id,
                "routing",
                routing.model_dump(),
                stage_data={
                    "contract_version": _QUESTION_ROUTING_CONTRACT_VERSION,
                },
            )

    if console:
        with console.status(
            f"[bold green]Stage 1b: Analyzing {routing.subject} question..."
        ):
            result = classify_question_image(
                image_path,
                routing=routing,
                show_spinner=True,
            )
    else:
        result = classify_question_image(
            image_path,
            routing=routing,
            show_spinner=True,
        )

    if cache and problem_id:
        cache.set(
            problem_id,
            "classification",
            result.model_dump(),
            stage_data={
                "contract_version": _QUESTION_CLASSIFICATION_CONTRACT_VERSION,
            },
        )

    return result


def classify_unified(*args, **kwargs):
    """Compatibility alias for :func:`classify_question`."""
    return classify_question(*args, **kwargs)


def run_problem_orchestrator(
    image_path: str,
    classification,
    use_context: bool = True,
    cache=None,
    problem_id: Optional[str] = None,
    console=None,
):
    """Stage 2: Run ProblemOrchestrator for scan + TikZ.

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
