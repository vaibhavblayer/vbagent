"""CLI command for scanning question images to extract LaTeX.

Stage 2: Extract LaTeX from image using subject-specific and type-specific prompts.
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
    "-i", "--input", "--image", "--tex",
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
    "--assess-difficulty", "assess_difficulty",
    is_flag=True,
    help="Assess difficulty after scanning"
)
@click.option(
    "--analyze-diagram", "analyze_diagram",
    is_flag=True,
    help="Analyze diagram in detail"
)
@click.option(
    "--orchestrate", "use_orchestrator",
    is_flag=True,
    help="Use solution orchestrator for complex solutions"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)
@click.option(
    "--generate-solution",
    is_flag=True,
    help="[EXPERIMENTAL] Use new solution generation pipeline with rich diagram context"
)
def scan(
    input_path: str | None,
    reference: str | None,
    question_type: str | None,
    subject: str | None,
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
    assess_difficulty: bool,
    analyze_diagram: bool,
    use_orchestrator: bool,
    verbose: bool,
    generate_solution: bool,
):
    """Stage 2: Extract LaTeX from question image with subject-specific formatting.
    
    Automatically detects subject (physics/chemistry/mathematics) and applies
    appropriate formatting conventions:
    - Chemistry: Uses \\ce{} notation for chemical formulas
    - Mathematics: Uses proof structure and set notation
    - Physics: Uses vector notation and SI units
    
    Runs classification first (unless --type and --subject provided), then
    extracts LaTeX using subject-specific and type-specific prompts.
    
    \b
    Examples:
        # Basic scanning
        vbagent scan -i question.png
        
        # With output file
        vbagent scan -i question.png -o output.tex
        
        # Override question type
        vbagent scan -i question.png --type mcq_sc
        
        # Chemistry question (auto-detected)
        vbagent scan -i chemistry/thermodynamics.png
        
        # Mathematics problem with verbose output
        vbagent scan -i math/calculus.png -v
        
        # Re-process existing TeX with reference
        vbagent scan -i existing.tex --reference context.tex
    
    \b
    Subject-Specific Features:
        Chemistry: \\ce{H2O}, \\ce{->}, chemfig structures
        Mathematics: Proof environments, \\forall, \\exists, set notation
        Physics: \\vec{F}, SI units, circuitikz, kinematikz
    
    \b
    See Also:
        vbagent classify --help    # For classification options
        vbagent process --help     # For full pipeline
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.content_generation.scanner import scan as scan_image, scan_with_type
    from vbagent.models.content import ScanResult
    
    console = _get_console()
    
    # Show deprecation warnings
    import sys
    if '--image' in sys.argv:
        console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
    if '--tex' in sys.argv:
        console.print("[yellow]Note:[/yellow] --tex is deprecated, use --input or -i", style="dim")
    
    # Validate input
    if not input_path:
        console.print("[red]Error:[/red] --input is required")
        raise SystemExit(1)
    
    # Determine if input is image or tex
    input_file = Path(input_path)
    is_tex_file = input_file.suffix.lower() in ['.tex', '.txt']
    
    if verbose:
        console.print(f"[dim]Input: {input_path}[/dim]")
        console.print(f"[dim]Type: {'TeX file' if is_tex_file else 'Image file'}[/dim]")
    
    try:
        result: ScanResult
        
        if question_type and subject:
            # Skip classification, use provided type and subject
            console.print(f"[cyan]Subject:[/cyan] {subject}")
            console.print(f"[cyan]Question type:[/cyan] {question_type}")
            with console.status("[bold green]Scanning..."):
                result = scan_with_type(input_path, question_type, subject=subject)
        elif question_type:
            # Use provided type, detect subject
            console.print(f"[cyan]Question type:[/cyan] {question_type}")
            with console.status("[bold green]Scanning..."):
                result = scan_with_type(input_path, question_type)
        else:
            # Use PipelineCache for classification
            from vbagent.cache import PipelineCache
            from vbagent.models.classification import PrimaryClassification
            from vbagent.agents.classification import classify_from_image
            
            problem_id = input_file.stem
            
            cache = PipelineCache()
            classification = None
            
            if cache.has(problem_id, "classification"):
                console.print("[dim]Loading cached classification...[/dim]")
                cached_data = cache.get(problem_id, "classification")
                # Only extract fields that exist in PrimaryClassification
                classification = PrimaryClassification(
                    subject=cached_data.get("subject", "physics"),
                    question_type=cached_data.get("question_type", "subjective"),
                    has_diagram=cached_data.get("has_diagram", False),
                )
            else:
                # Run classification
                with console.status("[bold green]Classifying image..."):
                    classification = classify_from_image(input_path, show_spinner=False)
                if cache:
                    cache.set(problem_id, "classification", classification.model_dump())
            
            from vbagent.cli.interfaces.ui import print_classification
            print_classification(console, {
                "subject": classification.subject,
                "question_type": classification.question_type,
                "has_diagram": classification.has_diagram,
            })
            
            # NEW: Use solution generation pipeline if flag is set
            if generate_solution:
                console.print("\n[cyan]Using NEW Solution Generation Pipeline...[/cyan]")
                console.print("[dim]  Stage 1: Scanning problem only[/dim]")
                console.print("[dim]  Stage 2: Generating solution with rich context[/dim]")
                console.print("[dim]  Stage 3: Generating diagrams (if needed)[/dim]")
                
                # Stage 1: Scan problem only (use existing scanner for now)
                with console.status("[bold green]Scanning problem..."):
                    scan_result = scan_image(input_path, classification, subject=classification.subject, show_spinner=False)
                
                from vbagent.cli.interfaces.ui import print_status
                print_status(console, "Problem scanned", "success")
                
                # Stage 2: Generate solution
                from vbagent.agents.content_generation.solution import generate_complete_solution
                
                with console.status("[bold green]Generating solution..."):
                    solution_latex = generate_complete_solution(
                        image_path=input_path,
                        classification=classification,
                        problem_text=scan_result.latex,
                        subject=classification.subject,
                        show_spinner=False,
                    )
                
                print_status(console, "Solution generated", "success")
                
                # Combine problem + solution
                final_latex = scan_result.latex + "\n\n" + solution_latex
                
                # Create result
                result = ScanResult(
                    latex=final_latex,
                    question_type=classification.question_type,
                    metadata={"solution_pipeline": "new"},
                    raw_diagram_description=None,
                )
                
                console.print(f"\n[green]✓ Complete LaTeX generated using new solution pipeline[/green]")
            
            # Use orchestrator if requested
            elif use_orchestrator:
                console.print("\n[cyan]Using Solution Orchestrator...[/cyan]")
                from vbagent.agents.orchestration.solution_orchestrator import create_solution_orchestrator
                
                orchestrator = create_solution_orchestrator()
                
                problem_context = f"Question type: {classification.question_type}, Subject: {classification.subject}"
                
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
                # Check for cached TikZ first
                from vbagent.cache import PipelineCache
                cache = PipelineCache()
                
                if cache.has(problem_id, "tikz") and cache.has(problem_id, "scan"):
                    console.print("[dim]Loading cached TikZ and scan...[/dim]")
                    tikz_code = cache.get(problem_id, "tikz")
                    scan_latex = cache.get(problem_id, "scan")
                    agent_used = "cached"
                    console.print(f"[green]✓ Loaded cached TikZ and scan[/green]")
                    
                    # Create result object from cached scan (scan is stored as plain text .tex file)
                    from vbagent.models.content import ScanResult
                    result = ScanResult(
                        latex=scan_latex if scan_latex else "",
                        question_type=classification.question_type,
                        metadata={},
                        raw_diagram_description=None
                    )
                    
                    # Combine cached TikZ if needed
                    if r'\input{diagram}' in result.latex:
                        from vbagent.cli.core.process import insert_tikz_into_latex
                        from vbagent.cli.common import format_latex
                        console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
                        result.latex = insert_tikz_into_latex(result.latex, tikz_code)
                        result.latex = format_latex(result.latex)
                        console.print("[green]  ✓ Combined[/green]")
                else:
                    # Run scanning and TikZ generation in parallel
                    import threading
                    from vbagent.agents.diagram.tikz import generate_tikz
                    from rich.progress import Progress, SpinnerColumn, TextColumn
                    
                    console.print("\n[cyan]Stage 2+3: Scanning & TikZ (parallel)...[/cyan]")
                    
                    # Prepare TikZ description
                    diagram_type = getattr(classification, 'diagram_type', None)
                    tikz_description = f"Generate TikZ for {diagram_type or 'diagram'}"
                    
                    # Results holders
                    scan_result_holder = {"result": None, "error": None, "done": False}
                    tikz_result_holder = {"result": None, "error": None, "done": False}
                    
                    def run_scan():
                        try:
                            scan_result_holder["result"] = scan_image(image, classification, subject=classification.subject, show_spinner=False)
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
                    from vbagent.cli.interfaces.ui import print_status
                    print_status(console, "Scanning complete", "success")
                    
                    if tikz_result_holder["error"]:
                        print_status(console, f"TikZ generation failed: {tikz_result_holder['error']}", "warning")
                        tikz_code = None
                    else:
                        tikz_code = tikz_result_holder["result"]
                        agent_used = tikz_result_holder.get("agent", "generic")
                        print_status(console, f"TikZ complete (agent: {agent_used})", "success")
                        
                        # Save TikZ to cache
                        if tikz_code and cache:
                            cache.set(problem_id, "tikz", tikz_code)
                        
                        # Save scan to cache
                        cache.set(problem_id, "scan", result.model_dump())
                        
                        # Show TikZ code
                        tikz_syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
                        console.print(_get_panel(tikz_syntax, title=f"Generated TikZ ({agent_used})", border_style="cyan"))
                        
                        # Combine if needed
                        if r'\input{diagram}' in result.latex:
                            from vbagent.cli.core.process import insert_tikz_into_latex
                            from vbagent.cli.common import format_latex
                            console.print("[dim]  → Combining LaTeX + TikZ...[/dim]")
                            result.latex = insert_tikz_into_latex(result.latex, tikz_code)
                            result.latex = format_latex(result.latex)
                            console.print("[green]  ✓ Combined[/green]")
            else:
                # No diagram - just run scanning
                with console.status("[bold green]Scanning image..."):
                    result = scan_image(image, classification, subject=classification.subject)
        
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
                    has_diagram=classification.has_diagram,
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
                        has_diagram=classification.has_diagram,
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
                
                from vbagent.cli.interfaces.ui import print_difficulty
                print_difficulty(console, difficulty_assessment.model_dump())
                
                # Save difficulty assessment
                if output:
                    import json
                    output_path = Path(output)
                    difficulty_file = output_path.parent / f"{output_path.stem}_difficulty.json"
                    difficulty_file.write_text(difficulty_assessment.model_dump_json(indent=2))
                    from vbagent.cli.interfaces.ui import print_status
                    print_status(console, f"Difficulty saved to: {difficulty_file}", "info")
                
            except Exception as e:
                from vbagent.cli.interfaces.ui import print_status
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
