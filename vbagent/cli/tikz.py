"""CLI command for generating TikZ diagram code.

Generates TikZ/PGF code for physics diagrams from images or descriptions.
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


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--image",
    type=click.Path(exists=True),
    help="Path to a diagram image file"
)
@click.option(
    "-d", "--description",
    type=str,
    help="Text description of the diagram to generate"
)
@click.option(
    "-t", "--tex",
    type=click.Path(exists=True),
    help="Path to TeX file with problem text (generates diagram from problem description)"
)
@click.option(
    "--ref", "ref_dirs",
    multiple=True,
    type=click.Path(exists=True),
    help="Reference directories containing TikZ/PGF documentation (can be used multiple times)"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output TeX file path for saving the generated TikZ code"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile TikZ to validate; retry with agent on failure"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document + preamble before each compile and prompt to continue/skip/quit"
)
def tikz(
    image: str | None,
    description: str | None,
    tex: str | None,
    ref_dirs: tuple[str, ...],
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
):
    """Generate TikZ code for physics diagrams.
    
    Can generate TikZ code from:
    - An image (-i/--image)
    - A text description (-d/--description)
    - A problem text file (-t/--tex)
    - Any combination of the above
    
    Optionally searches reference files (STY, TeX, PDF) for syntax examples.
    
    \b
    Examples:
        vbagent tikz -d "Free body diagram with gravity and normal force"
        vbagent tikz -i diagram.png -o diagram.tex
        vbagent tikz -t problem.tex -o diagram.tex
        vbagent tikz -t problem.tex -i reference.png -o diagram.tex
        vbagent tikz -d "RC circuit" --ref refs/circuitikz/ -o circuit.tex
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.tikz import generate_tikz, validate_tikz_output
    from vbagent.references.store import ReferenceStore
    
    console = _get_console()
    
    # Validate that at least one input is provided
    if not image and not description and not tex:
        console.print("[red]Error:[/red] At least one of --image, --description, or --tex must be provided")
        raise SystemExit(1)
    
    try:
        # Initialize reference store if directories provided
        if ref_dirs:
            store = ReferenceStore.get_instance(directories=list(ref_dirs))
            with console.status("[bold blue]Indexing reference files..."):
                indexed_count = store.index_files()
            console.print(f"[dim]Indexed {indexed_count} reference files[/dim]")
        
        # Read problem text if provided
        problem_text = None
        if tex:
            tex_path = Path(tex)
            problem_text = tex_path.read_text()
            console.print(f"[dim]Loaded problem from {tex}[/dim]")
        
        # Build description from inputs
        if description:
            desc = description
        elif not problem_text:
            desc = "Generate TikZ code for the diagram shown in the image."
        else:
            desc = ""  # Will use problem_text instead
        
        # Generate TikZ code
        with console.status("[bold green]Generating TikZ code..."):
            tikz_code = generate_tikz(
                description=desc,
                image_path=image,
                problem_text=problem_text,
            )
        
        # Validate output
        if not validate_tikz_output(tikz_code):
            console.print("[yellow]Warning:[/yellow] Generated code may not be valid TikZ")
        
        # Display the generated code
        syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
        console.print(_get_panel(syntax, title="Generated TikZ Code", border_style="green"))
        
        # Compile validation if -c flag
        if do_compile:
            from vbagent.compile import compile_and_retry
            from vbagent.agents.compile_fixer import fix_latex
            from vbagent.config import get_config
            
            subject = get_config().subject
            console.print("[dim]  → Compiling TikZ...[/dim]")
            tikz_code, compile_result = compile_and_retry(
                tikz_code,
                retry_fn=fix_latex,
                subject=subject,
                console=console,
                verbose=verbose_compile,
            )
        
        # Save to file if output path specified
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(tikz_code)
            console.print(f"\n[green]TikZ code saved to:[/green] {output}")
            
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]TikZ generation failed:[/red] {e}")
        raise SystemExit(1)
