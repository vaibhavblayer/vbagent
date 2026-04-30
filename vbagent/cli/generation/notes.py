"""CLI command for generating concept notes."""

import time
from pathlib import Path

import click
from rich.console import Console


@click.command()
@click.argument("topic")
@click.option("-o", "--output", "output_dir", type=click.Path(), default="agentic/notes",
              help="Output directory [default: agentic/notes]")
@click.option("-s", "--subject", type=click.Choice(["physics", "chemistry", "mathematics"]),
              default=None, help="Subject (default: from config)")
@click.option("--syllabus", type=click.Path(exists=True), default=None,
              help="Path to syllabus file for scope/depth guidance")
@click.option("--compile/--no-compile", "compile_pdf", default=True,
              help="Compile to PDF [default: yes]")
@click.option("--no-diagrams", is_flag=True, help="Skip diagram generation (placeholders only)")
@click.option("--plan-only", is_flag=True, help="Only generate the document plan")
@click.option("--max-workers", type=int, default=4, help="Max parallel workers [default: 4]")
@click.option("--no-cache", is_flag=True, help="Skip cache, force fresh generation")
def notes(
    topic: str,
    output_dir: str,
    subject: str | None,
    syllabus: str | None,
    compile_pdf: bool,
    no_diagrams: bool,
    plan_only: bool,
    max_workers: int,
    no_cache: bool,
):
    """Generate comprehensive concept notes on a topic.

    \b
    Examples:
        vbagent notes "Wave Optics: Single Slit, Double Slit, Slab"
        vbagent notes "Rotational Mechanics" --subject physics
        vbagent notes "Organic Reactions: SN1 and SN2" --subject chemistry
        vbagent notes "Wave Optics" --plan-only
        vbagent notes "Wave Optics" --no-diagrams
        vbagent notes "Wave Optics" --syllabus jee_syllabus.txt
        vbagent notes "Thermodynamics" --no-compile --max-workers 6
    """
    console = Console()

    # Resolve subject from config if not provided
    if subject is None:
        from vbagent.config import get_config
        subject = get_config().subject

    # Load syllabus if provided
    syllabus_text = ""
    if syllabus:
        syllabus_text = Path(syllabus).read_text(encoding="utf-8")
        console.print(
            f"[dim]Syllabus: {syllabus} ({len(syllabus_text)} chars)[/dim]")

    console.print(f"[bold cyan]Topic:[/bold cyan] {topic}")
    console.print(
        f"[dim]Subject: {subject} | Workers: {max_workers} | Diagrams: {not no_diagrams}[/dim]")

    t0 = time.time()

    try:
        from vbagent.utils.caffeinate import prevent_sleep
        from vbagent.agents.notes.generator import generate_notes

        with prevent_sleep("vbagent notes"):
            result = generate_notes(
                topic=topic,
                output_dir=output_dir,
                syllabus=syllabus_text,
                subject=subject,
                compile_pdf=compile_pdf,
                no_diagrams=no_diagrams,
                plan_only=plan_only,
                max_workers=max_workers,
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Failed:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)

    elapsed = time.time() - t0

    console.print(f"\n[bold green]Done[/bold green] in {elapsed:.1f}s")
    console.print(f"  Title: {result.title}")
    console.print(f"  Sections: {result.sections}")
    console.print(f"  Diagrams: {result.diagrams}")
    console.print(f"  TeX: {result.tex_path}")
    if result.pdf_path:
        console.print(f"  PDF: {result.pdf_path}")
    elif compile_pdf:
        console.print(
            "  [yellow]PDF compilation failed — check the .tex file[/yellow]")
