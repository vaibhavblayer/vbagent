"""CLI commands for paper orchestrator."""

from functools import wraps
import click
from pathlib import Path

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _paper_authoring_errors(function):
    """Render expected canonical-authoring failures without a traceback."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except click.ClickException:
            raise
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapped


@click.group(context_settings=CONTEXT_SETTINGS)
def paper():
    """Paper generation — create, manage, and QA exam papers.

    \b
    Quick Start:
        vbagent paper generate --exam jee_main --subject physics --chapter electrostatics --topic electric_field --type mcq_sc
        vbagent paper init --from-problems ./agentic/scans/ --subject physics
        vbagent paper generate --exam jee_main --subject physics --chapter kinematics --count 10
        vbagent paper solve
        vbagent paper hint
        vbagent paper status
    """
    pass


@paper.command()
@click.option("--from-problems", "source_dir", type=click.Path(exists=True), help="Directory with existing .tex files")
@click.option("-s", "--subject", default="physics", help="Subject (physics/chemistry/mathematics)")
@click.option("--target", multiple=True, help="Topic targets as topic:count (e.g. mechanics:10)")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing manifest")
@click.option("--tone", default="", help="Paper tone/thinking style (preset name or free-form, see 'paper tones')")
@click.option("--paper-dir", default="agentic", help="Base directory (default: agentic)")
def init(source_dir, subject, target, force, tone, paper_dir):
    """Initialize a paper with syllabus from existing problems."""
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    target_counts = {}
    for t in target:
        parts = t.split(":")
        if len(parts) == 2:
            target_counts[parts[0]] = int(parts[1])

    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    state = orch.init_paper(
        source_dir=Path(source_dir) if source_dir else None,
        subject=subject, target_counts=target_counts or None, force=force,
    )
    if tone:
        state.tone = tone
        orch.manifest.save(state)
    console.print(f"[green]OK[/green] Paper initialized: {len(state.problems)} problems, subject={state.subject}"
                  + (f", tone={state.tone}" if state.tone else ""))


@paper.command()
@click.option("--exam", required=True, help="Versioned exam syllabus ID, e.g. jee_main or neet")
@click.option(
    "--subject",
    required=True,
    type=click.Choice(["physics", "chemistry", "mathematics", "biology"]),
)
@click.option("--chapter", required=True, help="Exact or uniquely resolvable syllabus chapter")
@click.option("-t", "--topic", help="Topic for standalone generation")
@click.option(
    "--type",
    "question_type",
    default="mcq_sc",
    type=click.Choice(
        ["mcq_sc", "mcq_mc", "subjective", "integer", "assertion_reason", "passage", "match"]
    ),
    show_default=True,
)
@click.option(
    "-d",
    "--difficulty",
    default="medium",
    type=click.Choice(["easy", "medium", "hard"], case_sensitive=False),
    show_default=True,
)
@click.option("--idea", help="Idea description for the problem")
@click.option(
    "-c",
    "--count",
    default=1,
    type=click.IntRange(1, 100_000),
    show_default=True,
    help="Number of problems to generate",
)
@click.option("--concept", "concepts", multiple=True, help="Required concept; repeat as needed")
@click.option("--syllabus", "syllabus_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--syllabus-version", "expected_syllabus_version")
@click.option("--passage-questions", type=click.IntRange(2, 10), default=3, show_default=True)
@click.option("--diagram-ratio", type=click.FloatRange(0.0, 1.0), default=0.0, show_default=True)
@click.option("--no-solution", is_flag=True, help="Deprecated; accepted authoring always requires an independent solution")
@click.option("--tone", default="", help="Tone override (preset name or free-form, see 'paper tones')")
@click.option("--seed", type=int, default=0, show_default=True)
@click.option("--max-attempts", type=click.IntRange(1, 20), default=3, show_default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=2, show_default=True)
@click.option("--human-review/--automatic-acceptance", default=False, show_default=True)
@click.option("--paper-dir", default="agentic", help="Base directory")
@_paper_authoring_errors
def generate(
    exam, subject, chapter, topic, question_type, difficulty, idea, count,
    concepts, syllabus_path, expected_syllabus_version, passage_questions,
    diagram_ratio, no_solution, tone, seed, max_attempts, concurrency,
    human_review, paper_dir,
):
    """Create paper problems through durable syllabus-scoped authoring.

    \b
    Examples:
        vbagent paper generate --exam jee_main --subject physics --chapter electrostatics --topic electric_field --type mcq_sc
        vbagent paper generate --exam jee_main --subject physics --chapter kinematics --topic projectile_motion --idea "projectile on incline"
        vbagent paper generate --exam neet --subject physics --chapter optics --count 20 --concurrency 4
    """
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    if no_solution:
        raise click.UsageError(
            "--no-solution cannot be used for creation; an independent solution is a required acceptance gate"
        )
    difficulty_score = {"easy": 3, "medium": 5, "hard": 8}.get(difficulty.lower())

    from vbagent.authoring.models import AuthoringRequest

    request = AuthoringRequest(
        exam=exam,
        subject=subject,
        chapter=chapter,
        topics=[topic] if topic else [],
        syllabus_path=syllabus_path,
        expected_syllabus_version=expected_syllabus_version,
        count=count,
        question_types={question_type: 1.0},
        difficulties={difficulty_score: 1.0},
        diagram_ratio=diagram_ratio,
        passage_question_count=passage_questions,
        required_concepts=list(concepts),
        seed_ideas=[idea] if idea else [],
        tone=tone,
        seed=seed,
        acceptance={"human_review_required": human_review},
    )
    report = orch.author_problems(
        request,
        max_attempts=max_attempts,
        concurrency=concurrency,
    )
    console.print(
        f"\n[bold]Imported {report.total_generated}/{report.total_requested} accepted problem(s)[/bold]"
    )
    console.print(
        f"Run accepted={report.accepted}, needs_review={report.needs_review}, "
        f"rejected={report.rejected}, failed={report.failed}"
    )
    console.print(f"Authoring run: {report.authoring_run_id}\nArtifacts: {report.authoring_run_dir}")
    if report.total_generated != report.total_requested:
        raise click.ClickException(
            "paper authoring did not import every requested accepted problem; "
            "inspect or resume the durable authoring run"
        )


@paper.command()
@click.option("--problems", help="Comma-separated serial numbers")
@click.option("--regenerate", is_flag=True, help="Regenerate even if solution exists")
@click.option("--paper-dir", default="agentic", help="Base directory")
def solve(problems, regenerate, paper_dir):
    """Generate solutions for existing problems."""
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    report = orch.generate_solutions(problem_ids=ids, regenerate=regenerate)
    console.print(f"[bold]Solved {report.solved}/{report.total}[/bold]")


@paper.command()
@click.option("--problems", help="Comma-separated serial numbers")
@click.option("--style", default="conceptual", type=click.Choice(["conceptual", "equation", "direction"]))
@click.option("--paper-dir", default="agentic", help="Base directory")
def hint(problems, style, paper_dir):
    """Generate hints for problems."""
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    report = orch.generate_hints(problem_ids=ids, hint_style=style)
    console.print(f"[bold]Hints generated: {report.generated}/{report.total}[/bold]")


@paper.command()
@click.option("--paper-dir", default="agentic", help="Base directory")
def status(paper_dir):
    """Show paper status and coverage."""
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    state = orch.get_status()

    console.print(f"\n[bold]Paper: {state.paper_id}[/bold]")
    console.print(f"Subject: {state.subject}")
    if state.tone:
        console.print(f"Tone: {state.tone}")
    console.print(f"Problems: {len(state.problems)}")

    solved = sum(1 for p in state.problems if p.solution_status == "generated")
    hinted = sum(1 for p in state.problems if p.hint_status == "generated")
    qa_passed = sum(1 for p in state.problems if p.qa_status == "passed")
    enriched = sum(1 for p in state.problems if p.subtopic)
    diagrammed = sum(1 for p in state.problems if p.diagram_status != "none")
    console.print(f"Solutions: {solved}/{len(state.problems)}")
    console.print(f"Hints: {hinted}/{len(state.problems)}")
    console.print(f"QA passed: {qa_passed}/{len(state.problems)}")
    console.print(f"Classified: {enriched}/{len(state.problems)}")
    console.print(f"Diagrams: {diagrammed}/{len(state.problems)}")

    # Show subtopic breakdown if any are classified
    if enriched:
        subtopics: dict[str, int] = {}
        for p in state.problems:
            if p.subtopic:
                subtopics[p.subtopic] = subtopics.get(p.subtopic, 0) + 1
        console.print("\n[bold]Subtopic distribution:[/bold]")
        for st, cnt in sorted(subtopics.items(), key=lambda x: -x[1]):
            console.print(f"  {st}: {cnt}")


@paper.command()
@click.option("--problems", help="Comma-separated serial numbers")
@click.option("--paper-dir", default="agentic", help="Base directory")
def qa(problems, paper_dir):
    """Run QA checks on problems."""
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    results = orch.run_qa(problem_ids=ids)
    passed = sum(1 for r in results if r["passed"])
    console.print(f"[bold]QA: {passed}/{len(results)} passed[/bold]")


@paper.command()
@click.option("-s", "--subject", default=None, help="Filter by subject (physics/chemistry/mathematics)")
def tones(subject):
    """List available tone presets per subject."""
    from vbagent.paper.models import TONE_PRESETS
    from vbagent.cli.common import _get_console

    console = _get_console()
    subjects = [subject] if subject else list(TONE_PRESETS.keys())

    for subj in subjects:
        presets = TONE_PRESETS.get(subj, {})
        if not presets:
            continue
        console.print(f"\n[bold]{subj.title()}[/bold]")
        for name, desc in presets.items():
            console.print(f"  [cyan]{name}[/cyan] — {desc}")
    console.print("\nUse with: paper init --tone <name> or paper generate --tone <name>")
    console.print("Free-form text also accepted: --tone 'focus on symmetry and energy methods'")


@paper.command()
@click.option("--problems", help="Comma-separated serial numbers (default: all with empty subtopic)")
@click.option("--paper-dir", default="agentic", help="Base directory")
def enrich(problems, paper_dir):
    """Classify existing problems to fill in subtopic, concepts, and difficulty.

    \b
    Runs a lightweight LLM call on each problem's LaTeX to extract metadata.
    By default, only enriches problems with empty subtopic fields.

    Examples:
        vbagent paper enrich
        vbagent paper enrich --problems 1,2,3
    """
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    results = orch.enrich_problems(problem_ids=ids)
    enriched = sum(1 for r in results if r.get("success"))
    console.print(f"[bold]Enriched {enriched}/{len(results)} problems[/bold]")


@paper.command(name="compile")
@click.option("-o", "--output", default="main.tex", help="Output filename (default: main.tex)")
@click.option("-t", "--title", default=None, help="Document title (default: auto from manifest)")
@click.option("--all-packages", is_flag=True, help="Include packages for all subjects")
@click.option("--pdf", is_flag=True, help="Run pdflatex after generating main.tex")
@click.option("--inline", is_flag=True, help="Embed all problem content directly in main.tex (no \\input)")
@click.option("--only", type=click.Choice(["problems", "solutions", "hints"]), default=None, help="Only include specific content")
@click.option("--problems", help="Comma-separated serial numbers (default: all)")
@click.option("--paper-dir", default="agentic", help="Base directory")
def compile_cmd(output, title, all_packages, pdf, inline, only, problems, paper_dir):
    """Assemble main.tex from manifest and optionally compile to PDF.

    \b
    Each problem file in scans/ contains the full content: problem statement,
    options, diagrams, solution, alternate solution, and hints — all in one file.

    Use --only to render just one component:
        --only hints       Just the hints
        --only solutions   Just the solutions
        --only problems    Just the problem statements (no solutions/hints)

    Use --inline to embed all content directly into main.tex (single file output).

    Examples:
        vbagent paper compile --paper-dir .
        vbagent paper compile --pdf --paper-dir .
        vbagent paper compile --only hints --pdf --paper-dir .
        vbagent paper compile --inline --pdf
        vbagent paper compile --problems 1,2,3 --pdf
    """
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    try:
        result = orch.compile_paper(
            output=output, title=title, all_packages=all_packages,
            run_pdflatex=pdf, problems=ids, inline=inline, only=only,
        )
        if not result["success"]:
            raise SystemExit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@paper.command()
@click.option("--problems", help="Comma-separated serial numbers (default: all without diagrams)")
@click.option("--description", help="Diagram description (overrides auto-assessment)")
@click.option("--no-diagram", is_flag=True, help="Skip auto-diagram during generation")
@click.option("--paper-dir", default="agentic", help="Base directory")
def diagram(problems, description, no_diagram, paper_dir):
    """Add diagrams to existing problems.

    \b
    Uses the existing TikZ agent router to pick the right specialized agent
    (FBD, circuit, graph, optics, organic structure, etc.) based on subject
    and diagram description.

    By default, assesses each problem to decide if a diagram is needed.
    Use --description to provide a specific diagram description for all targets.

    Examples:
        vbagent paper diagram
        vbagent paper diagram --problems 1,2
        vbagent paper diagram --problems 3 --description "FBD of block on incline with friction"
    """
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    results = orch.generate_diagrams(problem_ids=ids, description=description)
    added = sum(1 for r in results if r.get("success"))
    console.print(f"[bold]Diagrams: {added}/{len(results)} added[/bold]")


@paper.command()
@click.option("-o", "--output", default="paper_export.zip", help="Output zip filename")
@click.option("-t", "--title", default=None, help="Document title")
@click.option("--all-packages", is_flag=True, help="Include packages for all subjects")
@click.option("--problems", help="Comma-separated serial numbers (default: all)")
@click.option("--paper-dir", default="agentic", help="Base directory")
def export(output, title, all_packages, problems, paper_dir):
    """Export Overleaf-ready zip with main.tex + problem files.

    \b
    Assembles solutions and hints into each problem file, generates main.tex,
    and packages everything into a zip that can be uploaded to Overleaf or
    compiled locally.

    Examples:
        vbagent paper export --paper-dir /tmp/jee_kinematics
        vbagent paper export --title "JEE Kinematics" --pdf
        vbagent paper export --problems 1,2,3
    """
    from vbagent.paper.orchestrator import PaperOrchestrator
    from vbagent.cli.common import _get_console

    console = _get_console()
    orch = PaperOrchestrator(base_dir=Path(paper_dir), console=console)
    ids = [int(x.strip()) for x in problems.split(",")] if problems else None
    try:
        zip_path = orch.export_zip(
            output=output, title=title, all_packages=all_packages, problems=ids,
        )
        console.print(f"[bold]Export complete: {zip_path}[/bold]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
