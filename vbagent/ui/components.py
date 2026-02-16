"""Reusable UI components."""

from typing import Optional
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.console import Console
from rich.syntax import Syntax


def create_panel(
    content: str,
    title: Optional[str] = None,
    style: str = "cyan",
    border_style: str = "bright_cyan",
) -> Panel:
    """Create a styled panel.
    
    Args:
        content: Panel content
        title: Optional title
        style: Content style
        border_style: Border style
        
    Returns:
        Configured Panel
    """
    return Panel(
        content,
        title=title,
        style=style,
        border_style=border_style,
        padding=(1, 2),
    )


def create_progress() -> Progress:
    """Create a styled progress bar.
    
    Returns:
        Configured Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=Console(),
    )


def create_code_block(
    code: str,
    language: str = "python",
    theme: str = "monokai",
    line_numbers: bool = False,
) -> Syntax:
    """Create a syntax-highlighted code block.
    
    Args:
        code: Code to display
        language: Programming language
        theme: Syntax theme
        line_numbers: Whether to show line numbers
        
    Returns:
        Syntax object
    """
    return Syntax(
        code,
        language,
        theme=theme,
        line_numbers=line_numbers,
        word_wrap=True,
    )
