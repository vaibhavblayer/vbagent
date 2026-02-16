"""CLI command for scanning physics question images to extract LaTeX.

Stage 2: Extract LaTeX from image using type-specific prompts.
"""

from pathlib import Path

import click

from ..common import _get_console, _get_panel, _get_syntax


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
@click.option(
    "--orchestrate", "use_orchestrator",
    is_flag=True,
    help="Use solution orchestrator to coordinate specialist agents for complex solutions"
)
def scan(
    image: str | None,
    tex: str | None,
    question_type: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    assess_difficulty: bool,
    analyze_diagram: bool,
    use_orchestrator: bool,
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
    from vbagent.agents.content_generation.scanner import scan as scan_image, scan_with_type
    from vbagent.models.content import ScanResult
    
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
                    from .ui import print_status
                    print_status(console, f"Loaded existing classification from {classification_file}", "info")
                except Exception as e:
                    from .ui import print_status
                    print_status(console, f"Failed to load classification: {e}", "warning")
                    classification = None
            
            if classification is None:
                # Run classification
                with console.status("[bold green]Classifying image..."):
                    classification = classify_image(image)
                
                from .ui import print_classification
                print_classification(console, classification.model_dump())
            
            # Use orchestrator if requested
            if use_orchestrator:
                console.print("\n[cyan]Using Solution Orchestrator...[/cyan]")
                from vbagent.agents.orchestration.solution_orchestrator import create_solution_orchestrator
                
                orchestrator = create_solution_orchestrator()
                
                problem_context = f"Question type: {classification.question_type}, Topic: {classification.topic}"
                if classification.subtopic:
                    problem_context += f", Subtopic: {classification.subtopic}"
                
                orchestrator_result = orchestrator.generate_solution(
                    image_path=image,
                    problem_context=problem_context,
                    question_type=classification.question_type,
                    verbose=True,
                )
                
                # Convert to ScanResult format
                result = ScanResult(
                    latex=orchestrator_result.latex,
                    question_type=classification.question_type,
                    metadata={
                        "orchestrated": True,
                        "plan_structure": orchestrator_result.plan.structure,
                        "agents_used": [o.agent for o in orchestrator_result.agent_outputs],
                        **orchestrator_result.metadata,
                    }
                )
                
                console.print(f"\n[green]✓ Solution generated using {len(orchestrator_result.agent_outputs)} specialist agents[/green]")
            
            # Then scan with classified type
            elif classification.has_diagram:
                # Run scanning and TikZ generation in parallel
                import threading
                from vbagent.agents.diagram.tikz import generate_tikz
                from rich.progress import Progress, SpinnerColumn, TextColumn
                
                console.print("\n[cyan]Stage 2+3: Scanning & TikZ (parallel)...[/cyan]")
                
                # Prepare TikZ description
                tikz_description = f"Generate TikZ for {classification.diagram_type or 'diagram'}"
                
                # Results holders
                scan_result_holder = {"result": None, "error": None, "done": False}
                tikz_result_holder = {"result": None, "error": None, "done": False}
                
                def run_scan():
                    try:
                        scan_result_holder["result"] = scan_image(image, classification, show_spinner=False)
                    except Exception as e:
                        scan_result_holder["error"] = e
                    finally:
                        scan_result_holder["done"] = True
                
                def run_tikz():
                    try:
                        # Use router if diagram analysis available
                        if analyze_diagram and diagram_analysis:
                            from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
                            tikz_code, agent_used = generate_tikz_with_routing(
                                image_path=image,
                                description=tikz_description,
                                diagram=diagram_analysis,
                                primary=primary,
                                use_context=True,
                                show_spinner=False
                            )
                            tikz_result_holder["result"] = tikz_code
                            tikz_result_holder["agent"] = agent_used
                        else:
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
                
                # Start both threads
                scan_thread = threading.Thread(target=run_scan, daemon=True)
                tikz_thread = threading.Thread(target=run_tikz, daemon=True)
                
                # Show combined spinner
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
                    
                    # Wait for both
                    while scan_thread.is_alive() or tikz_thread.is_alive():
                        scan_thread.join(timeout=0.1)
                        tikz_thread.join(timeout=0.1)
                
                # Check for errors
                if scan_result_holder["error"]:
                    raise scan_result_holder["error"]
                
                result = scan_result_holder["result"]
                from .ui import print_status
                print_status(console, "Scanning complete", "success")
                
                if tikz_result_holder["error"]:
                    print_status(console, f"TikZ generation failed: {tikz_result_holder['error']}", "warning")
                    tikz_code = None
                else:
                    tikz_code = tikz_result_holder["result"]
                    agent_used = tikz_result_holder.get("agent", "generic")
                    print_status(console, f"TikZ complete (agent: {agent_used})", "success")
                    
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
                from vbagent.models.classification import PrimaryClassification
                
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
                from vbagent.models.classification import PrimaryClassification
                
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
                
                from .ui import print_difficulty
                print_difficulty(console, difficulty_assessment.model_dump())
                
                # Save difficulty assessment
                if output:
                    import json
                    output_path = Path(output)
                    difficulty_file = output_path.parent / f"{output_path.stem}_difficulty.json"
                    difficulty_file.write_text(difficulty_assessment.model_dump_json(indent=2))
                    from .ui import print_status
                    print_status(console, f"Difficulty saved to: {difficulty_file}", "info")
                
            except Exception as e:
                from .ui import print_status
                print_status(console, f"Difficulty assessment failed: {e}", "warning")
        
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
