"""CLI command for classifying question images.

Stage 1: Classify question image and detect subject (physics/chemistry/mathematics).
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ..common import _get_console, configure_cli_verbosity
from vbagent.cli.item_selection import item_selection_options, resolve_item_range
from vbagent.pipeline.io import generate_image_paths_from_range
from vbagent.ui.tables import create_table

if TYPE_CHECKING:
    from rich.table import Table


def format_result_table(result) -> "Table":
    """Format classification result as a rich table."""
    table = create_table(title="Classification Result", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Subject", result.subject)
    table.add_row("Question Type", result.question_type)
    table.add_row("Has Diagram", "Yes" if result.has_diagram else "No")
    table.add_row("Confidence", f"{result.confidence:.2%}")
    table.add_row("Classified From", result.classified_from)
    
    return table


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-i", "--input", "--image",  # Standardized: --input is primary, --image for compatibility
    "input_path",
    required=True,
    type=click.Path(exists=True),
    help="Input image file path"
)
@item_selection_options
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output JSON file, or directory for a range"
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format: table (default) or json"
)
@click.option(
    "-v/-q", "--verbose/--quiet", "verbose",
    default=True,
    callback=configure_cli_verbosity,
    help="Show API profile, token, cache, and processing details [default: verbose]"
)
def classify(
    input_path: str,
    from_index: int | None,
    to_index: int | None,
    item: int | None,
    output: str | None,
    output_format: str,
    verbose: bool,
):
    """Stage 1: Classify one image or a numbered image range.
    
    Analyzes a question image and extracts metadata including:
    - Subject (physics, chemistry, mathematics)
    - Question type (mcq_sc, mcq_mc, subjective, etc.)
    - Diagram presence and type
    - Difficulty level
    
    The subject is automatically detected from the image content.
    
    \b
    Examples:
        # Basic classification
        vbagent classify -i question.png
        # Numbered image range
        vbagent classify -i images/problem_1.png --from 1 --to 12
        # One numbered item
        vbagent classify -i images/problem_1.png --item 5
        # Output as JSON
        vbagent classify -i question.png --format json
        # Save to file
        vbagent classify -i question.png -o result.json
        # Chemistry question
        vbagent classify -i chemistry/thermodynamics.png
        # Mathematics problem
        vbagent classify -i math/calculus.png
    
    \b
    Supported Subjects:
        - Physics: mechanics, electromagnetism, optics, thermodynamics, etc.
        - Chemistry: organic, inorganic, physical chemistry, etc.
        - Mathematics: algebra, calculus, geometry, trigonometry, etc.
    """
    # Lazy imports - only load heavy dependencies when command runs
    from vbagent.agents.classification.question_classifier import classify_primary_image as classify_image
    
    console = _get_console()
    item_range = resolve_item_range(from_index, to_index, item)
    input_paths = (
        generate_image_paths_from_range(input_path, item_range)
        if item_range is not None
        else [input_path]
    )
    if not input_paths:
        raise click.ClickException("No input files found in the selected range")

    batch_output = item_range is not None and item_range[0] != item_range[1]
    output_dir: Path | None = None
    if output and batch_output:
        output_dir = Path(output)
        if output_dir.suffix.lower() == ".json":
            raise click.UsageError(
                "Range classification requires --output to be a directory"
            )
        if output_dir.exists() and not output_dir.is_dir():
            raise click.UsageError(
                "Range classification requires --output to be a directory"
            )
    
    # Show deprecation warning if --image was used
    import sys
    if '--image' in sys.argv:
        console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
    
    results = []
    failures = 0
    for position, selected_path in enumerate(input_paths, 1):
        if len(input_paths) > 1:
            console.print(
                f"\n[bold]Image {position}/{len(input_paths)}: "
                f"{Path(selected_path).name}[/bold]"
            )
        try:
            status_msg = "[bold green]Classifying image and detecting subject..."
            with console.status(status_msg):
                result = classify_image(selected_path)
            results.append((selected_path, result))

            if verbose:
                console.print(f"[dim]Processed: {selected_path}[/dim]")
                console.print(f"[dim]Confidence: {result.confidence:.2%}[/dim]")

            if output_format != "json":
                console.print(format_result_table(result))

            if output:
                output_path = (
                    output_dir / f"{Path(selected_path).stem}.json"
                    if output_dir is not None
                    else Path(output)
                )
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result.model_dump_json(indent=2))
                console.print(f"[green]OK[/green] Results saved to: {output_path}")
        except Exception as exc:
            failures += 1
            console.print(
                f"[red]Classification failed for {Path(selected_path).name}:[/red] "
                f"{exc}"
            )
            if verbose:
                import traceback
                console.print(traceback.format_exc())

    if output_format == "json":
        if batch_output:
            click.echo(json.dumps([result.model_dump() for _, result in results], indent=2))
        elif results:
            click.echo(results[0][1].model_dump_json(indent=2))

    if len(input_paths) > 1:
        console.print(
            f"\n[bold green]Classification complete: {len(results)}/"
            f"{len(input_paths)} image(s)[/bold green]"
        )
    if failures:
        raise SystemExit(1)
