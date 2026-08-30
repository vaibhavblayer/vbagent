"""CLI command for extracting problem-only LaTeX from question images."""

import re
from pathlib import Path

import click

from ..common import (
    _get_console,
    _get_panel,
    _get_syntax,
    configure_cli_verbosity,
    format_latex,
)
from vbagent.cli.item_selection import item_selection_options, resolve_item_range
from vbagent.pipeline.io import generate_image_paths_from_range


VALID_QUESTION_TYPES = [
    "mcq_sc",
    "mcq_mc",
    "subjective",
    "integer",
    "assertion_reason",
    "passage",
    "match",
]

_SOLUTION_ENVIRONMENT_RE = re.compile(
    r"\\begin\s*\{(?:solution|alternatesolution|finalanswer)\}",
    flags=re.IGNORECASE,
)
_DEFAULT_OUTPUT_ROOT = Path("agentic")
_DEFAULT_SCANS_DIR = _DEFAULT_OUTPUT_ROOT / "scans"


def display_scan_result(result, console) -> None:
    """Display scan result with syntax highlighting."""
    syntax = _get_syntax(result.latex, "latex", theme="monokai", line_numbers=True)
    console.print(_get_panel(syntax, title="Extracted LaTeX", border_style="green"))

    if result.has_diagram:
        console.print("\n[yellow]Has Diagram:[/yellow] Yes")
        if result.raw_diagram_description:
            console.print(f"[yellow]Diagram Type:[/yellow] {result.raw_diagram_description}")


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _require_problem_only(latex: str) -> str:
    """Reject solution content at the standalone scan boundary."""
    if _SOLUTION_ENVIRONMENT_RE.search(latex):
        raise ValueError(
            "Problem-only scan returned solution content; refusing to emit it"
        )
    return latex


def _classify_for_scan(
    input_path: str,
    question_type: str | None,
    subject: str | None,
    cache,
    problem_id: str,
    console,
):
    """Run canonical classification, respecting explicit routing overrides."""
    from vbagent.agents.classification.question_classifier import (
        QuestionRoutingClassification,
        classify_question_image,
        classify_question_route,
    )
    from vbagent.pipeline.stages import classify_question

    if question_type is None and subject is None:
        return classify_question(
            input_path,
            cache=cache,
            problem_id=problem_id,
            console=console,
        )

    if question_type is None or subject is None:
        with console.status("[bold green]Stage 1a: Routing subject & type..."):
            routing = classify_question_route(input_path, show_spinner=True)
    else:
        routing = QuestionRoutingClassification(
            subject=subject,
            question_type=question_type,
        )

    routing = routing.model_copy(
        update={
            "subject": subject or routing.subject,
            "question_type": question_type or routing.question_type,
        }
    )
    console.print(
        "[dim]Using scan override: "
        f"{routing.subject}/{routing.question_type}[/dim]"
    )
    with console.status(
        f"[bold green]Stage 1b: Analyzing {routing.subject} question..."
    ):
        return classify_question_image(
            input_path,
            routing=routing,
            show_spinner=True,
        )


