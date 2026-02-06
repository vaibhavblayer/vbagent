"""Utility commands for file management.

Provides helper commands for organizing and managing question files.
"""

import click
from pathlib import Path
from typing import Optional


def _get_console():
    """Lazy import of rich Console."""
    from rich.console import Console
    return Console()


def _get_prompt():
    """Lazy import of rich Prompt."""
    from rich.prompt import Prompt, Confirm
    return Prompt, Confirm


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

# Supported image extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
TEX_EXTENSIONS = {".tex"}


@click.group(context_settings=CONTEXT_SETTINGS)
def util():
    """Utility commands for file management.
    
    \b
    Commands:
        rename   - Rename files to serialized format (Problem_1.png, etc.)
        count    - Count files by type in a directory
        clean    - Remove generated files (agentic/, .vbagent.json)
    
    \b
    Examples:
        vbagent util rename images/
        vbagent util rename . --prefix Question --ext .tex
        vbagent util count images/
        vbagent util clean
    """
    pass


@util.command()
@click.argument("directory", type=click.Path(exists=True), default=".")
@click.option("--prefix", "-p", default="problem", help="Prefix for renamed files (default: problem)")
@click.option("--start", "-s", type=int, default=1, help="Starting number")
@click.option("--ext", "-e", multiple=True, help="File extensions to rename (default: images)")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be renamed without doing it")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--preserve-order", "-o", is_flag=True, help="Preserve existing numerical order (Problem_1 → problem_1)")
@click.option("--shuffle", is_flag=True, help="Randomize file order before renaming")
@click.option("--lowercase", "-l", is_flag=True, default=True, help="Use lowercase prefix (default: True)")
@click.option("--uppercase", "-u", is_flag=True, help="Use uppercase prefix (Problem_1)")
@click.option("--pad", type=int, default=0, help="Zero-pad numbers (--pad 3 → problem_001.png)")
def rename(directory: str, prefix: str, start: int, ext: tuple, dry_run: bool, yes: bool,
           preserve_order: bool, shuffle: bool, lowercase: bool, uppercase: bool, pad: int):
    """Rename files to serialized format.
    
    Renames files in a directory to a consistent format like:
    problem_1.png, problem_2.png, problem_3.png, etc.
    
    \b
    Examples:
        vbagent util rename images/                    # Rename to problem_N.png
        vbagent util rename . --prefix Q               # q_1.png, q_2.png, ...
        vbagent util rename . --ext .tex               # Rename .tex files
        vbagent util rename . --start 10               # Start from problem_10.png
        vbagent util rename images/ --dry-run          # Preview changes
        vbagent util rename . --preserve-order         # Keep existing numbers
        vbagent util rename . --shuffle                # Randomize order
        vbagent util rename . --uppercase              # Problem_1.png
        vbagent util rename . --pad 3                  # problem_001.png
    """
    import re
    import random
    
    console = _get_console()
    _, Confirm = _get_prompt()
    
    dir_path = Path(directory)
    
    # Determine extensions to process
    if ext:
        extensions = {e if e.startswith(".") else f".{e}" for e in ext}
    else:
        extensions = IMAGE_EXTENSIONS
    
    # Find matching files
    files = []
    for f in dir_path.iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    
    if not files:
        console.print(f"[yellow]No files found with extensions: {', '.join(extensions)}[/yellow]")
        return
    
    # Sort files
    if preserve_order:
        # Extract numbers from filenames and sort numerically
        def extract_number(f: Path) -> int:
            match = re.search(r'(\d+)', f.stem)
            return int(match.group(1)) if match else 0
        files.sort(key=extract_number)
    elif shuffle:
        random.shuffle(files)
    else:
        # Natural sort (handles Problem_1, Problem_2, Problem_10 correctly)
        def natural_sort_key(f: Path) -> list:
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', f.name)]
        files.sort(key=natural_sort_key)
    
    console.print(f"[cyan]Found {len(files)} file(s) to rename[/cyan]")
    
    # Determine prefix case
    if uppercase:
        final_prefix = prefix.title() if prefix.islower() else prefix
    else:
        final_prefix = prefix.lower()
    
    # Generate new names
    renames = []
    for i, f in enumerate(files, start):
        if pad > 0:
            num_str = str(i).zfill(pad)
        else:
            num_str = str(i)
        new_name = f"{final_prefix}_{num_str}{f.suffix.lower()}"
        new_path = f.parent / new_name
        renames.append((f, new_path))
    
    # Show preview
    console.print("\n[bold]Rename plan:[/bold]")
    for old, new in renames:
        if old.name != new.name:
            console.print(f"  {old.name} → [green]{new.name}[/green]")
        else:
            console.print(f"  {old.name} [dim](no change)[/dim]")
    
    if dry_run:
        console.print("\n[dim]Dry run - no files were renamed[/dim]")
        return
    
    # Confirm
    if not yes:
        if not Confirm.ask("\nProceed with rename?", default=False):
            console.print("[dim]Cancelled[/dim]")
            return
    
    # Perform rename (use temp names to avoid conflicts)
    temp_renames = []
    for old, new in renames:
        if old != new:
            temp = old.parent / f".tmp_{old.name}"
            old.rename(temp)
            temp_renames.append((temp, new))
    
    # Final rename from temp
    renamed_count = 0
    for temp, new in temp_renames:
        temp.rename(new)
        renamed_count += 1
    
    console.print(f"\n[green]✓[/green] Renamed {renamed_count} file(s)")


