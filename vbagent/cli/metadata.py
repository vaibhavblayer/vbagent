"""CLI commands for question bank metadata management."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from vbagent.metadata import MetadataStore


@click.group()
def metadata():
    """Manage question bank metadata."""
    pass


@metadata.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--db",
    type=click.Path(),
    default=".vbagent/metadata.db",
    help="Path to metadata database",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Scan subdirectories recursively",
)
def index(directory: str, db: str, recursive: bool):
    """Index LaTeX files in a directory.
    
    Scans all .tex files and extracts metadata including chapter, topic,
    difficulty, question type, and tags. Metadata can be specified in
    comments at the top of each file:
    
    \b
    % chapter: Mechanics
    % topic: Kinematics
    % difficulty: medium
    % type: mcq_sc
    % tags: motion, acceleration, graphs
    
    Example:
        vbagent metadata index ./questions
        vbagent metadata index ./questions --db custom.db --no-recursive
    """
    console = Console()
    
    dir_path = Path(directory)
    db_path = Path(db)
    
    console.print(f"\n[bold cyan]Indexing question bank:[/bold cyan] {dir_path}")
    console.print(f"[dim]Database: {db_path}[/dim]\n")
    
    with console.status("[bold green]Scanning files..."):
        with MetadataStore(db_path) as store:
            count = store.index_directory(dir_path, recursive=recursive)
    
    console.print(f"[green]✓[/green] Indexed {count} question files\n")


@metadata.command()
@click.option(
    "--db",
    type=click.Path(),
    default=".vbagent/metadata.db",
    help="Path to metadata database",
)
@click.option("--topic", help="Filter by topic")
@click.option(
    "--difficulty",
    type=click.Choice(["easy", "medium", "hard"], case_sensitive=False),
    help="Filter by difficulty",
)
@click.option("--chapter", help="Filter by chapter")
@click.option("--type", "question_type", help="Filter by question type")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "paths"], case_sensitive=False),
    default="table",
    help="Output format",
)
def query(
    db: str,
    topic: str | None,
    difficulty: str | None,
    chapter: str | None,
    question_type: str | None,
    tags: str | None,
    limit: int | None,
    output_format: str,
):
    """Query questions by metadata filters.
    
    Examples:
        vbagent metadata query --topic Kinematics
        vbagent metadata query --difficulty medium --chapter Mechanics
        vbagent metadata query --tags "motion,graphs" --limit 10
        vbagent metadata query --type mcq_sc --format json
    """
    console = Console()
    db_path = Path(db)
    
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found: {db_path}")
        console.print("[dim]Run 'vbagent metadata index' first[/dim]")
        return
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    with MetadataStore(db_path) as store:
        results = store.query(
            topic=topic,
            difficulty=difficulty,
            chapter=chapter,
            question_type=question_type,
            tags=tag_list,
            limit=limit,
        )
    
    if not results:
        console.print("[yellow]No questions found matching the criteria[/yellow]")
        return
    
    # Output results
    if output_format == "json":
        output = [r.to_dict() for r in results]
        console.print(json.dumps(output, indent=2))
    
    elif output_format == "paths":
        for result in results:
            console.print(result.file_path)
    
    else:  # table
        table = Table(title=f"Query Results ({len(results)} questions)")
        table.add_column("File", style="cyan", no_wrap=False)
        table.add_column("Chapter", style="blue")
        table.add_column("Topic", style="green")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Type", style="magenta")
        table.add_column("Usage", style="dim")
        
        for result in results:
            # Shorten file path for display
            file_display = str(Path(result.file_path).name)
            
            table.add_row(
                file_display,
                result.chapter or "-",
                result.topic or "-",
                result.difficulty or "-",
                result.question_type or "-",
                str(result.usage_count),
            )
        
        console.print(table)


@metadata.command()
@click.option(
    "--db",
    type=click.Path(),
    default=".vbagent/metadata.db",
    help="Path to metadata database",
)
def stats(db: str):
    """Show question bank statistics.
    
    Displays aggregate statistics including counts by chapter, difficulty,
    topic, and question type, as well as most/least used questions.
    
    Example:
        vbagent metadata stats
        vbagent metadata stats --db custom.db
    """
    console = Console()
    db_path = Path(db)
    
    if not db_path.exists():
        console.print(f"[red]Error:[/red] Database not found: {db_path}")
        console.print("[dim]Run 'vbagent metadata index' first[/dim]")
        return
    
    with MetadataStore(db_path) as store:
        statistics = store.get_statistics()
    
    # Display statistics
    console.print(f"\n[bold cyan]Question Bank Statistics[/bold cyan]\n")
    console.print(f"[bold]Total Questions:[/bold] {statistics['total_questions']}\n")
    
    # By chapter
    if statistics["by_chapter"]:
        table = Table(title="By Chapter", show_header=True)
        table.add_column("Chapter", style="cyan")
        table.add_column("Count", style="green", justify="right")
        
        for chapter, count in statistics["by_chapter"].items():
            table.add_row(chapter, str(count))
        
        console.print(table)
        console.print()
    
    # By difficulty
    if statistics["by_difficulty"]:
        table = Table(title="By Difficulty", show_header=True)
        table.add_column("Difficulty", style="yellow")
        table.add_column("Count", style="green", justify="right")
        
        for diff, count in statistics["by_difficulty"].items():
            table.add_row(diff, str(count))
        
        console.print(table)
        console.print()
    
    # By topic
    if statistics["by_topic"]:
        table = Table(title="By Topic (Top 10)", show_header=True)
        table.add_column("Topic", style="blue")
        table.add_column("Count", style="green", justify="right")
        
        for topic, count in list(statistics["by_topic"].items())[:10]:
            table.add_row(topic, str(count))
        
        console.print(table)
        console.print()
    
    # By type
    if statistics["by_type"]:
        table = Table(title="By Question Type", show_header=True)
        table.add_column("Type", style="magenta")
        table.add_column("Count", style="green", justify="right")
        
        for qtype, count in statistics["by_type"].items():
            table.add_row(qtype, str(count))
        
        console.print(table)
        console.print()
    
    # Most used
    if statistics["most_used"]:
        table = Table(title="Most Used Questions", show_header=True)
        table.add_column("File", style="cyan", no_wrap=False)
        table.add_column("Usage Count", style="green", justify="right")
        table.add_column("Last Used", style="dim")
        
        for item in statistics["most_used"]:
            file_display = str(Path(item["file_path"]).name)
            last_used = item["last_used"] or "Never"
            if last_used != "Never":
                # Format timestamp
                from datetime import datetime
                dt = datetime.fromisoformat(last_used)
                last_used = dt.strftime("%Y-%m-%d %H:%M")
            
            table.add_row(
                file_display,
                str(item["usage_count"]),
                last_used,
            )
        
        console.print(table)
        console.print()
    
    # Least used
    if statistics["least_used"]:
        console.print(
            Panel(
                "\n".join([Path(p).name for p in statistics["least_used"][:5]]),
                title="Unused Questions (Sample)",
                border_style="dim",
            )
        )
        console.print()


if __name__ == "__main__":
    metadata()