def _scan_single(
    input_path: str | None,
    question_type: str | None,
    subject: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    verbose: bool,
):
    """Extract problem-only LaTeX from one question image."""

    from vbagent.cache import PipelineCache
    from vbagent.models.content import ScanResult
    from vbagent.pipeline.stages import run_problem_orchestrator

    console = _get_console()

    if not input_path:
        console.print("[red]Error:[/red] --input is required")
        raise SystemExit(1)

    input_file = Path(input_path)
    if input_file.suffix.lower() in {".tex", ".txt"}:
        console.print(
            "[red]Error:[/red] scan accepts question images; "
            "use 'vbagent run' for TeX input"
        )
        raise SystemExit(1)

    if verbose:
        console.print(f"[dim]Input: {input_path}[/dim]")
        console.print("[dim]Type: Image file[/dim]")

    try:
        problem_id = input_file.stem
        cache = PipelineCache()
        classification = _classify_for_scan(
            input_path,
            question_type,
            subject,
            cache,
            problem_id,
            console,
        )

        from vbagent.cli.interfaces.ui import print_classification

        print_classification(
            console,
            {
                "subject": classification.subject,
                "question_type": classification.question_type,
                "has_diagram": classification.has_diagram,
            },
        )

        problem_result = run_problem_orchestrator(
            input_path,
            classification,
            use_context=True,
            cache=cache,
            problem_id=problem_id,
            console=console,
        )
        result = ScanResult(
            latex=_require_problem_only(problem_result.latex or ""),
            has_diagram=classification.has_diagram,
            raw_diagram_description=classification.diagram_type,
        )

        # Display result
        display_scan_result(result, console)

        # Compile validation if -c flag
        if do_compile:
            from vbagent.compile import compile_and_retry
            from vbagent.agents.quality.latex_fixer import fix_latex

            console.print("[dim]  → Compiling LaTeX...[/dim]")
            result.latex, _ = compile_and_retry(
                result.latex,
                retry_fn=fix_latex,
                subject=classification.subject,
                console=console,
                verbose=verbose_compile,
            )

        # Save to file if output path specified
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.latex)
            console.print(f"\n[green]LaTeX saved to:[/green] {output}")

            # Match ``run`` when writing into an organized ``*/scans`` tree.
            # This lets later stage commands recover routing and diagram data
            # without asking the user to repeat subject/type flags.
            if output_path.parent.name == "scans":
                organized_root = output_path.parent.parent
                classifications_dir = organized_root / "classifications"
                classifications_dir.mkdir(parents=True, exist_ok=True)
                classification_path = classifications_dir / f"{problem_id}.json"
                classification_path.write_text(
                    classification.model_dump_json(indent=2),
                    encoding="utf-8",
                )
                console.print(
                    f"[green]Classification saved to:[/green] {classification_path}"
                )

                if problem_result.tikz_code:
                    tikz_dir = organized_root / "tikz"
                    tikz_dir.mkdir(parents=True, exist_ok=True)
                    tikz_path = tikz_dir / f"{problem_id}.tex"
                    tikz_path.write_text(
                        format_latex(problem_result.tikz_code),
                        encoding="utf-8",
                    )
                    console.print(f"[green]TikZ saved to:[/green] {tikz_path}")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Scan failed:[/red] {e}")
        raise SystemExit(1)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--input", "input_path", type=click.Path(exists=True),
    help="Question image path",
)
@item_selection_options
@click.option(
    "--type", "question_type", type=click.Choice(VALID_QUESTION_TYPES),
    help="Override the detected question type",
)
@click.option(
    "--subject",
    type=click.Choice(["physics", "chemistry", "mathematics", "biology"]),
    help="Override the detected subject",
)
@click.option(
    "-o", "--output", type=click.Path(),
    help=(
        "Output TeX file, or directory for a range "
        "(default: agentic/scans)"
    ),
)
@click.option("-c", "--compile", "do_compile", is_flag=True, help="Compile LaTeX to validate")
@click.option(
    "--verbose-compile", "verbose_compile", is_flag=True,
    help="Show full LaTeX document before each compile",
)
@click.option(
    "-v/-q", "--verbose/--quiet", "verbose", default=True,
    callback=configure_cli_verbosity,
    help="Show API profile, token, cache, and processing details [default: verbose]",
)
def scan(
    input_path: str | None,
    from_index: int | None,
    to_index: int | None,
    item: int | None,
    question_type: str | None,
    subject: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    verbose: bool,
):
    """Extract problem-only LaTeX from one image or a numbered image range.

    Automatically detects subject and applies appropriate formatting:
    - Chemistry: \\ce{} notation for chemical formulas
    - Mathematics: Proof structure and set notation
    - Physics: Vector notation and SI units

    Uses the canonical problem stage: classify, extract the question, and
    reconstruct any diagram. Solution generation is never run by this command.
    With no --output, results use the same agentic/scans workspace as run.

    \b
    Examples:
        vbagent scan -i question.png
        vbagent scan -i images/problem_1.png --from 1 --to 12
        vbagent scan -i images/problem_1.png --item 5
        vbagent scan -i question.png -o output.tex
        vbagent scan -i question.png --type mcq_sc --subject physics
        vbagent scan -i question.png -v -c

    \b
    See Also:
        vbagent run --help         Full pipeline with solution generation
        vbagent classify --help    Classification only
    """
    console = _get_console()
    if not input_path:
        raise click.UsageError("--input is required")

    item_range = resolve_item_range(from_index, to_index, item)
    input_paths = (
        generate_image_paths_from_range(input_path, item_range)
        if item_range is not None
        else [input_path]
    )
    if not input_paths:
        raise click.ClickException("No input files found in the selected range")

    explicit_range = from_index is not None or to_index is not None
    output_dir: Path | None = _DEFAULT_SCANS_DIR if output is None else None
    if output and explicit_range:
        output_dir = Path(output)
        if output_dir.suffix.lower() == ".tex":
            raise click.UsageError(
                "Range scanning requires --output to be a directory"
            )
        if output_dir.exists() and not output_dir.is_dir():
            raise click.UsageError(
                "Range scanning requires --output to be a directory"
            )

    failures = 0
    for position, selected_path in enumerate(input_paths, 1):
        if len(input_paths) > 1:
            console.print(
                f"\n[bold]Image {position}/{len(input_paths)}: "
                f"{Path(selected_path).name}[/bold]"
            )
        selected_output = output
        if output_dir is not None:
            selected_output = str(output_dir / f"{Path(selected_path).stem}.tex")
        try:
            _scan_single(
                selected_path,
                question_type,
                subject,
                selected_output,
                do_compile,
                verbose_compile,
                verbose,
            )
        except SystemExit:
            failures += 1
            if len(input_paths) == 1:
                raise

    if len(input_paths) > 1:
        console.print(
            f"\n[bold green]Scan complete: {len(input_paths) - failures}/"
            f"{len(input_paths)} image(s)[/bold green]"
        )
    if failures:
        raise SystemExit(1)
