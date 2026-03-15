"""Consistent styling for Rich components.

Defines the VBAgent visual language: colors, table presets, and theme.
"""

from rich.theme import Theme
from rich import box

# Color palette - modern, muted tones
COLORS = {
    "primary": "#5eead4",      # Teal
    "secondary": "#a78bfa",    # Violet
    "success": "#4ade80",      # Green
    "warning": "#fbbf24",      # Amber
    "error": "#f87171",        # Red
    "info": "#60a5fa",         # Blue
    "muted": "#6b7280",        # Gray-500
    "header": "#e5e7eb",       # Gray-200
    "accent": "#f472b6",       # Pink
    "surface": "#1f2937",      # Gray-800 (dark bg)
}

# Table styles - simplified with thin borders
TABLE_STYLES = {
    "simple": {
        "border_style": "#6b7280",
        "header_style": "bold #5eead4",
        "row_styles": ["", ""],
        "box": box.SIMPLE,
        "title_style": "bold #5eead4",
        "caption_style": "dim",
        "padding": (0, 1),
    },
    "minimal": {
        "border_style": "#4b5563",
        "header_style": "bold #5eead4",
        "row_styles": ["", ""],
        "box": box.SIMPLE_HEAD,
        "title_style": "bold",
        "caption_style": "dim",
        "padding": (0, 1),
    },
    "markdown": {
        "border_style": "#6b7280",
        "header_style": "bold #5eead4",
        "row_styles": ["", ""],
        "box": box.MARKDOWN,
        "title_style": "bold #5eead4",
        "caption_style": "dim",
        "padding": (0, 1),
    },
}

# Status indicators
STATUS = {
    "success": "[#4ade80]✓[/]",
    "error": "[#f87171]✗[/]",
    "warning": "[#fbbf24]⚠[/]",
    "info": "[#60a5fa]ℹ[/]",
    "pending": "[#6b7280]○[/]",
    "running": "[#5eead4]◉[/]",
    "skip": "[#6b7280]–[/]",
}

# Semantic labels for agent categories
CATEGORY_COLORS = {
    "classification": "#a78bfa",   # Violet
    "content_generation": "#5eead4",  # Teal
    "diagram": "#60a5fa",          # Blue
    "variants": "#fbbf24",         # Amber
    "quality": "#4ade80",          # Green
    "metadata": "#f472b6",         # Pink
    "orchestration": "#fb923c",    # Orange
    "selection": "#c084fc",        # Purple
    "global": "#e5e7eb",           # Gray
}

# Default theme
VBAGENT_THEME = Theme({
    "info": "#60a5fa",
    "warning": "#fbbf24",
    "error": "bold #f87171",
    "success": "bold #4ade80",
    "agent": "bold #a78bfa",
    "model": "bold #5eead4",
    "path": "italic #60a5fa",
    "muted": "#6b7280",
    "key": "bold #5eead4",
    "value": "#e5e7eb",
    "header": "bold #e5e7eb",
    "category": "bold #a78bfa",
    "duration": "italic #6b7280",
    "badge.success": "bold #1f2937 on #4ade80",
    "badge.error": "bold white on #f87171",
    "badge.warning": "bold #1f2937 on #fbbf24",
    "badge.info": "bold white on #60a5fa",
})