@util.command()
@click.argument("directory", type=click.Path(exists=True), default=".")
@click.option("--recursive", "-r", is_flag=True, help="Count recursively")
def count(directory: str, recursive: bool):
    """Count files by type in a directory.
    
    \b
    Examples:
        vbagent util count images/
        vbagent util count . --recursive
    """
    console = _get_console()
    
    dir_path = Path(directory)
    
    # Count by extension
    counts: dict[str, int] = {}
    
    if recursive:
        files = dir_path.rglob("*")
    else:
        files = dir_path.iterdir()
    
    for f in files:
        if f.is_file():
            ext = f.suffix.lower() or "(no extension)"
            counts[ext] = counts.get(ext, 0) + 1
    
    if not counts:
        console.print("[yellow]No files found[/yellow]")
        return
    
    # Display
    console.print(f"\n[bold]File counts in {directory}:[/bold]\n")
    
    total = 0
    for ext, count in sorted(counts.items(), key=lambda x: -x[1]):
        # Categorize
        if ext in IMAGE_EXTENSIONS:
            category = "[cyan]image[/cyan]"
        elif ext in TEX_EXTENSIONS:
            category = "[green]tex[/green]"
        elif ext == ".json":
            category = "[yellow]json[/yellow]"
        else:
            category = "[dim]other[/dim]"
        
        console.print(f"  {ext:15} {count:5}  {category}")
        total += count
    
    console.print(f"\n  [bold]Total:[/bold]         {total}")


@util.command()
@click.option("--output", "-o", is_flag=True, help="Remove agentic/ output directory")
@click.option("--config", "-c", is_flag=True, help="Remove .vbagent.json workspace config")
@click.option("--cache", is_flag=True, help="Remove __pycache__ and .hypothesis")
@click.option("--all", "-a", "all_", is_flag=True, help="Remove all generated files")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clean(output: bool, config: bool, cache: bool, all_: bool, yes: bool):
    """Remove generated files and directories.
    
    \b
    Examples:
        vbagent util clean --output     # Remove agentic/ directory
        vbagent util clean --config     # Remove .vbagent.json
        vbagent util clean --all        # Remove everything
        vbagent util clean -a -y        # Remove all without confirmation
    """
    import shutil
    
    console = _get_console()
    _, Confirm = _get_prompt()
    
    if all_:
        output = config = cache = True
    
    if not (output or config or cache):
        console.print("[yellow]Specify what to clean: --output, --config, --cache, or --all[/yellow]")
        return
    
    to_remove = []
    
    if output:
        agentic = Path("agentic")
        if agentic.exists():
            to_remove.append(("agentic/", agentic))
    
    if config:
        vbagent_json = Path(".vbagent.json")
        if vbagent_json.exists():
            to_remove.append((".vbagent.json", vbagent_json))
    
    if cache:
        for p in Path(".").rglob("__pycache__"):
            to_remove.append((str(p), p))
        hypothesis = Path(".hypothesis")
        if hypothesis.exists():
            to_remove.append((".hypothesis/", hypothesis))
    
    if not to_remove:
        console.print("[green]Nothing to clean[/green]")
        return
    
    console.print("[bold]Will remove:[/bold]")
    for name, _ in to_remove:
        console.print(f"  [red]✗[/red] {name}")
    
    if not yes:
        if not Confirm.ask("\nProceed?", default=False):
            console.print("[dim]Cancelled[/dim]")
            return
    
    for name, path in to_remove:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        console.print(f"[green]✓[/green] Removed {name}")


@util.command()
@click.argument("directory", type=click.Path(exists=True), default=".")
@click.option("--ext", "-e", multiple=True, default=[".png", ".jpg", ".jpeg"], help="Extensions to list")
def list(directory: str, ext: tuple):
    """List files ready for processing.
    
    Shows files that can be processed with `vbagent process`.
    
    \b
    Examples:
        vbagent util list images/
        vbagent util list . --ext .tex
    """
    console = _get_console()
    
    dir_path = Path(directory)
    extensions = {e if e.startswith(".") else f".{e}" for e in ext}
    
    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    
    if not files:
        console.print(f"[yellow]No files found with extensions: {', '.join(extensions)}[/yellow]")
        return
    
    console.print(f"\n[bold]Files in {directory}:[/bold]\n")
    for i, f in enumerate(files, 1):
        console.print(f"  {i:3}. {f.name}")
    
    console.print(f"\n[dim]Total: {len(files)} file(s)[/dim]")
    console.print(f"[dim]Process with: vbagent process -i {files[0]} -r 1 {len(files)}[/dim]")
