"""Modern table components."""

from typing import Optional, Literal, Any, Dict
from rich.table import Table
from rich.box import HEAVY_HEAD, DOUBLE_EDGE, SIMPLE_HEAD

from vbagent.ui.styles import TABLE_STYLES

TableStyle = Literal["modern", "minimal", "clean"]


def create_table(
    title: Optional[str] = None,
    style: TableStyle = "modern",
    show_header: bool = True,
    show_lines: bool = False,
    expand: bool = False,
) -> Table:
    """Create a styled table with modern appearance.
    
    Args:
        title: Optional table title
        style: Table style preset (modern, minimal, clean)
        show_header: Whether to show header row
        show_lines: Whether to show lines between rows
        expand: Whether to expand to full width
        
    Returns:
        Configured Rich Table instance
    """
    style_config = TABLE_STYLES[style]
    
    # Map box style names to Rich box objects
    box_map = {
        "HEAVY_HEAD": HEAVY_HEAD,
        "SIMPLE_HEAD": SIMPLE_HEAD,
        "DOUBLE_EDGE": DOUBLE_EDGE,
    }
    
    return Table(
        title=title,
        border_style=style_config["border_style"],
        header_style=style_config["header_style"],
        row_styles=style_config["row_styles"],
        box=box_map[style_config["box"]],
        show_header=show_header,
        show_lines=show_lines,
        expand=expand,
        padding=(0, 1),  # Vertical, horizontal padding
    )


def create_result_table(
    title: str,
    data: Dict[str, Any],
    style: TableStyle = "modern"
) -> Table:
    """Create a table for displaying results.
    
    Args:
        title: Table title
        data: Dictionary of key-value pairs
        style: Table style preset
        
    Returns:
        Populated table
    """
    table = create_table(title=title, style=style)
    table.add_column("Property", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    for key, value in data.items():
        table.add_row(key, str(value))
    
    return table
