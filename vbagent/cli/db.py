"""CLI commands for database management."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track


def _get_config():
    """Lazy import config."""
    from vbagent.config import get_config
    return get_config()


def _get_db_path() -> Path:
    """Get database path from config or default."""
    config = _get_config()
    if hasattr(config, 'database_path') and config.database_path:
        return Path(config.database_path).expanduser()
    return Path.home() / '.config' / 'vbagent' / 'database.db'


def _save_db_path(db_path: Path):
    """Save database path to config."""
    config_file = Path.home() / '.config' / 'vbagent' / 'config.json'
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    config_data = {}
    if config_file.exists():
        config_data = json.loads(config_file.read_text())
    
    config_data['database_path'] = str(db_path)
    config_file.write_text(json.dumps(config_data, indent=2))


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def db():
    """Database management for question bank.
    
    \b
    Commands:
        init     - Initialize database from directory
        insert   - Insert problems into database
        update   - Update existing question
        query    - Query questions with filters
        stats    - Show database statistics
        export   - Export questions from database
        delete   - Delete question by ID
    """
    pass


@db.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--db-path", type=click.Path(), help="Custom database location")
@click.option("--force", is_flag=True, help="Recreate database if exists")
@click.option("--recursive/--no-recursive", default=True, help="Scan subdirectories")
def init(path: str, db_path: str, force: bool, recursive: bool):
    """Initialize database from directory.
    
    \b
    Examples:
        vbagent db init ./questions
        vbagent db init --db-path custom.db --force
        vbagent db init  # Check existing database
    """
    from vbagent.database import QuestionDatabase, ContentExtractor
    
    console = Console()
    
    # Determine database path
    if db_path:
        db_file = Path(db_path)
    else:
        db_file = _get_db_path()
    
    # Check if database exists
    if db_file.exists() and not force:
        console.print(f"\n[green]✓[/green] Database already exists at: [cyan]{db_file}[/cyan]\n")
        
        # Show stats
        with QuestionDatabase(db_file) as database:
            stats = database.get_stats()
        
        # Display stats
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Total entries", str(stats['total_entries']))
        table.add_row("Standalone questions", str(stats['standalone_questions']))
        table.add_row("Passage sets", str(stats['passage_sets']))
        table.add_row("Sub-questions in passages", str(stats['passage_subquestions']))
        table.add_row("Effective question count", str(stats['effective_question_count']))
        
        console.print(table)
        console.print()
        return
    
    # Need path to initialize
    if not path:
        console.print("[red]Error:[/red] PATH required to initialize new database")
        console.print("[dim]Usage: vbagent db init <path>[/dim]")
        return
    
    # Create database
    console.print(f"\n[cyan]Initializing database at:[/cyan] {db_file}")
    console.print(f"[cyan]Scanning directory:[/cyan] {path}\n")
    
    dir_path = Path(path)
    
    # Find all .tex files
    if recursive:
        tex_files = list(dir_path.rglob("*.tex"))
    else:
        tex_files = list(dir_path.glob("*.tex"))
    
    if not tex_files:
        console.print("[yellow]No .tex files found[/yellow]")
        return
    
    console.print(f"[green]Found {len(tex_files)} .tex files[/green]\n")
    
    # Create database and insert
    with QuestionDatabase(db_file) as database:
        total_questions = 0
        
        for tex_file in track(tex_files, description="Processing files..."):
            try:
                records = ContentExtractor.extract_from_file(tex_file)
                
                if not records:
                    continue
                
                # Insert records
                if records[0].is_passage:
                    # Insert parent first
                    parent_id = database.insert(records[0])
                    # Insert children with parent_id
                    for child in records[1:]:
                        child.parent_question_id = parent_id
                        database.insert(child)
                    total_questions += 1
                else:
                    # Insert standalone questions
                    for record in records:
                        database.insert(record)
                        total_questions += 1
            
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Failed to process {tex_file.name}: {e}")
    
    # Save database path to config
    _save_db_path(db_file)
    
    console.print(f"\n[green]✓[/green] Database initialized with {total_questions} questions")
    console.print(f"[dim]Database path saved to config[/dim]\n")


@db.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--db-path", type=click.Path(), help="Database location")
@click.option("--recursive/--no-recursive", default=True, help="Scan subdirectories")
@click.option("--update-existing", is_flag=True, help="Update existing entries")
@click.option("--classify", is_flag=True, help="Force classification for metadata")
def insert(path: str, db_path: str, recursive: bool, update_existing: bool, classify: bool):
    """Insert problems into database.
    
    \b
    Examples:
        vbagent db insert ./new_questions
        vbagent db insert ./questions --update-existing
        vbagent db insert ./questions --classify
    """
    from vbagent.database import QuestionDatabase, ContentExtractor
    
    console = Console()
    
    db_file = Path(db_path) if db_path else _get_db_path()
    
    if not db_file.exists():
        console.print("[red]Error:[/red] Database not found. Run 'vbagent db init' first")
        return
    
    dir_path = Path(path)
    
    # Find all .tex files
    if recursive:
        tex_files = list(dir_path.rglob("*.tex"))
    else:
        tex_files = list(dir_path.glob("*.tex"))
    
    if not tex_files:
        console.print("[yellow]No .tex files found[/yellow]")
        return
    
    console.print(f"\n[cyan]Inserting from:[/cyan] {path}")
    console.print(f"[green]Found {len(tex_files)} .tex files[/green]\n")
    
    with QuestionDatabase(db_file) as database:
        inserted = 0
        skipped = 0
        
        for tex_file in track(tex_files, description="Processing files..."):
            try:
                records = ContentExtractor.extract_from_file(tex_file)
                
                if not records:
                    continue
                
                # Insert records
                if records[0].is_passage:
                    parent_id = database.insert(records[0])
                    for child in records[1:]:
                        child.parent_question_id = parent_id
                        database.insert(child)
                    inserted += 1
                else:
                    for record in records:
                        database.insert(record)
                        inserted += 1
            
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] {tex_file.name}: {e}")
                skipped += 1
    
    console.print(f"\n[green]✓[/green] Inserted: {inserted}, Skipped: {skipped}\n")


@db.command()
@click.option("--db-path", type=click.Path(), help="Database location")
@click.option("--subject", help="Filter by subject")
@click.option("--chapter", help="Filter by chapter")
@click.option("--topic", help="Filter by topic")
@click.option("--difficulty", type=click.Choice(["easy", "medium", "hard"]), help="Filter by difficulty")
@click.option("--type", "question_type", help="Filter by question type")
@click.option("--limit", type=int, help="Limit results")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def query(db_path: str, subject: str, chapter: str, topic: str, difficulty: str,
          question_type: str, limit: int, output_format: str):
    """Query questions with filters.
    
    \b
    Examples:
        vbagent db query --topic Kinematics
        vbagent db query --difficulty medium --subject physics
        vbagent db query --type passage --format json
    """
    from vbagent.database import QuestionDatabase
    
    console = Console()
    db_file = Path(db_path) if db_path else _get_db_path()
    
    if not db_file.exists():
        console.print("[red]Error:[/red] Database not found")
        return
    
    with QuestionDatabase(db_file) as database:
        results = database.query(
            subject=subject,
            chapter=chapter,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            limit=limit
        )
    
    if not results:
        console.print("[yellow]No questions found[/yellow]")
        return
    
    if output_format == "json":
        output = [
            {
                'id': r.id,
                'file_path': r.file_path,
                'question_type': r.question_type,
                'subject': r.subject,
                'topic': r.topic,
                'difficulty': r.difficulty,
                'is_passage': r.is_passage,
                'num_subquestions': r.num_subquestions,
            }
            for r in results
        ]
        console.print(json.dumps(output, indent=2))
    else:
        table = Table(title=f"Query Results ({len(results)} questions)")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Subject", style="blue")
        table.add_column("Topic", style="green")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Usage", style="dim")
        
        for r in results:
            qtype = f"{r.question_type}"
            if r.is_passage:
                qtype += f" ({r.num_subquestions})"
            
            table.add_row(
                str(r.id),
                qtype,
                r.subject or "-",
                r.topic or "-",
                r.difficulty or "-",
                str(r.usage_count)
            )
        
        console.print(table)


@db.command()
@click.option("--db-path", type=click.Path(), help="Database location")
@click.option("--subject", help="Filter by subject")
def stats(db_path: str, subject: str):
    """Show database statistics.
    
    \b
    Examples:
        vbagent db stats
        vbagent db stats --subject physics
    """
    from vbagent.database import QuestionDatabase
    
    console = Console()
    db_file = Path(db_path) if db_path else _get_db_path()
    
    if not db_file.exists():
        console.print("[red]Error:[/red] Database not found")
        return
    
    with QuestionDatabase(db_file) as database:
        stats_data = database.get_stats()
    
    console.print(f"\n[bold cyan]Database Statistics[/bold cyan]")
    console.print(f"[dim]Location: {db_file}[/dim]\n")
    
    # Overview
    table = Table(title="Overview")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green", justify="right")
    
    table.add_row("Total entries", str(stats_data['total_entries']))
    table.add_row("Standalone questions", str(stats_data['standalone_questions']))
    table.add_row("Passage sets", str(stats_data['passage_sets']))
    table.add_row("Sub-questions", str(stats_data['passage_subquestions']))
    table.add_row("Effective questions", str(stats_data['effective_question_count']))
    
    console.print(table)
    console.print()
    
    # By subject
    if stats_data['by_subject']:
        table = Table(title="By Subject")
        table.add_column("Subject", style="blue")
        table.add_column("Count", style="green", justify="right")
        
        for subj, count in stats_data['by_subject'].items():
            table.add_row(subj, str(count))
        
        console.print(table)
        console.print()
    
    # By difficulty
    if stats_data['by_difficulty']:
        table = Table(title="By Difficulty")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Count", style="green", justify="right")
        
        for diff, count in stats_data['by_difficulty'].items():
            table.add_row(diff, str(count))
        
        console.print(table)
        console.print()
    
    # By type
    if stats_data['by_type']:
        table = Table(title="By Question Type")
        table.add_column("Type", style="magenta")
        table.add_column("Count", style="green", justify="right")
        
        for qtype, count in stats_data['by_type'].items():
            table.add_row(qtype, str(count))
        
        console.print(table)
        console.print()


@db.command()
@click.argument("question_id", type=int)
@click.option("--db-path", type=click.Path(), help="Database location")
def delete(question_id: int, db_path: str):
    """Delete question by ID (cascade deletes children).
    
    \b
    Examples:
        vbagent db delete 42
    """
    from vbagent.database import QuestionDatabase
    
    console = Console()
    db_file = Path(db_path) if db_path else _get_db_path()
    
    if not db_file.exists():
        console.print("[red]Error:[/red] Database not found")
        return
    
    with QuestionDatabase(db_file) as database:
        record = database.get_by_id(question_id)
        if not record:
            console.print(f"[red]Error:[/red] Question ID {question_id} not found")
            return
        
        database.delete(question_id)
    
    console.print(f"[green]✓[/green] Deleted question ID {question_id}")
