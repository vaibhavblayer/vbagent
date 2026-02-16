"""LaTeX utility functions.

This module provides utilities for cleaning, validating, and formatting LaTeX content.
Extracted from duplicate implementations across the codebase.
"""

import re
from typing import Optional


def clean_latex_output(latex: str) -> str:
    """Clean LaTeX output by removing markdown code blocks.
    
    Handles:
    - ```latex ... ```
    - ```tex ... ```
    - ``` ... ```
    - Leading/trailing whitespace
    
    Args:
        latex: Raw LaTeX output from LLM
        
    Returns:
        Cleaned LaTeX without markdown artifacts
        
    Examples:
        >>> clean_latex_output("```latex\\n\\\\begin{document}\\n```")
        '\\\\begin{document}'
        >>> clean_latex_output("  \\\\section{Title}  ")
        '\\\\section{Title}'
    """
    if not latex:
        return latex
    
    # Remove markdown code block markers with language specifier
    # Matches: ```latex, ```tex, ```LaTeX, etc.
    latex = re.sub(r'^```(?:latex|tex|LaTeX)?\s*\n?', '', latex, flags=re.IGNORECASE)
    
    # Remove closing code block marker
    latex = re.sub(r'\n?```\s*$', '', latex)
    
    # Also handle case where ``` appears at the start without newline
    latex = re.sub(r'^```\s*', '', latex)
    
    return latex.strip()


def validate_latex_syntax(latex: str) -> tuple[bool, list[str]]:
    """Basic LaTeX syntax validation.
    
    Performs simple validation checks:
    - Matching braces: { }
    - Matching brackets: [ ]
    - Matching begin/end environments
    - Basic command structure
    
    Note: This is not a complete LaTeX parser. For full validation,
    use a LaTeX compiler.
    
    Args:
        latex: LaTeX content to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
        
    Examples:
        >>> validate_latex_syntax("\\\\begin{document}\\\\end{document}")
        (True, [])
        >>> validate_latex_syntax("\\\\begin{document}")
        (False, ['Unmatched environment: document'])
    """
    if not latex:
        return True, []
    
    errors = []
    
    # Check matching braces
    brace_count = 0
    for i, char in enumerate(latex):
        if char == '{' and (i == 0 or latex[i-1] != '\\'):
            brace_count += 1
        elif char == '}' and (i == 0 or latex[i-1] != '\\'):
            brace_count -= 1
            if brace_count < 0:
                errors.append(f"Unmatched closing brace at position {i}")
                break
    
    if brace_count > 0:
        errors.append(f"Unmatched opening braces: {brace_count} unclosed")
    
    # Check matching brackets
    bracket_count = 0
    for i, char in enumerate(latex):
        if char == '[' and (i == 0 or latex[i-1] != '\\'):
            bracket_count += 1
        elif char == ']' and (i == 0 or latex[i-1] != '\\'):
            bracket_count -= 1
            if bracket_count < 0:
                errors.append(f"Unmatched closing bracket at position {i}")
                break
    
    if bracket_count > 0:
        errors.append(f"Unmatched opening brackets: {bracket_count} unclosed")
    
    # Check matching begin/end environments
    begin_pattern = r'\\begin\{([^}]+)\}'
    end_pattern = r'\\end\{([^}]+)\}'
    
    begins = re.findall(begin_pattern, latex)
    ends = re.findall(end_pattern, latex)
    
    # Track environment stack
    env_stack = []
    all_commands = []
    
    # Find all begin/end commands with their positions
    for match in re.finditer(begin_pattern, latex):
        all_commands.append(('begin', match.group(1), match.start()))
    for match in re.finditer(end_pattern, latex):
        all_commands.append(('end', match.group(1), match.start()))
    
    # Sort by position
    all_commands.sort(key=lambda x: x[2])
    
    # Check matching
    for cmd_type, env_name, pos in all_commands:
        if cmd_type == 'begin':
            env_stack.append(env_name)
        elif cmd_type == 'end':
            if not env_stack:
                errors.append(f"Unmatched \\end{{{env_name}}} at position {pos}")
            elif env_stack[-1] != env_name:
                errors.append(
                    f"Mismatched environment: expected \\end{{{env_stack[-1]}}} "
                    f"but found \\end{{{env_name}}} at position {pos}"
                )
                env_stack.pop()
            else:
                env_stack.pop()
    
    # Check for unclosed environments
    for env_name in env_stack:
        errors.append(f"Unmatched environment: {env_name}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def format_latex_for_display(latex: str, max_lines: int = 10) -> str:
    """Format LaTeX for terminal display.
    
    Truncates long LaTeX content for display in terminal/CLI output.
    Useful for showing previews without overwhelming the terminal.
    
    Args:
        latex: LaTeX content to format
        max_lines: Maximum number of lines to display (default: 10)
        
    Returns:
        Formatted LaTeX suitable for terminal display
        
    Examples:
        >>> content = "\\n".join([f"Line {i}" for i in range(20)])
        >>> result = format_latex_for_display(content, max_lines=5)
        >>> "..." in result
        True
    """
    if not latex:
        return latex
    
    lines = latex.split('\n')
    
    if len(lines) <= max_lines:
        return latex
    
    # Show first max_lines-1 lines and add ellipsis
    displayed_lines = lines[:max_lines-1]
    remaining = len(lines) - (max_lines - 1)
    
    displayed_lines.append(f"... ({remaining} more lines)")
    
    return '\n'.join(displayed_lines)


def extract_preamble(latex: str) -> str:
    """Extract preamble from complete LaTeX document.
    
    Extracts everything before \\begin{document} from a complete LaTeX document.
    This includes documentclass, usepackage commands, and custom definitions.
    
    Args:
        latex: Complete LaTeX document
        
    Returns:
        Preamble content (empty string if no preamble found)
        
    Examples:
        >>> doc = "\\\\documentclass{article}\\n\\\\begin{document}\\nContent\\n\\\\end{document}"
        >>> extract_preamble(doc)
        '\\\\documentclass{article}'
    """
    if not latex:
        return ""
    
    # Find the position of \begin{document}
    match = re.search(r'\\begin\{document\}', latex)
    
    if not match:
        # No \begin{document} found, return empty string
        return ""
    
    # Extract everything before \begin{document}
    preamble = latex[:match.start()].strip()
    
    return preamble
