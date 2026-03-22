"""CLI command for scanning question images to extract LaTeX.

Stage 2: Extract LaTeX from image using subject-specific and type-specific prompts.
"""

from pathlib import Path

import click

from ..common import _get_console, _get_panel, _get_syntax


VALID_QUESTION_TYPES = ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"]


def display_scan_result(result, console) -> None:
    """Display scan result with syntax highlighting."""
    syntax = _get_syntax(result.latex, "latex", theme="monokai", line_numbers=True)
    console.print(_get_panel(syntax, title="Extracted LaTeX", border_style="green"))

    if result.has_diagram:
        console.print(f"\n[yellow]Has Diagram:[/yellow] Yes")
        if result.raw_diagram_description:
            console.print(f"[yellow]Diagram Type:[/yellow] {result.raw_diagram_description}")


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--input",
    "input_path",
    type=click.Path(exists=True),
    help="Input file path (image or tex file)"
)
@click.option(
    "--reference",
    type=click.Path(exists=True),
    help="Reference TeX file for re-processing or context"
)
@click.option(
    "--type", "question_type",
    type=click.Choice(VALID_QUESTION_TYPES),
    help="Override question type (skips classification)"
)
@click.option(
    "--subject",
    type=click.Choice(["physics", "chemistry", "mathematics"]),
    help="Override subject detection"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output TeX file path"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile LaTeX to validate"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document before each compile"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)
def scan(
    input_path: str | None,
    reference: str | None,
    question_type: str | None,
    subject: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    verbose: bool,
):
    """Stage 2: Extract LaTeX from question image.

    Automatically detects subject and applies appropriate formatting:
    - Chemistry: \\ce{} notation for chemical formulas
    - Mathematics: Proof structure and set notation
    - Physics: Vector notation and SI units

    Runs classification first (unless --type and --subject provided), then
    extracts LaTeX using subject-specific and type-specific prompts.

    \b
    Examples:
        vbagent scan -i question.png
        vbagent scan -i question.png -o output.tex
        vbagent scan -i question.png --type mcq_sc --subject physics
        vbagent scan -i question.png -v -c

    \b
    See Also:
        vbagent run --help         Full pipeline with solution generation
        vbagent classify --help    Classification only
    """
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.content_generation.scanner import scan as scan_image, scan_with_type
    from vbagent.models.content import ScanResult

    console = _get_console()

    if not input_path:
        console.print("[red]Error:[/red] --input is required")
        raise SystemExit(1)

    input_file = Path(input_path)
    is_tex_file = input_file.suffix.lower() in ['.tex', '.txt']

    if verbose:
        console.print(f"[dim]Input: {input_path}[/dim]")
        console.print(f"[dim]Type: {'TeX file' if is_tex_file else 'Image file'}[/dim]")

    try:
        result: ScanResult

        if question_type and subject:
            console.print(f"[cyan]Subject:[/cyan] {subject}")
            console.print(f"[cyan]Question type:[/cyan] {question_type}")
            with console.status("[bold green]Scanning..."):
                result = scan_with_type(input_path, question_type, subject=subject)
        elif question_type:
            console.print(f"[cyan]Question type:[/cyan] {question_type}")
            with console.status("[bold green]Scanning..."):
                result = scan_with_type(input_path, question_type)
        else:
            from vbagent.cache import PipelineCache
            from vbagent.models.classification import PrimaryClassification
            from vbagent.agents.classification import classify_from_image

            problem_id = input_file.stem
            cache = PipelineCache()
            classification = None

            if cache.has(problem_id, "classification"):
                console.print("[dim]Loading cached classification...[/dim]")
                cached_data = cache.get(problem_id, "classification")
                classification = PrimaryClassification(
                    subject=cached_data.get("subject", "physics"),
                    question_type=cached_data.get("question_type", "subjective"),
                    has_diagram=cached_data.get("has_diagram", False),
                )
            else:
                with console.status("[bold green]Classifying image..."):
                    classification = classify_from_image(input_path, show_spinner=False)
                cache.set(problem_id, "classification", classification.model_dump())

            from vbagent.cli.interfaces.ui import print_classification
            print_classification(console, {
                "subject": classification.subject,
                "question_type": classification.question_type,
                "has_diagram": classification.has_diagram,
            })

            # Scan with classified type
            if classification.has_diagram:
                from vbagent.cache import PipelineCache
                cache = PipelineCache()

                if cache.has(problem_id, "tikz") and cache.has(problem_id, "scan"):
                    console.print("[dim]Loading cached TikZ and scan...[/dim]")
                    tikz_code = cache.get(problem_id, "tikz")
                    scan_latex = cache.get(problem_id, "scan")
                    console.print(f"[green]✓ Loaded cached TikZ and scan[/green]")

                    result = ScanResult(
                        latex=scan_latex if scan_latex else "",
                        question_type=classification.question_type,
                        metadata={},
                        raw_diagram_description=None
                    )

                    if r'\input{diagram}' in result.latex:
                        from vbagent.pipeline.io import insert_tikz_into_latex
                        from vbagent.cli.common import format_latex
                        console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
                        result.latex = insert_tikz_into_latex(result.latex, tikz_code)
                        result.latex = format_latex(result.latex)
                        console.print("[green]  ✓ Combined[/green]")
                else:
                    import threading
                    from vbagent.agents.diagram.tikz import generate_tikz
                    from rich.progress import Progress, SpinnerColumn, TextColumn

                    console.print("\n[cyan]Stage 2+3: Scanning & TikZ (parallel)...[/cyan]")

                    diagram_type = getattr(classification, 'diagram_type', None)
                    tikz_description = f"Generate TikZ for {diagram_type or 'diagram'}"

                    scan_result_holder = {"result": None, "error": None, "done": False}
                    tikz_result_holder = {"result": None, "error": None, "done": False}

                    image = input_path

                    def run_scan():
                        try:
                            scan_result_holder["result"] = scan_image(image, classification, subject=classification.subject, show_spinner=False)
                        except Exception as e:
                            scan_result_holder["error"] = e
                        finally:
                            scan_result_holder["done"] = True

                    def run_tikz():
                        try:
                            tikz_result_holder["result"] = generate_tikz(
                                description=tikz_description,
                                image_path=image,
                                use_context=True,
                                classification=classification,
                                show_spinner=False
                            )
                            tikz_result_holder["agent"] = "generic"
                        except Exception as e:
                            tikz_result_holder["error"] = e
                        finally:
                            tikz_result_holder["done"] = True

                    scan_thread = threading.Thread(target=run_scan, daemon=True)
                    tikz_thread = threading.Thread(target=run_tikz, daemon=True)

                    progress = Progress(
                        SpinnerColumn(),
                        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
                        console=console,
                        transient=True
                    )

                    with progress:
                        task = progress.add_task("Processing Scanner + TikZ...", total=None)
                        scan_thread.start()
                        tikz_thread.start()
                        while scan_thread.is_alive() or tikz_thread.is_alive():
                            scan_thread.join(timeout=0.1)
                            tikz_thread.join(timeout=0.1)

                    if scan_result_holder["error"]:
                        raise scan_result_holder["error"]

                    result = scan_result_holder["result"]
                    from vbagent.cli.interfaces.ui import print_status
                    print_status(console, "Scanning complete", "success")

                    if tikz_result_holder["error"]:
                        print_status(console, f"TikZ generation failed: {tikz_result_holder['error']}", "warning")
                        tikz_code = None
                    else:
                        tikz_code = tikz_result_holder["result"]
                        agent_used = tikz_result_holder.get("agent", "generic")
                        print_status(console, f"TikZ complete (agent: {agent_used})", "success")

                        if tikz_code and cache:
                            cache.set(problem_id, "tikz", tikz_code)
                        cache.set(problem_id, "scan", result.model_dump())

                        tikz_syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
                        console.print(_get_panel(tikz_syntax, title=f"Generated TikZ ({agent_used})", border_style="cyan"))

                        if r'\input{diagram}' in result.latex:
                            from vbagent.pipeline.io import insert_tikz_into_latex
                            from vbagent.cli.common import format_latex
                            console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
                            result.latex = insert_tikz_into_latex(result.latex, tikz_code)
                            result.latex = format_latex(result.latex)
                            console.print("[green]  ✓ Combined[/green]")
            else:
                image = input_path
                with console.status("[bold green]Scanning image..."):
                    result = scan_image(image, classification, subject=classification.subject)

        # Display result
        display_scan_result(result, console)

        # Compile validation if -c flag
        if do_compile:
            from vbagent.compile import compile_and_retry
            from vbagent.agents.quality.latex_fixer import fix_latex
            from vbagent.config import get_config

            subject = get_config().subject
            console.print("[dim]  → Compiling LaTeX...[/dim]")
            result.latex, compile_result = compile_and_retry(
                result.latex,
                retry_fn=fix_latex,
                subject=subject,
                console=console,
                verbose=verbose_compile,
            )

        # Save to file if output path specified
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.latex)
            console.print(f"\n[green]LaTeX saved to:[/green] {output}")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Scan failed:[/red] {e}")
        raise SystemExit(1)
