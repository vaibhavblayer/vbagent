"""Reusable UI components."""

from typing import Optional
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns
from rich import box


def create_panel(
    content,
    title: Optional[str] = None,
    style: str = "",
    border_style: str = "#5eead4",
    subtitle: Optional[str] = None,
    padding: tuple[int, int] = (1, 2),
) -> Panel:
    """Create a styled panel.

    Args:
        content: Panel content (str or Rich renderable)
        title: Optional title
        style: Content style
        border_style: Border style
        subtitle: Optional subtitle (bottom-right)
        padding: (vertical, horizontal) padding

    Returns:
        Configured Panel
    """
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        style=style,
        border_style=border_style,
        box=box.ROUNDED,
        padding=padding,
    )


def create_progress(show_time: bool = True) -> Progress:
    """Create a styled progress bar.

    Args:
        show_time: Whether to show elapsed time

    Returns:
        Configured Progress instance
    """
    cols = [
        SpinnerColumn(style="#5eead4"),
        TextColumn("[bold #5eead4]{task.description}"),
        BarColumn(bar_width=30, style="#374151", complete_style="#5eead4", finished_style="#4ade80"),
        TextColumn("[#e5e7eb]{task.percentage:>3.0f}%"),
    ]
    if show_time:
        cols.append(TimeElapsedColumn())

    return Progress(*cols, console=Console(), transient=True)


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


def create_status_line(label: str, value: str, color: str = "#5eead4") -> Text:
    """Create a colored label: value line.

    Args:
        label: Left-side label
        value: Right-side value
        color: Label color

    Returns:
        Rich Text object
    """
    t = Text()
    t.append(f"{label}: ", style=f"bold {color}")
    t.append(value, style="#e5e7eb")
    return t


def create_badge(text: str, variant: str = "info") -> str:
    """Create an inline badge string.

    Args:
        text: Badge text
        variant: One of success, error, warning, info

    Returns:
        Rich markup string
    """
    style_map = {
        "success": "bold #1f2937 on #4ade80",
        "error": "bold white on #f87171",
        "warning": "bold #1f2937 on #fbbf24",
        "info": "bold white on #60a5fa",
    }
    s = style_map.get(variant, style_map["info"])
    return f"[{s}] {text} [/]"


def create_section_header(title: str, style: str = "#5eead4") -> Text:
    """Create a section header with a subtle rule.

    Args:
        title: Section title
        style: Color

    Returns:
        Rich Text
    """
    t = Text()
    t.append(f"── {title} ", style=f"bold {style}")
    t.append("─" * 40, style="#374151")
    return t
