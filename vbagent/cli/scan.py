"""CLI command for scanning physics question images to extract LaTeX.

Stage 2: Extract LaTeX from image using type-specific prompts.
"""

from pathlib import Path

import click


def _get_console():
    """Lazy import of rich Console."""
    from rich.console import Console
    return Console()


def _get_panel(*args, **kwargs):
    """Lazy import of rich Panel."""
    from rich.panel import Panel
    return Panel(*args, **kwargs)


def _get_syntax(*args, **kwargs):
    """Lazy import of rich Syntax."""
    from rich.syntax import Syntax
    return Syntax(*args, **kwargs)


VALID_QUESTION_TYPES = ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"]


def display_scan_result(result, console) -> None:
    """Display scan result with syntax highlighting."""
    # Show LaTeX with syntax highlighting
    syntax = _get_syntax(result.latex, "latex", theme="monokai", line_numbers=True)
    console.print(_get_panel(syntax, title="Extracted LaTeX", border_style="green"))
    
    # Show metadata
    if result.has_diagram:
        console.print(f"\n[yellow]Has Diagram:[/yellow] Yes")
        if result.raw_diagram_description:
            console.print(f"[yellow]Diagram Type:[/yellow] {result.raw_diagram_description}")


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--image",
    type=click.Path(exists=True),
    help="Path to the physics question image file"
)
@click.option(
    "-t", "--tex",
    type=click.Path(exists=True),
    help="Path to existing TeX file (for re-processing)"
)
@click.option(
    "--type", "question_type",
    type=click.Choice(VALID_QUESTION_TYPES),
    help="Override question type (skips classification)"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output TeX file path for saving results"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile LaTeX to validate; retry with agent on failure"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document + preamble before each compile and prompt to continue/skip/quit"
)
def scan(image: str | None, tex: str | None, question_type: str | None, output: str | None, do_compile: bool, verbose_compile: bool):
    """Stage 2: Extract LaTeX from physics question image.
    
    Runs classification first (unless --type provided), then extracts LaTeX
    using the appropriate type-specific prompt.
    
    \b
    Examples:
        vbagent scan -i question.png
        vbagent scan --image images/q1.png --output output.tex
        vbagent scan -i images/q1.png --type mcq_sc
        vbagent scan -i q.png -t existing.tex -o updated.tex
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.scanner import scan as scan_image, scan_with_type
    from vbagent.models.scan import ScanResult
    
    console = _get_console()
    
    # Validate input
    if not image and not tex:
        console.print("[red]Error:[/red] Either --image or --tex must be provided")
        raise SystemExit(1)
    
    if tex and not image:
        console.print("[red]Error:[/red] --tex requires --image for scanning")
        raise SystemExit(1)
    
    try:
        result: ScanResult
        
        if question_type:
            # Skip classification, use provided type
            console.print(f"[cyan]Using question type:[/cyan] {question_type}")
            with console.status("[bold green]Scanning image..."):
                result = scan_with_type(image, question_type)
        else:
            # Check for existing classification file
            from vbagent.models.classification import ClassificationResult
            image_path = Path(image)
            base_name = image_path.stem
            classification_file = Path("agentic/classifications") / f"{base_name}.json"
            
            classification = None
            if classification_file.exists():
                try:
                    import json
                    with open(classification_file) as f:
                        data = json.load(f)
                    classification = ClassificationResult(**data)
                    console.print(f"[dim]  ✓ Loaded existing classification from {classification_file}[/dim]")
                    console.print(f"[cyan]Type:[/cyan] {classification.question_type}")
                    console.print(f"[cyan]Confidence:[/cyan] {classification.confidence:.2%}")
                except Exception as e:
                    console.print(f"[yellow]  ⚠ Failed to load classification: {e}[/yellow]")
                    classification = None
            
            if classification is None:
                # Run classification
                with console.status("[bold green]Classifying image..."):
                    classification = classify_image(image)
                
                console.print(f"[cyan]Detected type:[/cyan] {classification.question_type}")
                console.print(f"[cyan]Confidence:[/cyan] {classification.confidence:.2%}")
            
            # Then scan with classified type
            if classification.has_diagram:
                # Run scanning and TikZ generation in parallel
                import threading
                from vbagent.agents.tikz import generate_tikz
                
                console.print("[bold green]Scanning & TikZ (parallel)...[/bold green]")
                
                # Prepare TikZ description
                tikz_description = f"Generate TikZ for {classification.diagram_type or 'diagram'}"
                
                # Results holders
                scan_result_holder = {"result": None, "error": None, "done": False}
                tikz_result_holder = {"result": None, "error": None, "done": False}
                
                def run_scan():
                    try:
                        scan_result_holder["result"] = scan_image(image, classification)
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
                        )
                    except Exception as e:
                        tikz_result_holder["error"] = e
                    finally:
                        tikz_result_holder["done"] = True
                
                # Start both threads
                scan_thread = threading.Thread(target=run_scan, daemon=True)
                tikz_thread = threading.Thread(target=run_tikz, daemon=True)
                
                console.print("[dim]  → Scanning LaTeX...[/dim]")
                console.print("[dim]  → Generating TikZ...[/dim]")
                
                scan_thread.start()
                tikz_thread.start()
                
                # Wait for both
                scan_thread.join()
                tikz_thread.join()
                
                # Check for errors
                if scan_result_holder["error"]:
                    raise scan_result_holder["error"]
                
                result = scan_result_holder["result"]
                console.print("[green]  ✓ Scanning complete[/green]")
                
                if tikz_result_holder["error"]:
                    console.print(f"[yellow]  ⚠ TikZ generation failed: {tikz_result_holder['error']}[/yellow]")
                    tikz_code = None
                else:
                    tikz_code = tikz_result_holder["result"]
                    console.print("[green]  ✓ TikZ complete[/green]")
                    
                    # Show TikZ code
                    tikz_syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
                    console.print(_get_panel(tikz_syntax, title="Generated TikZ", border_style="cyan"))
                    
                    # Combine if needed
                    if r'\input{diagram}' in result.latex:
                        from vbagent.cli.process import insert_tikz_into_latex
                        from vbagent.cli.common import format_latex
                        console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
                        result.latex = insert_tikz_into_latex(result.latex, tikz_code)
                        result.latex = format_latex(result.latex)
                        console.print("[green]  ✓ Combined[/green]")
            else:
                # No diagram - just run scanning
                with console.status("[bold green]Scanning image..."):
                    result = scan_image(image, classification)
        
        # Display result
        display_scan_result(result, console)
        
        # Compile validation if -c flag
        if do_compile:
            from vbagent.compile import compile_and_retry
            from vbagent.agents.compile_fixer import fix_latex
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
