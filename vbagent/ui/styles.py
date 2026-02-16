"""Consistent styling for Rich components."""

from rich.theme import Theme

# Color palette
COLORS = {
    "primary": "#00d4ff",      # Cyan
    "success": "#00ff88",      # Green
    "warning": "#ffaa00",      # Orange
    "error": "#ff4444",        # Red
    "info": "#8888ff",         # Blue
    "muted": "#888888",        # Gray
    "header": "#ffffff",       # White
}

# Table styles
TABLE_STYLES = {
    "modern": {
        "border_style": "bright_cyan",
        "header_style": "bold white on bright_cyan",
        "row_styles": ["", "dim"],
        "box": "HEAVY_HEAD",  # Thick header border
    },
    "minimal": {
        "border_style": "dim",
        "header_style": "bold cyan",
        "row_styles": ["", ""],
        "box": "SIMPLE_HEAD",
    },
    "clean": {
        "border_style": "bright_white",
        "header_style": "bold white on blue",
        "row_styles": ["", "on grey11"],
        "box": "DOUBLE_EDGE",  # Double line for outer border
    }
}

# Default theme
VBAGENT_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "agent": "bold magenta",
    "model": "bold blue",
    "path": "italic cyan",
})
