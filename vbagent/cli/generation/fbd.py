"""CLI command for generating Free Body Diagram TikZ code."""

from pathlib import Path

import click

from ..common import _get_console, _get_panel, _get_syntax


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--image",
    type=click.Path(exists=True),
    help="Path to scenario image"
)
@click.option(
    "-d", "--description",
    type=str,
    help="Text description of the FBD scenario"
)
@click.option(
    "-t", "--tex",
    type=click.Path(exists=True),
    help="Path to TeX file with problem text"
)
@click.option(
    "--ref", "ref_dirs",
    multiple=True,
    type=click.Path(exists=True),
    help="Reference directories with FBD examples (can be used multiple times)"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output TeX file path"
)
@click.option(
    "-c", "--compile", "do_compile",
    is_flag=True,
    help="Compile TikZ to validate; retry with agent on failure"
)
@click.option(
    "--verbose-compile", "verbose_compile",
    is_flag=True,
    help="Show full LaTeX document + preamble before compile"
)
def fbd(
    image: str | None,
    description: str | None,
    tex: str | None,
    ref_dirs: tuple[str, ...],
    output: str | None,
    do_compile: bool,
    verbose_compile: bool,
):
    """Generate Free Body Diagram TikZ code.
    
    Can generate from image, description, or problem text.
    
    Examples:
    
        vbagent fbd -d "Block on inclined plane at 30 degrees"
        
        vbagent fbd -i scenario.png -o fbd.tex
        
        vbagent fbd -t problem.tex -c
    """
    console = _get_console()
    
    if not image and not description and not tex:
        console.print("[red]Error: Must provide at least one of: --image, --description, or --tex[/red]")
        raise click.Abort()
    
    # Add reference directories if provided
    if ref_dirs:
        from vbagent.references.store import ReferenceStore
        store = ReferenceStore.get_instance()
        for ref_dir in ref_dirs:
            store.add_directory(ref_dir)
    
    # Read problem text if provided
    problem_text = None
    if tex:
        problem_text = Path(tex).read_text(encoding="utf-8")
    
    # Generate FBD
    console.print("[cyan]Generating Free Body Diagram...[/cyan]")
    
    from vbagent.agents.diagram.physics import generate_fbd
    
    try:
        tikz_code = generate_fbd(
            description=description or "",
            image_path=image,
            problem_text=problem_text,
        )
    except Exception as e:
        console.print(f"[red]Error generating FBD: {e}[/red]")
        raise click.Abort()
    
    # Display result
    syntax = _get_syntax(tikz_code, "latex", theme="monokai", line_numbers=True)
    panel = _get_panel(syntax, title="[bold green]Generated FBD", border_style="green")
    console.print(panel)
    
    # Save to file if requested
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tikz_code, encoding="utf-8")
        console.print(f"[green]✓[/green] Saved to {output}")
    
    # Compile if requested
    if do_compile or verbose_compile:
        from vbagent.compile import compile_and_retry
        
        console.print("\n[cyan]Compiling FBD...[/cyan]")
        
        result = compile_and_retry(
            tikz_code,
            subject="physics",
            verbose=verbose_compile,
        )
        
        if result.success:
            console.print("[green]✓ Compilation successful[/green]")
            if result.pdf_path:
                console.print(f"[dim]PDF: {result.pdf_path}[/dim]")
        else:
            console.print(f"[red]✗ Compilation failed after retries[/red]")
            if result.error:
                console.print(f"[dim]{result.error}[/dim]")
