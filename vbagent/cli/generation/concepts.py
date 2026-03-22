"""CLI command for generating concept revision sheets.

Aggregates ideas from batch-processed problems into a deduplicated,
organized concept sheet saved to agentic/concepts/concepts.tex.
"""

from pathlib import Path

import click

from ..common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _inventory(agentic_dir: Path) -> dict[str, int]:
    """Count what's available in the agentic directory."""
    scans_dir = agentic_dir / "scans"
    ideas_dir = agentic_dir / "ideas"
    images_dir = Path("images")

    images = len(list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))) if images_dir.exists() else 0
    scans = len(list(scans_dir.glob("*.tex"))) if scans_dir.exists() else 0
    ideas = len(list(ideas_dir.glob("*.json"))) if ideas_dir.exists() else 0

    return {"images": images, "scans": scans, "ideas": ideas}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-d", "--dir", "agentic_dir", type=click.Path(), default="agentic", help="Agentic output directory (default: agentic)")
@click.option("-s", "--subject", type=click.Choice(["physics", "chemistry", "mathematics"]), default=None, help="Subject (default: from config)")
@click.option("--full", is_flag=True, help="Send full .tex files (includes diagrams/TikZ)")
@click.option("--idea", "idea_only", is_flag=True, help="Extract only \\begin{idea} blocks from scans")
@click.option("--latex", "as_latex", is_flag=True, help="Use LLM to generate LaTeX directly (instead of JSON→LaTeX)")
@click.option("-c", "--compile", "do_compile", is_flag=True, help="Compile to PDF after generating")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def concepts(agentic_dir: str, subject: str | None, full: bool, idea_only: bool, as_latex: bool, do_compile: bool, yes: bool):
    """Generate a concept revision sheet from processed problems.

    Reads extracted ideas and organizes them into a concept sheet grouped
    by theme (5-7 groups) with a TikZ mindmap.

    \b
    Modes:
        (default)  Use ideas/*.json files
        --idea     Extract \\begin{idea} blocks from scans/*.tex
        --full     Send full .tex files (includes diagrams/TikZ)

    \b
    Output: agentic/concepts/concepts.tex

    \b
    Examples:
        vbagent concepts                    # From ideas/*.json
        vbagent concepts --idea             # From idea blocks in scans/
        vbagent concepts --full             # Full .tex files
        vbagent concepts --full -s chemistry
        vbagent concepts --idea --latex     # Direct LaTeX generation
        vbagent concepts --compile
    """
    from vbagent.agents.content_generation.concepts import (
        collect_ideas,
        collect_scans,
        collect_idea_blocks,
        generate_concepts_json,
        generate_concepts_latex,
        concept_sheet_to_latex,
    )

    console = _get_console()
    base = Path(agentic_dir)

    if not base.exists():
        console.print(f"[red]Error:[/red] Directory '{agentic_dir}' not found. Run 'vbagent batch init' first.")
        raise SystemExit(1)

    # Resolve subject
    if subject is None:
        from vbagent.config import get_config
        subject = get_config().subject

    # Inventory check
    stats = _inventory(base)
    console.print(f"[cyan]Inventory ({agentic_dir}/)[/cyan]")
    console.print(f"  Images:  {stats['images']}")
    console.print(f"  Scanned: {stats['scans']}")
    console.print(f"  Ideas:   {stats['ideas']}")

    # Determine mode
    mode = "ideas"  # default
    if full and idea_only:
        console.print("[yellow]Warning:[/yellow] --full and --idea are mutually exclusive. Using --full.")
        idea_only = False

    if full:
        mode = "full"
    elif idea_only:
        mode = "idea_blocks"
    elif stats["ideas"] == 0 and stats["scans"] > 0:
        # Auto-fallback: no ideas/*.json but scans exist — use idea blocks
        console.print("[dim]No ideas/*.json found — extracting idea blocks from scans/*.tex[/dim]")
        mode = "idea_blocks"

    # Validate
    if mode == "full" and stats["scans"] == 0:
        console.print("[red]Error:[/red] No scanned files in scans/. Run batch processing first.")
        raise SystemExit(1)
    elif mode == "idea_blocks" and stats["scans"] == 0:
        console.print("[red]Error:[/red] No scanned files in scans/. Run batch processing first.")
        raise SystemExit(1)
    elif mode == "ideas" and stats["ideas"] == 0:
        console.print("[red]Error:[/red] No idea files in ideas/ and no scans in scans/.")
        raise SystemExit(1)

    # Source info
    if mode == "full":
        source_count = stats["scans"]
        source_label = "full .tex files"
    elif mode == "idea_blocks":
        source_count = stats["scans"]
        source_label = "idea blocks from scans"
    else:
        source_count = stats["ideas"]
        source_label = "idea JSON files"

    console.print(f"\nWill generate concept sheet from {source_count} {source_label} ({subject})")

    if not yes:
        if not click.confirm("Proceed?", default=True):
            console.print("[dim]Cancelled.[/dim]")
            return

    # Collect data
    ideas = {}
    scans = None
    idea_blocks = None

    if mode == "full":
        scans = collect_scans(base / "scans")
    elif mode == "idea_blocks":
        idea_blocks = collect_idea_blocks(base / "scans")
        if not idea_blocks:
            console.print("[yellow]Warning:[/yellow] No \\begin{idea} blocks found in scans. Falling back to --full mode.")
            scans = collect_scans(base / "scans")
            idea_blocks = None
        else:
            console.print(f"[dim]Extracted idea blocks from {len(idea_blocks)} files[/dim]")
    else:
        ideas = collect_ideas(base / "ideas")

    # Generate
    output_dir = base / "concepts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "concepts.tex"

    with console.status("[bold green]Generating concept sheet..."):
        if as_latex:
            latex = generate_concepts_latex(
                ideas, subject=subject, full_scans=scans, idea_blocks=idea_blocks,
            )
        else:
            sheet = generate_concepts_json(
                ideas, subject=subject, full_scans=scans, idea_blocks=idea_blocks,
            )
            # Save JSON too
            json_file = output_dir / "concepts.json"
            json_file.write_text(sheet.model_dump_json(indent=2))
            console.print(f"[dim]Saved JSON: {json_file}[/dim]")
            latex = concept_sheet_to_latex(sheet, subject=subject)

    output_file.write_text(latex)
    console.print(f"[green]✓ Concept sheet saved to {output_file}[/green]")

    # Compile if requested
    if do_compile:
        from vbagent.compile import compile_latex
        console.print("\nCompiling to PDF...")
        success, pdf_path = compile_latex(str(output_file))
        if success:
            console.print(f"[green]✓ PDF: {pdf_path}[/green]")
        else:
            console.print("[red]Compilation failed.[/red]")
