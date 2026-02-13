"""Common UI components for consistent terminal output."""

from typing import Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from contextlib import contextmanager
import time

# Status indicators
STATUS_SUCCESS = "[✓]"
STATUS_ERROR = "[✗]"
STATUS_WARNING = "[!]"
STATUS_INFO = "[i]"

# Box drawing
BOX_TOP = "┌─"
BOX_BOTTOM = "└─"
BOX_MID = "├─"
BOX_VERT = "│"
BOX_HORIZ = "─"


def print_section(console: Console, title: str, content: dict, style: str = "cyan"):
    """Print a structured section with key-value pairs."""
    # Calculate max key length for alignment
    max_key_len = max(len(k) for k in content.keys()) if content else 0
    
    lines = []
    for key, value in content.items():
        padded_key = key.ljust(max_key_len)
        lines.append(f"{padded_key} : {value}")
    
    panel = Panel(
        "\n".join(lines),
        title=f"[bold]{title}[/bold]",
        border_style=style,
        padding=(0, 1)
    )
    console.print(panel)


def print_status(console: Console, message: str, status: str = "success"):
    """Print a status message with indicator."""
    indicators = {
        "success": (STATUS_SUCCESS, "green"),
        "error": (STATUS_ERROR, "red"),
        "warning": (STATUS_WARNING, "yellow"),
        "info": (STATUS_INFO, "cyan"),
    }
    indicator, color = indicators.get(status, (STATUS_INFO, "cyan"))
    console.print(f"[{color}]{indicator}[/{color}] {message}")


@contextmanager
def agent_spinner(console: Console, agent_name: str, model: str, reasoning: str):
    """Context manager for agent execution with spinner."""
    start_time = time.time()
    
    # Create progress with spinner
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        TextColumn("│"),
        TextColumn("[dim]{task.fields[model]}[/dim]"),
        TextColumn("│"),
        TextColumn("[dim]{task.fields[reasoning]} reasoning[/dim]"),
        console=console,
        transient=True  # Remove after completion
    )
    
    with progress:
        task = progress.add_task(
            agent_name,
            model=model,
            reasoning=reasoning,
            total=None  # Indeterminate
        )
        
        try:
            yield progress
        finally:
            duration = time.time() - start_time
            progress.stop()
            # Print completion status
            console.print(
                f"[dim]{BOX_VERT} {agent_name} │ {model} │ {duration:.1f}s[/dim]"
            )


def print_agent_result(console: Console, agent_name: str, duration: float, status: str = "success"):
    """Print agent completion result."""
    indicator = STATUS_SUCCESS if status == "success" else STATUS_ERROR
    color = "green" if status == "success" else "red"
    console.print(f"[{color}]{indicator}[/{color}] {agent_name} completed in {duration:.1f}s")


def print_classification(console: Console, data: dict):
    """Print classification results in structured format."""
    content = {
        "Type": data.get("question_type", "unknown"),
        "Confidence": f"{data.get('confidence', 0) * 100:.1f}%",
        "Chapter": data.get("chapter", "N/A"),
        "Topic": data.get("topic", "N/A"),
    }
    
    if data.get("has_diagram"):
        content["Diagram"] = f"Yes ({data.get('diagram_type', 'unknown')})"
    else:
        content["Diagram"] = "No"
    
    print_section(console, "Classification", content, style="cyan")


def print_difficulty(console: Console, data: dict):
    """Print difficulty assessment in structured format."""
    content = {
        "Level": f"{data.get('difficulty', 'unknown').title()} ({data.get('difficulty_score', 0):.1f}/10)",
        "Expected Time": f"{data.get('expected_solve_time_minutes', 0)} minutes",
        "Cognitive Level": data.get('cognitive_level', 'unknown').title(),
    }
    
    if data.get('expected_error_rate'):
        content["Error Rate"] = f"{data.get('expected_error_rate') * 100:.0f}%"
    
    lines = ["\n".join(f"{k.ljust(15)} : {v}" for k, v in content.items())]
    
    # Add prerequisites
    if data.get('prerequisite_concepts'):
        lines.append("\nPrerequisites:")
        for concept in data['prerequisite_concepts'][:3]:  # Show first 3
            lines.append(f"  • {concept}")
    
    # Add common mistakes
    if data.get('common_mistakes'):
        lines.append("\nCommon Mistakes:")
        for mistake in data['common_mistakes'][:2]:  # Show first 2
            lines.append(f"  • {mistake}")
    
    panel = Panel(
        "\n".join(lines),
        title="[bold]Difficulty Assessment[/bold]",
        border_style="yellow",
        padding=(0, 1)
    )
    console.print(panel)


def print_latex_result(console: Console, line_count: int, has_solution: bool, duration: float):
    """Print LaTeX extraction result."""
    content = {
        "Status": f"{STATUS_SUCCESS} Complete",
        "Duration": f"{duration:.1f}s",
        "Lines": str(line_count),
        "Has Solution": "Yes" if has_solution else "No",
    }
    print_section(console, "LaTeX Extraction", content, style="green")


def print_debug_input(console: Console, agent_name: str, model: str, reasoning: str, input_text: str):
    """Print debug input in structured format."""
    content = [
        f"Agent      : {agent_name}",
        f"Model      : {model}",
        f"Reasoning  : {reasoning}",
        "",
        input_text,
    ]
    
    panel = Panel(
        "\n".join(content),
        title="[bold]DEBUG - INPUT[/bold]",
        border_style="yellow",
        padding=(0, 1)
    )
    console.print(panel)


def print_debug_output(console: Console, agent_name: str, duration: float, output: str):
    """Print debug output in structured format."""
    content = [
        f"Agent      : {agent_name}",
        f"Duration   : {duration:.2f}s",
        f"Status     : Success",
        "",
        output,
    ]
    
    panel = Panel(
        "\n".join(content),
        title="[bold]DEBUG - OUTPUT[/bold]",
        border_style="green",
        padding=(0, 1)
    )
    console.print(panel)


@contextmanager
def parallel_progress(console: Console, tasks: list[tuple[str, str]]):
    """Context manager for parallel task execution with live progress.
    
    Args:
        tasks: List of (task_name, model) tuples
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}[/bold]"),
        TextColumn("│"),
        TextColumn("[dim]{task.fields[model]}[/dim]"),
        TextColumn("│"),
        TextColumn("{task.fields[status]}"),
        console=console,
        transient=False
    )
    
    task_ids = {}
    with progress:
        for task_name, model in tasks:
            task_id = progress.add_task(
                task_name,
                model=model,
                status="[yellow]Running...[/yellow]",
                total=None
            )
            task_ids[task_name] = task_id
        
        yield progress, task_ids
