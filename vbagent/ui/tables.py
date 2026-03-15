"""Simple table components."""

from typing import Optional, Literal, Any, Dict
from rich.table import Table
from rich import box

from vbagent.ui.styles import TABLE_STYLES, CATEGORY_COLORS

TableStyle = Literal["simple", "minimal", "markdown"]


def create_table(
    title: Optional[str] = None,
    style: TableStyle = "simple",
    show_header: bool = True,
    show_lines: bool = False,
    expand: bool = False,
    caption: Optional[str] = None,
) -> Table:
    """Create a simple table with clean appearance.

    Args:
        title: Optional table title
        style: Table style preset (simple, minimal, markdown)
        show_header: Whether to show header row
        show_lines: Whether to show lines between rows
        expand: Whether to expand to full width
        caption: Optional caption below the table

    Returns:
        Configured Rich Table instance
    """
    cfg = TABLE_STYLES[style]

    return Table(
        title=title,
        title_style=cfg.get("title_style", ""),
        caption=caption,
        caption_style=cfg.get("caption_style", "dim"),
        border_style=cfg["border_style"],
        header_style=cfg["header_style"],
        row_styles=cfg["row_styles"],
        box=cfg["box"],
        show_header=show_header,
        show_lines=show_lines,
        expand=expand,
        padding=cfg.get("padding", (0, 1)),
    )


def create_result_table(
    title: str,
    data: Dict[str, Any],
    style: TableStyle = "simple",
) -> Table:
    """Create a key-value result table.

    Args:
        title: Table title
        data: Dictionary of key-value pairs
        style: Table style preset

    Returns:
        Populated table
    """
    table = create_table(title=title, style=style)
    table.add_column("Property", style="bold #5eead4", no_wrap=True, min_width=14)
    table.add_column("Value", style="#e5e7eb")

    for key, value in data.items():
        display = _format_value(value)
        table.add_row(key, display)

    return table


def create_category_table(
    title: str,
    columns: list[str],
    style: TableStyle = "simple",
    caption: Optional[str] = None,
) -> Table:
    """Create a table designed for category-grouped rows.

    Adds columns with sensible defaults for agent config / status displays.

    Args:
        title: Table title
        columns: List of column header names
        style: Table style preset
        caption: Optional caption

    Returns:
        Table with columns added (no rows yet)
    """
    table = create_table(title=title, style=style, caption=caption)

    for i, col in enumerate(columns):
        col_style = ""
        if i == 0:
            col_style = "bold #a78bfa"  # category
        elif i == 1:
            col_style = "#5eead4"       # name
        elif i == 2:
            col_style = "#4ade80"       # model / primary value
        else:
            col_style = "#e5e7eb"

        table.add_column(col, style=col_style, no_wrap=(i < 2))

    return table


def add_category_row(
    table: Table,
    category: str,
    values: list[str],
    is_header: bool = False,
) -> None:
    """Add a row with category coloring.

    Args:
        table: Target table
        category: Category key (e.g. 'classification')
        values: Row values (excluding category column)
        is_header: Whether this is a category header row
    """
    color = CATEGORY_COLORS.get(category, "#e5e7eb")
    cat_label = f"[{color}]{category.replace('_', ' ').title()}[/]"

    if is_header:
        cat_label = f"[bold {color}]{category.replace('_', ' ').title()}[/]"

    table.add_row(cat_label, *values)


# ── helpers ──────────────────────────────────────────────────────────

def _format_value(value: Any) -> str:
    """Format a value for display in a table cell."""
    if value is None:
        return "[#6b7280]–[/]"
    if isinstance(value, bool):
        return "[#4ade80]yes[/]" if value else "[#f87171]no[/]"
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, list):
        if not value:
            return "[#6b7280]–[/]"
        return ", ".join(str(v) for v in value[:8]) + ("…" if len(value) > 8 else "")
    if isinstance(value, dict):
        if not value:
            return "[#6b7280]–[/]"
        items = [f"{k}={v}" for k, v in list(value.items())[:4]]
        return ", ".join(items) + ("…" if len(value) > 4 else "")
    return str(value)
