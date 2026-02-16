"""Shared utility functions for VBAgent.

This module consolidates duplicate utility functions that were previously
scattered across the codebase. It provides:

- LaTeX cleaning, validation, and formatting utilities
- TeX file parsing and section extraction
- Result formatting for CLI display

The utils module is organized into submodules:
- latex: LaTeX cleaning, validation, formatting
- tex_parser: TeX file parsing, section extraction
- formatting: CLI result formatting
"""

# Lazy imports to avoid circular dependencies and improve import performance
__all__ = [
    # LaTeX utilities (from latex.py)
    "clean_latex_output",
    "validate_latex_syntax",
    "format_latex_for_display",
    "extract_preamble",
    # TeX parser utilities (from tex_parser.py)
    "parse_tex_file",
    "parse_tex_file_with_sections",
    "extract_items",
    "extract_answer",
    # Formatting utilities (from formatting.py)
    "format_result_table",
    "format_diff",
    "format_stats",
]


def __getattr__(name: str):
    """Lazy load utility functions on first access."""
    if name in __all__:
        # Import the appropriate submodule based on the function name
        if name in ["clean_latex_output", "validate_latex_syntax", 
                    "format_latex_for_display", "extract_preamble"]:
            from . import latex
            return getattr(latex, name)
        elif name in ["parse_tex_file", "parse_tex_file_with_sections",
                      "extract_items", "extract_answer"]:
            from . import tex_parser
            return getattr(tex_parser, name)
        elif name in ["format_result_table", "format_diff", "format_stats"]:
            from . import formatting
            return getattr(formatting, name)
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
