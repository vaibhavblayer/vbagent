"""LaTeX extraction and parsing utilities.

This module provides enhanced LaTeX extraction capabilities including:
- Subitem extraction (splitting \\item (a), \\item (b) patterns)
- Multi-file project parsing with recursive \\input{} resolution
- Circular reference detection
- Relative path resolution
- Directory filtering by subdirectory
"""

from vbagent.latex.extractor import (
    extract_subitems,
    parse_latex_project,
    extract_from_directory,
    CircularReferenceError,
)

__all__ = [
    "extract_subitems",
    "parse_latex_project",
    "extract_from_directory",
    "CircularReferenceError",
]
