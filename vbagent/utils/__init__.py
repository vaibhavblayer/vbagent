"""Shared utility functions for VBAgent.

Provides:
- LaTeX cleaning, validation, and formatting utilities
- Result formatting for CLI display

TeX parsing lives in vbagent.tex (canonical location).
"""

__all__ = [
    # LaTeX utilities (from latex.py)
    "clean_latex_output",
    "validate_latex_syntax",
    "format_latex_for_display",
    "extract_preamble",
    # Formatting utilities (from formatting.py)
    "format_result_table",
    "format_diff",
    "format_stats",
]


def __getattr__(name: str):
    """Lazy load utility functions on first access."""
    if name in ("clean_latex_output", "validate_latex_syntax",
                "format_latex_for_display", "extract_preamble"):
        from . import latex
        return getattr(latex, name)
    elif name in ("format_result_table", "format_diff", "format_stats"):
        from . import formatting
        return getattr(formatting, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
