"""Individual pipeline stage functions.

Each function represents one stage of the processing pipeline,
extracted from the monolithic process_image() for composability.
"""

from __future__ import annotations

import re
import threading
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


def classify(
    image_path: str,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> "PrimaryClassification":
    """Stage 1: Classify image using multi-agent system."""
    from vbagent.agents.classification import classify_from_image
    from vbagent.models.classification import PrimaryClassification

    if cache and problem_id and cache.has(problem_id, "classification"):
        if console:
            console.print("[dim]Loading cached classification...[/dim]")
        return PrimaryClassification(**cache.get(problem_id, "classification"))

    if console:
        primary = None
        with console.status("[bold green]Stage 1: Classifying image..."):
            primary = classify_from_image(image_path, show_spinner=False)
    else:
        primary = classify_from_image(image_path, show_spinner=False)

    if cache and problem_id:
        cache.set(problem_id, "classification", primary.model_dump())

    return primary


def analyze_diagram_stage(
    image_path: str,
    primary: "PrimaryClassification",
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> Optional["DiagramAnalysis"]:
    """Stage 1b: Analyze diagram in detail."""
    from vbagent.agents.classification import analyze_diagram as analyze_diagram_agent
    from vbagent.models.classification import DiagramAnalysis

    if cache and problem_id and cache.has(problem_id, "diagram"):
        if console:
            console.print("[dim]Loading cached diagram analysis...[/dim]")
        return DiagramAnalysis(**cache.get(problem_id, "diagram"))

    if console:
        with console.status("[bold green]Analyzing diagram..."):
            result = analyze_diagram_agent(image_path, primary, show_spinner=False)
    else:
        result = analyze_diagram_agent(image_path, primary, show_spinner=False)

    if cache and problem_id:
        cache.set(problem_id, "diagram", result.model_dump())

    return result


def scan_and_tikz_parallel(
    image_path: str,
    primary: "PrimaryClassification",
    diagram_analysis: Optional["DiagramAnalysis"],
    use_context: bool = True,
    cache: Optional["PipelineCache"] = None,
    problem_id: Optional[str] = None,
    console=None,
) -> tuple[str, Optional[str], Optional[str]]:
    """Stage 2+3: Run scanning and TikZ generation in parallel.

    Returns:
        (latex, tikz_code, agent_used)
    """
    from vbagent.agents.content_generation.scanner import scan as scan_image
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    from vbagent.agents.diagram.tikz import generate_tikz
    from vbagent.pipeline.io import convert_primary_to_classification
    from rich.progress import Progress, SpinnerColumn, TextColumn

    latex_cached = cache and problem_id and cache.has(problem_id, "scan")
    tikz_cached = cache and problem_id and cache.has(problem_id, "tikz")

    if latex_cached and tikz_cached:
        if console:
            console.print("[dim]Loading cached scan & TikZ...[/dim]")
        latex = cache.get(problem_id, "scan")
        tikz_code = cache.get(problem_id, "tikz")
        if console:
            console.print("[green]✓[/green] Loaded from cache")
        return latex, tikz_code, "cached"

    if console:
        console.print("[bold green]Stage 2+3: Scanning & TikZ (parallel)...[/bold green]")

    tikz_description = f"Generate TikZ for {diagram_analysis.diagram_type if diagram_analysis else 'diagram'}"

    scan_result_holder = {"result": None, "error": None}
    tikz_result_holder = {"result": None, "error": None, "agent": "generic"}

    def run_scan():
        if latex_cached:
            scan_result_holder["result"] = type("obj", (object,), {"latex": cache.get(problem_id, "scan")})()
            return
        try:
            classification = convert_primary_to_classification(primary)
            scan_result_holder["result"] = scan_image(
                image_path, classification, use_context=use_context, subject=primary.subject, show_spinner=False
            )
        except Exception as e:
            scan_result_holder["error"] = e

    def run_tikz():
        if tikz_cached:
            tikz_result_holder["result"] = cache.get(problem_id, "tikz")
            return
        try:
            if diagram_analysis:
                code, agent = generate_tikz_with_routing(
                    image_path=image_path,
                    description=tikz_description,
                    diagram=diagram_analysis,
                    primary=primary,
                    use_context=use_context,
                    show_spinner=False,
                )
                tikz_result_holder["result"] = code
                tikz_result_holder["agent"] = agent
            else:
                classification = convert_primary_to_classification(primary)
                tikz_result_holder["result"] = generate_tikz(
                    description=tikz_description,
                    image_path=image_path,
                    use_context=use_context,
                    classification=classification,
                    show_spinner=False,
                )
        except Exception as e:
            tikz_result_holder["error"] = e

    if console:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            console=console,
            transient=True,
        )
        with progress:
            progress.add_task("Processing Scanner + TikZ...", total=None)
            scan_thread = threading.Thread(target=run_scan, daemon=True)
            tikz_thread = threading.Thread(target=run_tikz, daemon=True)
            scan_thread.start()
            tikz_thread.start()
            while scan_thread.is_alive() or tikz_thread.is_alive():
                scan_thread.join(timeout=0.1)
                tikz_thread.join(timeout=0.1)
    else:
        scan_thread = threading.Thread(target=run_scan, daemon=True)
        tikz_thread = threading.Thread(target=run_tikz, daemon=True)
        scan_thread.start()
        tikz_thread.start()
        scan_thread.join()
        tikz_thread.join()

    if scan_result_holder["error"]:
        raise scan_result_holder["error"]

    latex = scan_result_holder["result"].latex
    if cache and problem_id and not latex_cached:
        cache.set(problem_id, "scan", latex)
    if console:
        console.print("[green]✓[/green] Scanning complete")

    tikz_code = None
    agent_used = "generic"
    if tikz_result_holder["error"]:
        if console:
            console.print(f"[yellow]![/yellow] TikZ generation failed: {tikz_result_holder['error']}")
    else:
        tikz_code = tikz_result_holder["result"]
        if cache and problem_id and not tikz_cached:
            cache.set(problem_id, "tikz", tikz_code)
        agent_used = tikz_result_holder.get("agent", "generic")
        if console:
            console.print(f"[green]✓[/green] TikZ complete (agent: {agent_used})")

    return latex, tikz_code, agent_used


def scan_only(
    image_path: str,
    primary: "PrimaryClassification",
    use_context: bool = True,
    console=None,
) -> str:
    """Stage 2: Scan image without TikZ (no diagram)."""
    from vbagent.agents.content_generation.scanner import scan as scan_image
    from vbagent.pipeline.io import convert_primary_to_classification

    if console:
        console.print("[bold green]Stage 2: Scanning image...[/bold green]")
    classification = convert_primary_to_classification(primary)
    scan_result = scan_image(image_path, classification, use_context=use_context, subject=primary.subject)
    if console:
        console.print("[green]✓[/green] Scanning complete")
    return scan_result.latex


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


def generate_problem_diagrams(
    image_path: str,
    primary: "PrimaryClassification",
    diagram_analysis: Optional["DiagramAnalysis"],
    use_context: bool = True,
    console=None,
) -> Optional[str]:
    """Generate problem diagrams (main + MCQ options) for orchestrator path."""
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    from vbagent.agents.diagram import generate_mcq_options

    problem_tikz = None

    has_main_diagram = (
        diagram_analysis
        and diagram_analysis.diagram_type
        and diagram_analysis.diagram_type.lower() != "none"
        and not (
            diagram_analysis.has_option_diagrams
            and diagram_analysis.num_option_diagrams > 0
            and not any(
                elem
                for elem in (diagram_analysis.diagram_elements or [])
                if "option" not in elem.lower() and "label" not in elem.lower()
            )
        )
    )

    if has_main_diagram:
        tikz_description = f"Generate diagrams for {diagram_analysis.diagram_type if diagram_analysis else 'problem'}"
        try:
            problem_tikz, agent_used = generate_tikz_with_routing(
                image_path=image_path,
                description=tikz_description,
                diagram=diagram_analysis,
                primary=primary,
                use_context=use_context,
                show_spinner=False,
            )
            if console:
                console.print(f"[green]  ✓ Main diagram generated (agent: {agent_used})[/green]")
        except Exception as e:
            if console:
                console.print(f"[yellow]  ⚠ Main diagram generation failed: {e}[/yellow]")

    if diagram_analysis and diagram_analysis.has_option_diagrams:
        if console:
            console.print("[dim]  → Generating MCQ option diagrams...[/dim]")
        try:
            option_tikz = generate_mcq_options(
                image_path=image_path,
                subject=primary.subject,
                option_diagram_type=diagram_analysis.option_diagram_type or "organic_structure",
                option_descriptions=diagram_analysis.option_diagram_descriptions,
                diagram_analysis=diagram_analysis.model_dump() if hasattr(diagram_analysis, "model_dump") else diagram_analysis,
                use_context=use_context,
                show_spinner=False,
            )
            if problem_tikz:
                problem_tikz = problem_tikz + "\n\n" + option_tikz
            else:
                problem_tikz = option_tikz
            if console:
                console.print("[green]  ✓ Option diagrams generated (coordinator)[/green]")
        except Exception as e:
            if console:
                console.print(f"[yellow]  ⚠ Option diagram generation failed: {e}[/yellow]")

    return problem_tikz


def generate_option_diagrams(
    image_path: str,
    latex: str,
    primary: "PrimaryClassification",
    diagram_analysis: Optional["DiagramAnalysis"],
    use_context: bool = True,
    console=None,
) -> Optional[str]:
    """Generate MCQ option diagrams when \\OptionA/\\OptionB placeholders are detected."""
    from vbagent.agents.diagram import generate_mcq_options

    option_descriptions = None
    options_match = re.search(r'% OPTIONS_DIAGRAMS:\s*(.+?)(?:\n|$)', latex)
    if options_match:
        desc_text = options_match.group(1)
        option_parts = re.findall(r'\([a-d]\)\s*([^,]+(?:,(?!\s*\([a-d]\))[^,]+)*)', desc_text)
        if option_parts:
            option_descriptions = [part.strip() for part in option_parts]

    tikz_code = generate_mcq_options(
        image_path=image_path,
        subject=primary.subject,
        option_diagram_type=diagram_analysis.option_diagram_type if diagram_analysis else "organic_structure",
        option_descriptions=option_descriptions,
        diagram_analysis=diagram_analysis.model_dump() if diagram_analysis else None,
        use_context=use_context,
        show_spinner=False,
    )
    if console:
        console.print("[green]  ✓ Option diagrams complete (coordinator)[/green]")
    return tikz_code


def generate_option_diagrams_simple(
    image_path: str,
    latex: str,
    classification: "ClassificationResult",
    use_context: bool = True,
    console=None,
) -> Optional[str]:
    """Generate option diagrams using generic TikZ (no diagram analysis available)."""
    from vbagent.agents.diagram.tikz import generate_tikz

    options_match = re.search(r'% OPTIONS_DIAGRAMS:\s*(.+?)(?:\n|$)', latex)
    if options_match:
        tikz_description = f"Generate option diagrams: {options_match.group(1)}"
    else:
        tikz_description = "Generate TikZ diagrams for MCQ options (\\OptionA, \\OptionB, \\OptionC, \\OptionD)"

    if console:
        console.print("[bold green]Stage 3: Generating option diagrams...[/bold green]")
        console.print("[dim]  → Generating TikZ for options...[/dim]")

    tikz_code = generate_tikz(
        description=tikz_description,
        image_path=image_path,
        use_context=use_context,
        classification=classification,
    )
    if console:
        console.print("[green]  ✓ Option diagrams complete[/green]")
    return tikz_code


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
        ideas = IdeaResult(**cache.get(problem_id, "ideas"))
    else:
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
        try:
            if console:
                with console.status("[bold green]Generating idea block..."):
                    idea_latex = generate_idea_latex(content_for_latex)
            else:
                idea_latex = generate_idea_latex(content_for_latex)
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
        return UnifiedClassificationResult(**cache.get(problem_id, "classification"))

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
