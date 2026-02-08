"""CLI commands for DPP (Daily Practice Problem) creation.

Provides commands for creating DPP sets from question banks with
various selection strategies.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from vbagent.config import get_config
from vbagent.dpp.builder import DPPBuilder
from vbagent.metadata.store import MetadataStore


console = Console()


@click.group()
def dpp():
    """Create and manage Daily Practice Problem (DPP) sets.
    
    DPP sets are curated collections of questions selected from your
    question bank using smart strategies for balanced difficulty,
    topic coverage, or random selection.
    """
    pass


@dpp.command()
@click.option(
    "--count", "-n",
    type=int,
    required=True,
    help="Number of questions to include in DPP"
)
@click.option(
    "--strategy", "-s",
    type=click.Choice(["balanced", "topic_coverage", "random"]),
    default="balanced",
    help="Selection strategy (default: balanced)"
)
@click.option(
    "--topic", "-t",
    help="Filter by topic"
)
@click.option(
    "--difficulty", "-d",
    type=click.Choice(["easy", "medium", "hard"]),
    help="Filter by difficulty"
)
@click.option(
    "--chapter", "-c",
    help="Filter by chapter"
)
@click.option(
    "--question-type", "-q",
    help="Filter by question type"
)
@click.option(
    "--tags",
    help="Filter by tags (comma-separated)"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output path for main.tex (default: dpp_TIMESTAMP.tex)"
)
@click.option(
    "--title",
    default="Daily Practice Problem Set",
    help="Title for the DPP document"
)
@click.option(
    "--compile",
    is_flag=True,
    help="Compile DPP to PDF after creation"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show verbose compilation output"
)
def create(
    count: int,
    strategy: str,
    topic: str,
    difficulty: str,
    chapter: str,
    question_type: str,
    tags: str,
    output: str,
    title: str,
    compile: bool,
    verbose: bool
):
    """Create a new DPP set from the question bank.
    
    Examples:
    
        # Create a 10-question DPP with balanced difficulty
        vbagent dpp create -n 10
        
        # Create a DPP on mechanics with topic coverage
        vbagent dpp create -n 15 -s topic_coverage -t Mechanics
        
        # Create a DPP with only medium difficulty questions
        vbagent dpp create -n 8 -d medium --compile
    """
    try:
        # Get config and database path
        config = get_config()
        db_path = Path(config.workspace_root) / ".vbagent" / "metadata.db"
        
        if not db_path.exists():
            console.print(
                "[red]Error:[/red] Metadata database not found. "
                "Run 'vbagent metadata index <directory>' first."
            )
            raise click.Abort()
        
        # Build filters
        filters = {}
        if topic:
            filters["topic"] = topic
        if difficulty:
            filters["difficulty"] = difficulty
        if chapter:
            filters["chapter"] = chapter
        if question_type:
            filters["question_type"] = question_type
        if tags:
            filters["tags"] = [t.strip() for t in tags.split(",")]
        
        # Create DPP
        with console.status(f"[bold blue]Creating DPP with {strategy} strategy..."):
            with MetadataStore(db_path) as store:
                builder = DPPBuilder(store)
                
                output_path = Path(output) if output else None
                result = builder.create_dpp(
                    count=count,
                    strategy=strategy,
                    filters=filters if filters else None,
                    output_path=output_path,
                    title=title
                )
        
        # Display results
        console.print(f"\n[green]✓[/green] DPP created successfully!")
        console.print(f"  Output: [cyan]{result.main_tex_path}[/cyan]")
        console.print(f"  Strategy: [yellow]{result.strategy_used}[/yellow]")
        console.print(f"  Questions: [yellow]{len(result.questions)}[/yellow]")
        
        # Show question summary
        _display_question_summary(result.questions)
        
        # Compile if requested
        if compile:
            console.print(f"\n[bold blue]Compiling DPP to PDF...[/bold blue]")
            success, output_msg = result.compile(verbose=verbose)
            
            if success:
                console.print(f"[green]✓[/green] Compilation successful!")
                console.print(f"  PDF: [cyan]{output_msg}[/cyan]")
            else:
                console.print(f"[red]✗[/red] Compilation failed:")
                console.print(Panel(output_msg, border_style="red"))
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


def _display_question_summary(questions: list) -> None:
    """Display a summary table of selected questions."""
    # Count by difficulty
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0, "unknown": 0}
    for q in questions:
        diff = q.difficulty or "unknown"
        if diff in difficulty_counts:
            difficulty_counts[diff] += 1
        else:
            difficulty_counts["unknown"] += 1
    
    # Count by topic
    topic_counts = {}
    for q in questions:
        topic = q.topic or "Unknown"
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    # Create difficulty table
    diff_table = Table(title="Difficulty Distribution", show_header=True)
    diff_table.add_column("Difficulty", style="cyan")
    diff_table.add_column("Count", style="yellow", justify="right")
    diff_table.add_column("Percentage", style="green", justify="right")
    
    total = len(questions)
    for diff in ["easy", "medium", "hard", "unknown"]:
        count = difficulty_counts[diff]
        if count > 0:
            percentage = (count / total) * 100
            diff_table.add_row(diff.capitalize(), str(count), f"{percentage:.1f}%")
    
    console.print(diff_table)
    
    # Create topic table (top 5 topics)
    if topic_counts:
        topic_table = Table(title="Topic Coverage (Top 5)", show_header=True)
        topic_table.add_column("Topic", style="cyan")
        topic_table.add_column("Count", style="yellow", justify="right")
        
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        for topic, count in sorted_topics[:5]:
            topic_table.add_row(topic, str(count))
        
        console.print(topic_table)


@dpp.command()
@click.argument("dpp_file", type=click.Path(exists=True))
@click.option(
    "--output-dir", "-o",
    type=click.Path(),
    help="Output directory for PDF (default: same as DPP file)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show verbose compilation output"
)
def compile_dpp(dpp_file: str, output_dir: str, verbose: bool):
    """Compile a DPP .tex file to PDF.
    
    Examples:
    
        # Compile a DPP file
        vbagent dpp compile dpp_20240115_143022.tex
        
        # Compile with verbose output
        vbagent dpp compile dpp.tex -v
    """
    try:
        from vbagent.compile import compile_latex
        
        dpp_path = Path(dpp_file)
        
        # Read content
        content = dpp_path.read_text(encoding="utf-8")
        
        # Determine output directory
        out_dir = Path(output_dir) if output_dir else dpp_path.parent
        
        # Compile
        with console.status("[bold blue]Compiling DPP..."):
            result = compile_latex(
                content,
                subject="physics",
                output_dir=str(out_dir),
                verbose=verbose
            )
        
        if result.success:
            console.print(f"[green]✓[/green] Compilation successful!")
            console.print(f"  PDF: [cyan]{result.pdf_path}[/cyan]")
        else:
            console.print(f"[red]✗[/red] Compilation failed:")
            console.print(Panel(result.error_summary, border_style="red"))
            raise click.Abort()
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()


if __name__ == "__main__":
    dpp()
