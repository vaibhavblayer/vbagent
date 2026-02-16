"""CLI result formatting utilities.

This module provides utilities for formatting results, diffs, and statistics
for display in the CLI using Rich components.
"""

from typing import Any, Optional
import difflib


def format_result_table(result: Any, title: str) -> "Table":
    """Format any result as a rich table.
    
    Creates a two-column table (Field, Value) for displaying structured results.
    Automatically handles common result types and converts values to strings.
    
    Args:
        result: Result object to format (typically a Pydantic model or dict)
        title: Title for the table
        
    Returns:
        Rich Table instance ready for display
        
    Examples:
        >>> from vbagent.models.classification import ClassificationResult
        >>> result = ClassificationResult(...)
        >>> table = format_result_table(result, "Classification Result")
        >>> console.print(table)
    """
    from rich.table import Table
    
    table = Table(title=title, show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    # Handle different result types
    if hasattr(result, 'model_dump'):
        # Pydantic model
        data = result.model_dump()
    elif hasattr(result, '__dict__'):
        # Regular object
        data = result.__dict__
    elif isinstance(result, dict):
        # Dictionary
        data = result
    else:
        # Fallback: convert to string
        table.add_row("Result", str(result))
        return table
    
    # Add rows for each field
    for key, value in data.items():
        # Format field name (convert snake_case to Title Case)
        field_name = key.replace('_', ' ').title()
        
        # Format value
        if value is None:
            formatted_value = "[dim]None[/dim]"
        elif isinstance(value, bool):
            formatted_value = "Yes" if value else "No"
        elif isinstance(value, float):
            # Format floats with 2 decimal places
            formatted_value = f"{value:.2f}"
        elif isinstance(value, list):
            # Join list items
            formatted_value = ", ".join(str(v) for v in value) if value else "[dim]empty[/dim]"
        elif isinstance(value, dict):
            # Format dict as key: value pairs
            formatted_value = ", ".join(f"{k}: {v}" for k, v in value.items()) if value else "[dim]empty[/dim]"
        else:
            formatted_value = str(value)
        
        table.add_row(field_name, formatted_value)
    
    return table


def format_diff(old: str, new: str, filename: Optional[str] = None) -> str:
    """Format diff for terminal display.
    
    Creates a unified diff between old and new content with color-coded
    additions and deletions suitable for terminal display.
    
    Args:
        old: Original content
        new: Modified content
        filename: Optional filename for diff header (default: "file")
        
    Returns:
        Formatted diff string with ANSI color codes
        
    Examples:
        >>> old = "Hello world"
        >>> new = "Hello Python world"
        >>> diff = format_diff(old, new, "example.txt")
        >>> print(diff)
    """
    if filename is None:
        filename = "file"
    
    # Split into lines
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    # Ensure lines end with newline for difflib
    if old_lines and not old_lines[-1].endswith('\n'):
        old_lines[-1] += '\n'
    if new_lines and not new_lines[-1].endswith('\n'):
        new_lines[-1] += '\n'
    
    # Generate unified diff
    diff_lines = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=''
    )
    
    # Format with colors
    formatted_lines = []
    for line in diff_lines:
        if line.startswith('+++') or line.startswith('---'):
            # File headers - bold
            formatted_lines.append(f"[bold]{line}[/bold]")
        elif line.startswith('@@'):
            # Hunk headers - cyan
            formatted_lines.append(f"[cyan]{line}[/cyan]")
        elif line.startswith('+'):
            # Additions - green
            formatted_lines.append(f"[green]{line}[/green]")
        elif line.startswith('-'):
            # Deletions - red
            formatted_lines.append(f"[red]{line}[/red]")
        else:
            # Context - default
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def format_stats(stats: dict, title: Optional[str] = None) -> "Table":
    """Format statistics as a table.
    
    Creates a two-column table (Metric, Value) for displaying statistics.
    Automatically formats numbers with appropriate precision and adds
    visual styling.
    
    Args:
        stats: Dictionary of statistics (metric_name -> value)
        title: Optional title for the table (default: "Statistics")
        
    Returns:
        Rich Table instance ready for display
        
    Examples:
        >>> stats = {"total": 100, "success": 95, "failed": 5, "rate": 0.95}
        >>> table = format_stats(stats, "Processing Statistics")
        >>> console.print(table)
    """
    from rich.table import Table
    
    if title is None:
        title = "Statistics"
    
    table = Table(title=title, show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    
    for key, value in stats.items():
        # Format metric name (convert snake_case to Title Case)
        metric_name = key.replace('_', ' ').title()
        
        # Format value
        if isinstance(value, float):
            # Check if it looks like a percentage (0-1 range)
            if 0 <= value <= 1:
                formatted_value = f"{value:.1%}"
            else:
                formatted_value = f"{value:.2f}"
        elif isinstance(value, int):
            # Add thousand separators for large numbers
            formatted_value = f"{value:,}"
        elif isinstance(value, dict):
            # For nested dicts, show count
            formatted_value = f"{len(value)} items"
        elif isinstance(value, list):
            # For lists, show count
            formatted_value = f"{len(value)} items"
        else:
            formatted_value = str(value)
        
        table.add_row(metric_name, formatted_value)
    
    return table
