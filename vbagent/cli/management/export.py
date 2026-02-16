"""CLI commands for exporting LaTeX files in different formats."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from vbagent.export import Exporter, ExportMode


console = Console()


@click.group()
def export():
    """Export LaTeX files in different formats."""
    pass


@export.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output directory for exported files'
)
@click.option(
    '--mode', '-m',
    type=click.Choice(['flat', 'structured', 'project'], case_sensitive=False),
    default='flat',
    help='Export mode: flat (single directory), structured (organized subdirs), '
         'or project (main.tex with \\input{})'
)
@click.option(
    '--template', '-t',
    type=click.Path(exists=True),
    help='Custom LaTeX template file (for project mode)'
)
@click.option(
    '--title',
    default='LaTeX Document',
    help='Document title (for project mode)'
)
def run(files, output, mode, template, title):
    """Export LaTeX files in the specified format.
    
    Examples:
    
        # Export files to a flat directory
        vbagent export run file1.tex file2.tex -o output/ -m flat
        
        # Export with structured organization
        vbagent export run questions/*.tex -o output/ -m structured
        
        # Export as a LaTeX project with main.tex
        vbagent export run *.tex -o output/ -m project --title "My DPP"
        
        # Use custom template for project mode
        vbagent export run *.tex -o output/ -m project -t template.tex
    """
    try:
        # Convert file paths
        file_paths = [Path(f) for f in files]
        output_dir = Path(output)
        
        # Parse mode
        export_mode = ExportMode(mode.lower())
        
        # Read custom template if provided
        template_content = None
        if template:
            template_path = Path(template)
            template_content = template_path.read_text()
        
        # Create exporter and export
        exporter = Exporter()
        
        console.print(f"[cyan]Exporting {len(file_paths)} files in {mode} mode...[/cyan]")
        
        result = exporter.export(
            files=file_paths,
            output_dir=output_dir,
            mode=export_mode,
            template=template_content,
            title=title
        )
        
        # Display results
        console.print(f"[green]✓[/green] Export completed successfully!")
        console.print(f"  Output directory: {result.output_dir}")
        console.print(f"  Files exported: {result.file_count}")
        console.print(f"  Mode: {result.mode.value}")
        
        if result.main_tex:
            console.print(f"  Main file: {result.main_tex}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Export failed: {str(e)}")
        raise click.Abort()


@export.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option(
    '--output', '-o',
    type=click.Path(),
    required=True,
    help='Output directory for exported files'
)
@click.option(
    '--mode', '-m',
    type=click.Choice(['flat', 'structured', 'project'], case_sensitive=False),
    default='flat',
    help='Export mode'
)
@click.option(
    '--pattern',
    default='*.tex',
    help='File pattern to match (default: *.tex)'
)
@click.option(
    '--recursive/--no-recursive',
    default=True,
    help='Search subdirectories recursively'
)
@click.option(
    '--template', '-t',
    type=click.Path(exists=True),
    help='Custom LaTeX template file (for project mode)'
)
@click.option(
    '--title',
    default='LaTeX Document',
    help='Document title (for project mode)'
)
def directory(directory, output, mode, pattern, recursive, template, title):
    """Export all LaTeX files from a directory.
    
    Examples:
    
        # Export all .tex files from a directory
        vbagent export directory questions/ -o output/ -m flat
        
        # Export with pattern matching
        vbagent export directory . -o output/ --pattern "dpp_*.tex"
        
        # Non-recursive export
        vbagent export directory questions/ -o output/ --no-recursive
    """
    try:
        dir_path = Path(directory)
        output_dir = Path(output)
        
        # Find matching files
        if recursive:
            file_paths = list(dir_path.rglob(pattern))
        else:
            file_paths = list(dir_path.glob(pattern))
        
        if not file_paths:
            console.print(f"[yellow]No files matching '{pattern}' found in {directory}[/yellow]")
            return
        
        # Parse mode
        export_mode = ExportMode(mode.lower())
        
        # Read custom template if provided
        template_content = None
        if template:
            template_path = Path(template)
            template_content = template_path.read_text()
        
        # Create exporter and export
        exporter = Exporter()
        
        console.print(f"[cyan]Exporting {len(file_paths)} files from {directory}...[/cyan]")
        
        result = exporter.export(
            files=file_paths,
            output_dir=output_dir,
            mode=export_mode,
            template=template_content,
            title=title
        )
        
        # Display results
        console.print(f"[green]✓[/green] Export completed successfully!")
        console.print(f"  Output directory: {result.output_dir}")
        console.print(f"  Files exported: {result.file_count}")
        console.print(f"  Mode: {result.mode.value}")
        
        if result.main_tex:
            console.print(f"  Main file: {result.main_tex}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Export failed: {str(e)}")
        raise click.Abort()


@export.command()
def modes():
    """Display information about available export modes."""
    table = Table(title="Export Modes")
    
    table.add_column("Mode", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Use Case", style="yellow")
    
    table.add_row(
        "flat",
        "All files in a single directory",
        "Simple exports, quick sharing"
    )
    table.add_row(
        "structured",
        "Organized subdirectories by type\n(questions/, solutions/, diagrams/, etc.)",
        "Large projects, organized workflows"
    )
    table.add_row(
        "project",
        "main.tex with \\input{} references\nto individual files",
        "Compilable LaTeX projects, DPPs"
    )
    
    console.print(table)
    console.print("\n[cyan]Examples:[/cyan]")
    console.print("  vbagent export run *.tex -o output/ -m flat")
    console.print("  vbagent export run *.tex -o output/ -m structured")
    console.print("  vbagent export run *.tex -o output/ -m project --title 'My DPP'")


if __name__ == '__main__':
    export()
