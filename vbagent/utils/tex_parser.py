"""TeX file parsing utilities."""

import re
from pathlib import Path
from typing import Optional


def parse_tex_file(tex_path: str) -> str:
    """Read and return TeX file content.
    
    Args:
        tex_path: Path to the TeX file
        
    Returns:
        Content of the TeX file
    """
    return Path(tex_path).read_text()


def parse_tex_file_with_sections(tex_path: str) -> tuple[str, str]:
    """Parse TeX file and extract problem/solution sections.
    
    Expects the file to contain \\item for the problem and
    \\begin{solution}...\\end{solution} for the solution.
    
    Args:
        tex_path: Path to the TeX file
        
    Returns:
        Tuple of (problem, solution)
    """
    content = Path(tex_path).read_text()
    
    # Extract problem (everything from \item to \begin{solution})
    problem_match = re.search(
        r'\\item\s*(.*?)(?=\\begin\{solution\})',
        content,
        re.DOTALL
    )
    problem = problem_match.group(1).strip() if problem_match else content
    
    # Extract solution
    solution_match = re.search(
        r'\\begin\{solution\}(.*?)\\end\{solution\}',
        content,
        re.DOTALL
    )
    solution = solution_match.group(1).strip() if solution_match else ""
    
    return problem, solution


def extract_items(content: str) -> list[str]:
    """Extract all top-level \\item blocks from content.

    Splits content by \\item markers to get individual problems,
    skipping \\item markers inside nested environments like itemize/enumerate.

    Args:
        content: TeX content containing \\item markers

    Returns:
        List of item strings (each starting with \\item)
    """
    # Track nesting depth of itemize/enumerate environments
    lines = content.split('\n')
    items = []
    current_item = []
    depth = 0
    in_item = False

    for line in lines:
        stripped = line.strip()

        # Check for environment boundaries (before processing \item)
        if re.search(r'\\begin\{(itemize|enumerate)\}', stripped):
            depth += 1
            if in_item:
                current_item.append(line)
            continue

        if re.search(r'\\end\{(itemize|enumerate)\}', stripped):
            depth -= 1
            if in_item:
                current_item.append(line)
            continue

        # Only treat \item as a top-level split point when depth == 0
        if depth == 0 and re.match(r'\s*\\item\b', line):
            if in_item and current_item:
                items.append('\n'.join(current_item).strip())
            current_item = [line]
            in_item = True
        elif in_item:
            current_item.append(line)

    # Don't forget the last item
    if in_item and current_item:
        items.append('\n'.join(current_item).strip())

    return items


def extract_answer(content: str) -> Optional[str]:
    """Extract answer from problem content.
    
    Handles:
    - MCQ: \\ans marker in tasks environment (returns A, B, C, D, etc.)
    - Integer: \\ansint{value} command
    - Multiple correct: Returns comma-separated (A,C)
    
    Args:
        content: TeX content containing answer markers
        
    Returns:
        Answer string or None if not found
    """
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
