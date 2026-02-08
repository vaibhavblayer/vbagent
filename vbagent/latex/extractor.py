"""Enhanced LaTeX extraction functions.

This module provides functions for extracting and parsing LaTeX content:
- extract_subitems: Split multi-part questions into individual subitems
- parse_latex_project: Parse multi-file LaTeX projects with \\input{} resolution
- extract_from_directory: Extract LaTeX files from directories with filtering
"""

import re
from pathlib import Path
from typing import Optional


class CircularReferenceError(Exception):
    """Raised when circular \\input{} references are detected."""
    
    def __init__(self, cycle_path: list[str]):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join(cycle_path)
        super().__init__(f"Circular reference detected: {cycle_str}")


def extract_subitems(tex_content: str) -> list[str]:
    """Extract individual subitems from LaTeX content.
    
    Splits patterns like:
        \\item (a) First part
        \\item (b) Second part
        \\item (c) Third part
    
    into separate items, preserving all content for each subitem.
    
    Args:
        tex_content: LaTeX content containing subitems
        
    Returns:
        List of individual subitem contents. If no subitems are found,
        returns the original content as a single-item list.
        
    Examples:
        >>> content = "\\\\item (a) First\\n\\\\item (b) Second"
        >>> extract_subitems(content)
        ['(a) First', '(b) Second']
    """
    # Pattern to match \item (a), \item (b), etc.
    # Matches: \item followed by optional whitespace, then (letter) or (roman numeral)
    pattern = r'\\item\s*\(([a-z]|[ivxlcdm]+)\)'
    
    # Find all matches with their positions
    matches = list(re.finditer(pattern, tex_content, re.IGNORECASE))
    
    if not matches:
        # No subitems found, return original content
        return [tex_content]
    
    subitems = []
    for i, match in enumerate(matches):
        # Get the start position of this subitem
        start = match.start()
        
        # Get the end position (start of next subitem or end of content)
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(tex_content)
        
        # Extract the subitem content
        subitem_content = tex_content[start:end].strip()
        
        # Remove the \item prefix but keep the (a), (b), etc.
        subitem_content = re.sub(r'^\\item\s*', '', subitem_content)
        
        subitems.append(subitem_content)
    
    return subitems


def parse_latex_project(
    main_tex: Path,
    max_depth: int = 10
) -> dict[str, str]:
    """Parse multi-file LaTeX project with recursive \\input{} resolution.
    
    Follows \\input{} and \\include{} references recursively, resolving
    relative paths and detecting circular references.
    
    Args:
        main_tex: Path to the main .tex file
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Dictionary mapping file paths (as strings) to their content.
        The main file is included with key str(main_tex).
        
    Raises:
        FileNotFoundError: If main_tex or any referenced file doesn't exist
        CircularReferenceError: If circular references are detected
        ValueError: If max_depth is exceeded
        
    Examples:
        >>> result = parse_latex_project(Path("main.tex"))
        >>> print(result.keys())
        dict_keys(['main.tex', 'chapter1.tex', 'chapter2.tex'])
    """
    if not main_tex.exists():
        raise FileNotFoundError(f"Main TeX file not found: {main_tex}")
    
    # Track visited files to detect circular references
    visited: dict[str, str] = {}  # path -> content
    visiting_stack: list[str] = []  # Current path being processed
    
    def _parse_file(tex_path: Path, depth: int = 0) -> None:
        """Recursively parse a TeX file and its inputs."""
        if depth > max_depth:
            raise ValueError(
                f"Maximum recursion depth ({max_depth}) exceeded. "
                f"Possible circular reference or very deep nesting."
            )
        
        # Convert to absolute path for consistent tracking
        abs_path = tex_path.resolve()
        path_str = str(abs_path)
        
        # Check for circular reference (currently being processed)
        if path_str in visiting_stack:
            cycle = visiting_stack[visiting_stack.index(path_str):] + [path_str]
            raise CircularReferenceError(cycle)
        
        # Check if already visited (already processed)
        if path_str in visited:
            return
        
        # Mark as currently visiting
        visiting_stack.append(path_str)
        
        try:
            # Read file content
            if not tex_path.exists():
                raise FileNotFoundError(f"Referenced file not found: {tex_path}")
            
            content = tex_path.read_text(encoding='utf-8', errors='ignore')
            visited[path_str] = content
            
            # Find all \input{} and \include{} commands
            # Pattern matches: \input{file}, \input{file.tex}, \include{file}
            input_pattern = r'\\(?:input|include)\{([^}]+)\}'
            
            for match in re.finditer(input_pattern, content):
                input_file = match.group(1).strip()
                
                # Resolve relative path
                input_path = _resolve_input_path(tex_path.parent, input_file)
                
                # Recursively parse the input file
                _parse_file(input_path, depth + 1)
        
        finally:
            # Remove from visiting stack
            visiting_stack.pop()
    
    # Start parsing from main file
    _parse_file(main_tex)
    
    return visited


def _resolve_input_path(base_dir: Path, input_file: str) -> Path:
    """Resolve \\input{} path relative to base directory.
    
    Handles:
    - Relative paths (./file.tex, ../file.tex)
    - Paths without .tex extension (adds it automatically)
    - Absolute paths (though not recommended in LaTeX)
    
    Args:
        base_dir: Directory containing the file with \\input{} command
        input_file: The file path from \\input{file}
        
    Returns:
        Resolved absolute Path object
        
    Raises:
        FileNotFoundError: If the resolved path doesn't exist
    """
    # Remove any quotes or whitespace
    input_file = input_file.strip('\'"')
    
    # Try with original name first
    input_path = base_dir / input_file
    if input_path.exists():
        return input_path
    
    # Try adding .tex extension if not present
    if not input_file.endswith('.tex'):
        input_path_with_ext = base_dir / f"{input_file}.tex"
        if input_path_with_ext.exists():
            return input_path_with_ext
    
    # If neither exists, raise error with helpful message
    raise FileNotFoundError(
        f"Could not resolve input file: {input_file}\n"
        f"Tried: {input_path} and {input_path}.tex"
    )


def extract_from_directory(
    directory: Path,
    subdirectory: Optional[str] = None,
    recursive: bool = True,
    pattern: str = "*.tex"
) -> list[Path]:
    """Extract LaTeX files from a directory with optional filtering.
    
    Args:
        directory: Root directory to search
        subdirectory: Optional subdirectory filter (e.g., "scans", "variants")
                     If specified, only files in this subdirectory are returned
        recursive: Whether to search subdirectories recursively
        pattern: Glob pattern for matching files (default: "*.tex")
        
    Returns:
        List of Path objects for matching .tex files
        
    Raises:
        FileNotFoundError: If directory doesn't exist
        ValueError: If directory is not a directory
        
    Examples:
        >>> # Get all .tex files
        >>> files = extract_from_directory(Path("questions"))
        
        >>> # Get only files in scans/ subdirectory
        >>> scans = extract_from_directory(Path("questions"), subdirectory="scans")
        
        >>> # Get files non-recursively
        >>> files = extract_from_directory(Path("questions"), recursive=False)
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # Determine search path
    if subdirectory:
        search_path = directory / subdirectory
        if not search_path.exists():
            # Return empty list if subdirectory doesn't exist
            return []
        if not search_path.is_dir():
            raise ValueError(f"Not a directory: {search_path}")
    else:
        search_path = directory
    
    # Collect matching files
    if recursive:
        # Use rglob for recursive search
        files = list(search_path.rglob(pattern))
    else:
        # Use glob for non-recursive search
        files = list(search_path.glob(pattern))
    
    # Sort for consistent ordering
    files.sort()
    
    return files
