"""CLI command for classifying question images.

Stage 1: Classify question image and detect subject (physics/chemistry/mathematics).
"""

from pathlib import Path

import click

from ..common import _get_console
from vbagent.ui.tables import create_table


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
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output JSON file path (optional)"
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format: table (default) or json"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)
def classify(input_path: str, output: str | None, output_format: str, verbose: bool):
    """Stage 1: Classify question image and detect subject.
    
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
    from vbagent.agents.classifier import classify as classify_image
    
    console = _get_console()
    
    # Show deprecation warning if --image was used
    import sys
    if '--image' in sys.argv:
        console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
    
    try:
        # Run classification
        status_msg = "[bold green]Classifying image and detecting subject..."
        with console.status(status_msg):
            result = classify_image(input_path)
        
        if verbose:
            console.print(f"[dim]Processed: {input_path}[/dim]")
            console.print(f"[dim]Confidence: {result.confidence:.2%}[/dim]")
        
        # Output based on format
        if output_format == "json":
            click.echo(result.model_dump_json(indent=2))
        else:
            # Display rich formatted output
            console.print(format_result_table(result))
        
        # Save to file if output path specified
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.model_dump_json(indent=2))
            console.print(f"\n[green]✓[/green] Results saved to: {output}")
            
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Classification failed:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise SystemExit(1)
