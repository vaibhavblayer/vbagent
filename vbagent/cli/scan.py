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
@click.option(
    "--assess-difficulty", "assess_difficulty",
    is_flag=True,
    help="Assess difficulty after scanning (uses Agent 3)"
)
@click.option(
    "--analyze-diagram", "analyze_diagram",
    is_flag=True,
    help="Analyze diagram in detail (uses Agent 2)"
)
def scan(
    image: str | None,
    tex: str | None,
    question_type: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    assess_difficulty: bool,
    analyze_diagram: bool
):
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
                        # Use router if diagram analysis available
                        if analyze_diagram and diagram_analysis:
                            from vbagent.agents.tikz_router import generate_tikz_with_routing
                            tikz_code, agent_used = generate_tikz_with_routing(
                                image_path=image,
                                description=tikz_description,
                                diagram=diagram_analysis,
                                primary=primary if 'primary' in locals() else None,
                                use_context=True
                            )
                            tikz_result_holder["result"] = tikz_code
                            tikz_result_holder["agent"] = agent_used
                        else:
                            tikz_result_holder["result"] = generate_tikz(
                                description=tikz_description,
                                image_path=image,
                                use_context=True,
                                classification=classification,
                            )
                            tikz_result_holder["agent"] = "generic"
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
                    agent_used = tikz_result_holder.get("agent", "generic")
                    console.print(f"[green]  ✓ TikZ complete (agent: {agent_used})[/green]")
                    
                    # Show TikZ code
                    tikz_syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
                    console.print(_get_panel(tikz_syntax, title=f"Generated TikZ ({agent_used})", border_style="cyan"))
                    
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
        
        # NEW: Diagram analysis (Agent 2) if requested
        diagram_analysis = None
        if analyze_diagram and classification.has_diagram and image:
            console.print("\n[bold cyan]Running diagram analysis (Agent 2)...[/bold cyan]")
            try:
                from vbagent.agents.classification import analyze_diagram as analyze_diagram_agent
                from vbagent.models.classification_v2 import PrimaryClassification
                
                # Convert to PrimaryClassification
                primary = PrimaryClassification(
                    subject=getattr(classification, 'subject', 'physics'),
                    question_type=classification.question_type,
                    chapter=classification.chapter,
                    topic=classification.topic,
                    subtopic=classification.subtopic,
                    has_diagram=classification.has_diagram,
                    num_options=classification.num_options,
                    key_concepts=classification.key_concepts,
                    requires_calculus=classification.requires_calculus,
                    confidence=classification.confidence,
                    classified_from="image"
                )
                
                with console.status("[bold green]Analyzing diagram..."):
                    diagram_analysis = analyze_diagram_agent(image, primary)
                
                console.print(f"[green]  ✓ Diagram Type:[/green] {diagram_analysis.diagram_type}")
                console.print(f"[green]  ✓ Category:[/green] {diagram_analysis.diagram_category}")
                console.print(f"[green]  ✓ Complexity:[/green] {diagram_analysis.diagram_complexity}")
                console.print(f"[green]  ✓ Suggested Agent:[/green] {diagram_analysis.suggested_tikz_agent}")
                
                if diagram_analysis.tikz_requirements.libraries:
                    console.print(f"[dim]  Libraries: {', '.join(diagram_analysis.tikz_requirements.libraries)}[/dim]")
                
            except Exception as e:
                console.print(f"[yellow]  ⚠ Diagram analysis failed: {e}[/yellow]")
        
        # NEW: Difficulty assessment (Agent 3) if requested
        difficulty_assessment = None
        if assess_difficulty:
            console.print("\n[bold cyan]Running difficulty assessment (Agent 3)...[/bold cyan]")
            try:
                from vbagent.agents.classification import assess_difficulty as assess_difficulty_agent
                from vbagent.models.classification_v2 import PrimaryClassification
                
                # Convert to PrimaryClassification if not already done
                if not diagram_analysis:
                    primary = PrimaryClassification(
                        subject=getattr(classification, 'subject', 'physics'),
                        question_type=classification.question_type,
                        chapter=classification.chapter,
                        topic=classification.topic,
                        subtopic=classification.subtopic,
                        has_diagram=classification.has_diagram,
                        num_options=classification.num_options,
                        key_concepts=classification.key_concepts,
                        requires_calculus=classification.requires_calculus,
                        confidence=classification.confidence,
                        classified_from="image"
                    )
                
                with console.status("[bold green]Assessing difficulty..."):
                    difficulty_assessment = assess_difficulty_agent(
                        result.latex,
                        primary,
                        diagram_analysis,
                        tikz_code if 'tikz_code' in locals() else None
                    )
                
                console.print(f"[green]  ✓ Difficulty:[/green] {difficulty_assessment.difficulty} ({difficulty_assessment.difficulty_score:.1f}/10)")
                console.print(f"[green]  ✓ Solve Time:[/green] {difficulty_assessment.expected_solve_time_minutes} min")
                console.print(f"[green]  ✓ Cognitive Level:[/green] {difficulty_assessment.cognitive_level}")
                
                if difficulty_assessment.difficulty_reasoning:
                    console.print(f"\n[cyan]Reasoning:[/cyan]")
                    console.print(f"[dim]{difficulty_assessment.difficulty_reasoning}[/dim]")
                
                if difficulty_assessment.prerequisite_concepts:
                    console.print(f"\n[cyan]Prerequisites:[/cyan] {', '.join(difficulty_assessment.prerequisite_concepts[:3])}")
                
                if difficulty_assessment.common_mistakes:
                    console.print(f"[cyan]Common Mistakes:[/cyan]")
                    for mistake in difficulty_assessment.common_mistakes[:2]:
                        console.print(f"  • {mistake}")
                
                # Save difficulty assessment
                if output:
                    import json
                    output_path = Path(output)
                    difficulty_file = output_path.parent / f"{output_path.stem}_difficulty.json"
                    difficulty_file.write_text(difficulty_assessment.model_dump_json(indent=2))
                    console.print(f"\n[dim]Difficulty saved to: {difficulty_file}[/dim]")
                
            except Exception as e:
                console.print(f"[yellow]  ⚠ Difficulty assessment failed: {e}[/yellow]")
        
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
