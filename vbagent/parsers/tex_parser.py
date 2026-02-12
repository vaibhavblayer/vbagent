"""LaTeX file parsing utilities for extracting problem files and answers."""

import re
from pathlib import Path
from typing import Optional


def parse_main_tex(main_tex_path: Path) -> list[Path]:
    """Parse main.tex and extract all problem file paths.
    
    Handles:
    - \\foreach \\i in {1,...,10} patterns
    - \\foreach \\i in {1, 3, 5, 7} patterns
    - Direct \\input{problem_11.tex} statements
    - Nested folders like physics/problem_\\i.tex
    - Recursive \\input{physics/main_physics} that contains loops
    
    Args:
        main_tex_path: Path to main.tex file
        
    Returns:
        List of resolved problem file paths
    """
    return _parse_tex_recursive(main_tex_path, main_tex_path.parent, set())


def _parse_tex_recursive(tex_path: Path, base_dir: Path, visited: set[Path]) -> list[Path]:
    """Recursively parse tex files to find all problem files."""
    if tex_path in visited or not tex_path.exists():
        return []
    
    visited.add(tex_path)
    content = tex_path.read_text(encoding="utf-8")
    current_dir = tex_path.parent
    problem_files = []
    
    # Remove comments
    lines = [line.split('%')[0] for line in content.split('\n')]
    content = '\n'.join(lines)
    
    # Pattern 1: \foreach \i in {1,...,10}
    foreach_range = re.finditer(
        r'\\foreach\s+\\i\s+in\s*\{(\d+),\s*\.\.\.,\s*(\d+)\}.*?\\input\{([^}]+)\}',
        content, re.DOTALL
    )
    for match in foreach_range:
        start, end, pattern = int(match.group(1)), int(match.group(2)), match.group(3)
        for i in range(start, end + 1):
            file_path = pattern.replace(r'\i', str(i))
            # Try both current_dir and base_dir
            resolved = _resolve_path(file_path, current_dir, base_dir)
            problem_files.append(resolved)
    
    # Pattern 2: \foreach \i in {1, 3, 5, 7}
    foreach_list = re.finditer(
        r'\\foreach\s+\\i\s+in\s*\{([^}]+)\}.*?\\input\{([^}]+)\}',
        content, re.DOTALL
    )
    for match in foreach_list:
        numbers_str, pattern = match.group(1), match.group(2)
        # Skip if it's a range pattern (already handled)
        if '...' in numbers_str:
            continue
        numbers = [int(n.strip()) for n in numbers_str.split(',')]
        for i in numbers:
            file_path = pattern.replace(r'\i', str(i))
            # Try both current_dir and base_dir
            resolved = _resolve_path(file_path, current_dir, base_dir)
            problem_files.append(resolved)
    
    # Pattern 3: All \input{...} statements
    direct_inputs = re.finditer(r'\\input\{([^}]+)\}', content)
    for match in direct_inputs:
        file_path = match.group(1)
        # Skip if it contains \i (already handled by foreach)
        if r'\i' in file_path:
            continue
        
        # Add .tex if missing
        if not file_path.endswith('.tex'):
            file_path += '.tex'
        
        # Skip answer-related files
        file_lower = file_path.lower()
        if any(x in file_lower for x in ['answer', 'ans_', 'solution']):
            continue
        
        # Try both current_dir and base_dir
        full_path = _resolve_path(file_path, current_dir, base_dir)
        
        # Check if it's a problem file or another main file
        if full_path.exists():
            file_content = full_path.read_text(encoding="utf-8")
            # If it contains \item, it's a problem file
            if r'\item' in file_content:
                problem_files.append(full_path)
            # Otherwise, recursively parse it
            else:
                problem_files.extend(_parse_tex_recursive(full_path, base_dir, visited))
        else:
            # File doesn't exist, assume it's a problem file
            problem_files.append(full_path)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in problem_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    
    return unique_files


def _resolve_path(file_path: str, current_dir: Path, base_dir: Path) -> Path:
    """Resolve file path, trying both current directory and base directory."""
    # Try relative to current directory first
    path1 = current_dir / file_path
    if path1.exists():
        return path1
    
    # Try relative to base directory
    path2 = base_dir / file_path
    if path2.exists():
        return path2
    
    # Default to current directory if neither exists
    return path1


def extract_answer_from_problem(problem_file: Path) -> Optional[str]:
    """Extract answer from a problem file.
    
    Handles:
    - MCQ: \\ans marker in tasks environment (returns A, B, C, D, etc.)
    - Integer: \\ansint{value} command
    - Multiple correct: Returns comma-separated (A,C)
    
    Args:
        problem_file: Path to problem .tex file
        
    Returns:
        Answer string or None if not found
    """
    if not problem_file.exists():
        return None
    
    content = problem_file.read_text(encoding="utf-8")
    
    # Remove comments
    lines = [line.split('%')[0] for line in content.split('\n')]
    content = '\n'.join(lines)
    
    # Check for integer answer first
    ansint_match = re.search(r'\\ansint\{([^}]+)\}', content)
    if ansint_match:
        return ansint_match.group(1).strip()
    
    # Check for MCQ answer in tasks environment
    tasks_match = re.search(r'\\begin\{tasks\}.*?\\end\{tasks\}', content, re.DOTALL)
    if tasks_match:
        tasks_content = tasks_match.group(0)
        
        # Find all \task and \ans positions
        task_positions = [(m.start(), 'task') for m in re.finditer(r'\\task\b', tasks_content)]
        ans_positions = [(m.start(), 'ans') for m in re.finditer(r'\\ans\b', tasks_content)]
        
        if not ans_positions:
            return None
        
        # Combine and sort by position
        all_markers = sorted(task_positions + ans_positions, key=lambda x: x[0])
        
        # Find which tasks have \ans
        correct_options = []
        task_count = 0
        
        for i, (pos, marker_type) in enumerate(all_markers):
            if marker_type == 'task':
                task_count += 1
                # Check if next marker is \ans
                if i + 1 < len(all_markers) and all_markers[i + 1][1] == 'ans':
                    # Convert to letter (0->A, 1->B, etc.)
                    correct_options.append(chr(65 + task_count - 1))
        
        if correct_options:
            return ','.join(correct_options)
    
    return None
