"""Unified TeX parsing and extraction utilities.

Single source of truth for all TeX/LaTeX file parsing:
- File reading and section extraction
- Item extraction from \\item markers
- Answer extraction (MCQ \\ans, integer \\ansint)
- Multi-file project parsing with \\input{} resolution
- Subitem extraction (splitting multi-part questions)
- Directory-based file discovery

Previously split across three modules:
- vbagent/utils/tex_parser.py (basic parsing)
- vbagent/parsers/tex_parser.py (main.tex parsing, answer extraction from files)
- vbagent/latex/extractor.py (project parsing, subitems, directory extraction)
"""

import re
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CircularReferenceError(Exception):
    """Raised when circular \\input{} references are detected."""

    def __init__(self, cycle_path: list[str]):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join(cycle_path)
        super().__init__(f"Circular reference detected: {cycle_str}")


# ---------------------------------------------------------------------------
# Basic file reading
# ---------------------------------------------------------------------------

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

    Expects \\item for the problem and
    \\begin{solution}...\\end{solution} for the solution.

    Args:
        tex_path: Path to the TeX file

    Returns:
        Tuple of (problem, solution)
    """
    content = Path(tex_path).read_text()

    problem_match = re.search(
        r'\\item\s*(.*?)(?=\\begin\{solution\})',
        content,
        re.DOTALL,
    )
    problem = problem_match.group(1).strip() if problem_match else content

    solution_match = re.search(
        r'\\begin\{solution\}(.*?)\\end\{solution\}',
        content,
        re.DOTALL,
    )
    solution = solution_match.group(1).strip() if solution_match else ""

    return problem, solution


# ---------------------------------------------------------------------------
# Item extraction
# ---------------------------------------------------------------------------

def extract_items(content: str) -> list[str]:
    """Extract all top-level \\item blocks from content.

    Splits content by \\item markers, skipping markers inside
    nested itemize/enumerate environments.

    Args:
        content: TeX content containing \\item markers

    Returns:
        List of item strings (each starting with \\item)
    """
    lines = content.split('\n')
    items: list[str] = []
    current_item: list[str] = []
    depth = 0
    in_item = False

    for line in lines:
        stripped = line.strip()

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

        if depth == 0 and re.match(r'\s*\\item\b', line):
            if in_item and current_item:
                items.append('\n'.join(current_item).strip())
            current_item = [line]
            in_item = True
        elif in_item:
            current_item.append(line)

    if in_item and current_item:
        items.append('\n'.join(current_item).strip())

    return items


def extract_subitems(tex_content: str) -> list[str]:
    """Extract individual subitems from LaTeX content.

    Splits patterns like::

        \\item (a) First part
        \\item (b) Second part

    into separate items, preserving content for each subitem.

    Args:
        tex_content: LaTeX content containing subitems

    Returns:
        List of subitem contents.  If no subitems found, returns
        the original content as a single-item list.
    """
    pattern = r'\\item\s*\(([a-z]|[ivxlcdm]+)\)'
    matches = list(re.finditer(pattern, tex_content, re.IGNORECASE))

    if not matches:
        return [tex_content]

    subitems: list[str] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(tex_content)
        subitem = tex_content[start:end].strip()
        subitem = re.sub(r'^\\item\s*', '', subitem)
        subitems.append(subitem)

    return subitems


# ---------------------------------------------------------------------------
# Answer extraction
# ---------------------------------------------------------------------------

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

    # Integer answer takes priority
    ansint_match = re.search(r'\\ansint\{([^}]+)\}', content)
    if ansint_match:
        return ansint_match.group(1).strip()

    # MCQ answer in tasks environment
    tasks_match = re.search(r'\\begin\{tasks\}.*?\\end\{tasks\}', content, re.DOTALL)
    if tasks_match:
        tasks_content = tasks_match.group(0)

        task_positions = [(m.start(), 'task') for m in re.finditer(r'\\task\b', tasks_content)]
        ans_positions = [(m.start(), 'ans') for m in re.finditer(r'\\ans\b', tasks_content)]

        if not ans_positions:
            return None

        all_markers = sorted(task_positions + ans_positions, key=lambda x: x[0])

        correct_options: list[str] = []
        task_count = 0

        for i, (pos, marker_type) in enumerate(all_markers):
            if marker_type == 'task':
                task_count += 1
                if i + 1 < len(all_markers) and all_markers[i + 1][1] == 'ans':
                    correct_options.append(chr(65 + task_count - 1))

        if correct_options:
            return ','.join(correct_options)

    return None


def extract_answer_from_problem(problem_file: Path) -> Optional[str]:
    """Extract answer from a problem .tex file.

    Convenience wrapper: reads the file then calls :func:`extract_answer`.

    Args:
        problem_file: Path to problem .tex file

    Returns:
        Answer string or None if not found
    """
    if not problem_file.exists():
        return None
    content = problem_file.read_text(encoding="utf-8")
    return extract_answer(content)


# ---------------------------------------------------------------------------
# main.tex project parsing (foreach loops, recursive input resolution)
# ---------------------------------------------------------------------------

def parse_main_tex(main_tex_path: Path) -> list[Path]:
    """Parse main.tex and extract all problem file paths.

    Handles:
    - ``\\foreach \\i in {1,...,10}`` range patterns
    - ``\\foreach \\i in {1, 3, 5, 7}`` list patterns
    - Direct ``\\input{problem_11.tex}`` statements
    - Nested folders like ``physics/problem_\\i.tex``
    - Recursive ``\\input{physics/main_physics}`` that contains loops

    Args:
        main_tex_path: Path to main.tex file

    Returns:
        List of resolved problem file paths
    """
    return _parse_tex_recursive(main_tex_path, main_tex_path.parent, set())


def _parse_tex_recursive(
    tex_path: Path, base_dir: Path, visited: set[Path]
) -> list[Path]:
    """Recursively parse tex files to find all problem files."""
    if tex_path in visited or not tex_path.exists():
        return []

    visited.add(tex_path)
    content = tex_path.read_text(encoding="utf-8")
    current_dir = tex_path.parent
    problem_files: list[Path] = []

    # Remove comments
    lines = [line.split('%')[0] for line in content.split('\n')]
    content = '\n'.join(lines)

    # Pattern 1: \foreach \i in {1,...,10}
    foreach_range = re.finditer(
        r'\\foreach\s+\\i\s+in\s*\{(\d+),\s*\.\.\.,\s*(\d+)\}.*?\\input\{([^}]+)\}',
        content, re.DOTALL,
    )
    for match in foreach_range:
        start, end, pattern = int(match.group(1)), int(match.group(2)), match.group(3)
        for i in range(start, end + 1):
            file_path = pattern.replace(r'\i', str(i))
            resolved = _resolve_path(file_path, current_dir, base_dir)
            problem_files.append(resolved)

    # Pattern 2: \foreach \i in {1, 3, 5, 7}
    foreach_list = re.finditer(
        r'\\foreach\s+\\i\s+in\s*\{([^}]+)\}.*?\\input\{([^}]+)\}',
        content, re.DOTALL,
    )
    for match in foreach_list:
        numbers_str, pattern = match.group(1), match.group(2)
        if '...' in numbers_str:
            continue
        numbers = [int(n.strip()) for n in numbers_str.split(',')]
        for i in numbers:
            file_path = pattern.replace(r'\i', str(i))
            resolved = _resolve_path(file_path, current_dir, base_dir)
            problem_files.append(resolved)

    # Pattern 3: Direct \input{...} statements
    direct_inputs = re.finditer(r'\\input\{([^}]+)\}', content)
    for match in direct_inputs:
        file_path = match.group(1)
        if r'\i' in file_path:
            continue
        if not file_path.endswith('.tex'):
            file_path += '.tex'
        file_lower = file_path.lower()
        if any(x in file_lower for x in ['answer', 'ans_', 'solution']):
            continue

        full_path = _resolve_path(file_path, current_dir, base_dir)

        if full_path.exists():
            file_content = full_path.read_text(encoding="utf-8")
            if r'\item' in file_content:
                problem_files.append(full_path)
            else:
                problem_files.extend(_parse_tex_recursive(full_path, base_dir, visited))
        else:
            problem_files.append(full_path)

    # Deduplicate preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in problem_files:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    return unique


def _resolve_path(file_path: str, current_dir: Path, base_dir: Path) -> Path:
    """Resolve file path, trying current directory then base directory."""
    path1 = current_dir / file_path
    if path1.exists():
        return path1
    path2 = base_dir / file_path
    if path2.exists():
        return path2
    return path1


# ---------------------------------------------------------------------------
# Multi-file project parsing (\\input / \\include with circular detection)
# ---------------------------------------------------------------------------

def parse_latex_project(main_tex: Path, max_depth: int = 10) -> dict[str, str]:
    """Parse multi-file LaTeX project with recursive \\input{} resolution.

    Follows \\input{} and \\include{} references recursively, resolving
    relative paths and detecting circular references.

    Args:
        main_tex: Path to the main .tex file
        max_depth: Maximum recursion depth

    Returns:
        Dictionary mapping absolute file paths to their content.

    Raises:
        FileNotFoundError: If main_tex or a referenced file doesn't exist
        CircularReferenceError: If circular references are detected
        ValueError: If max_depth is exceeded
    """
    if not main_tex.exists():
        raise FileNotFoundError(f"Main TeX file not found: {main_tex}")

    visited: dict[str, str] = {}
    visiting_stack: list[str] = []

    def _parse_file(tex_path: Path, depth: int = 0) -> None:
        if depth > max_depth:
            raise ValueError(
                f"Maximum recursion depth ({max_depth}) exceeded. "
                f"Possible circular reference or very deep nesting."
            )

        abs_path = tex_path.resolve()
        path_str = str(abs_path)

        if path_str in visiting_stack:
            cycle = visiting_stack[visiting_stack.index(path_str):] + [path_str]
            raise CircularReferenceError(cycle)

        if path_str in visited:
            return

        visiting_stack.append(path_str)
        try:
            if not tex_path.exists():
                raise FileNotFoundError(f"Referenced file not found: {tex_path}")

            content = tex_path.read_text(encoding='utf-8', errors='ignore')
            visited[path_str] = content

            input_pattern = r'\\(?:input|include)\{([^}]+)\}'
            for match in re.finditer(input_pattern, content):
                input_file = match.group(1).strip()
                input_path = _resolve_input_path(tex_path.parent, input_file)
                _parse_file(input_path, depth + 1)
        finally:
            visiting_stack.pop()

    _parse_file(main_tex)
    return visited


def _resolve_input_path(base_dir: Path, input_file: str) -> Path:
    """Resolve \\input{} path relative to base directory."""
    input_file = input_file.strip('\'"')

    input_path = base_dir / input_file
    if input_path.exists():
        return input_path

    if not input_file.endswith('.tex'):
        input_path_with_ext = base_dir / f"{input_file}.tex"
        if input_path_with_ext.exists():
            return input_path_with_ext

    raise FileNotFoundError(
        f"Could not resolve input file: {input_file}\n"
        f"Tried: {input_path} and {input_path}.tex"
    )


# ---------------------------------------------------------------------------
# Directory extraction
# ---------------------------------------------------------------------------

def extract_from_directory(
    directory: Path,
    subdirectory: Optional[str] = None,
    recursive: bool = True,
    pattern: str = "*.tex",
) -> list[Path]:
    """Extract LaTeX files from a directory with optional filtering.

    Args:
        directory: Root directory to search
        subdirectory: Optional subdirectory filter (e.g. "scans", "variants")
        recursive: Whether to search subdirectories recursively
        pattern: Glob pattern for matching files (default: "*.tex")

    Returns:
        Sorted list of Path objects for matching files

    Raises:
        FileNotFoundError: If directory doesn't exist
        ValueError: If directory is not a directory
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    if subdirectory:
        search_path = directory / subdirectory
        if not search_path.exists():
            return []
        if not search_path.is_dir():
            raise ValueError(f"Not a directory: {search_path}")
    else:
        search_path = directory

    if recursive:
        files = list(search_path.rglob(pattern))
    else:
        files = list(search_path.glob(pattern))

    files.sort()
    return files

# ---------------------------------------------------------------------------
# LaTeX formatting — add line breaks for readability
# ---------------------------------------------------------------------------

def format_tex(tex: str) -> str:
    """Add line breaks and indentation to LaTeX for readable .tex files.

    Handles:
    - Line break before \\begin{...} and \\end{...}
    - Line break before \\item
    - Indentation inside environments
    - Preserves tikzpicture/verbatim blocks as-is
    - Auto-wraps bare tikzpicture in \\begin{center} (except MCQ options)
    """
    import re as _re

    # Don't touch empty strings
    if not tex or not tex.strip():
        return tex

    # Step 0: Wrap bare \begin{tikzpicture} in \begin{center} if not already
    tex = _center_wrap_tikz(tex)

    # Step 1: Insert newlines before structural commands (if not already there)
    # Before \begin{...} (but not inside tikzpicture)
    tex = _re.sub(r'(?<!\n)\s*(\\begin\{(?!tikzpicture|circuitikz))', r'\n\1', tex)
    # Before \end{...}
    tex = _re.sub(r'(?<!\n)\s*(\\end\{(?!tikzpicture|circuitikz))', r'\n\1', tex)
    # Before \item
    tex = _re.sub(r'(?<!\n)\s*(\\item\b)', r'\n\1', tex)

    # Step 2: Split into lines and apply indentation
    lines = tex.split('\n')
    formatted: list[str] = []
    indent = 0
    in_tikz = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue

        # Track tikzpicture blocks — don't re-indent them
        if _re.match(r'\\begin\{(tikzpicture|circuitikz)', stripped):
            in_tikz = True
        if in_tikz:
            formatted.append(line)  # preserve original indentation
            if _re.match(r'\\end\{(tikzpicture|circuitikz)', stripped):
                in_tikz = False
            continue

        # Decrease indent before \end
        if stripped.startswith('\\end{'):
            indent = max(0, indent - 1)

        formatted.append('    ' * indent + stripped)

        # Increase indent after \begin (but not \begin{document})
        if _re.match(r'\\begin\{(?!document)', stripped):
            indent += 1

    return '\n'.join(formatted)


def _center_wrap_tikz(tex: str) -> str:
    r"""Wrap bare \begin{tikzpicture} blocks in \begin{center}.

    Skips blocks that are already inside \begin{center} or inside
    \def\Option (MCQ option diagrams).
    """
    import re as _re

    def _is_inside_def(text: str, pos: int) -> bool:
        """Check if position is inside a \\def\\Option{...} block."""
        # Look backwards for \def\Option that hasn't been closed
        before = text[:pos]
        last_def = before.rfind("\\def\\Option")
        if last_def == -1:
            return False
        # Check if there's an unmatched { between def and pos
        snippet = before[last_def:]
        depth = 0
        for ch in snippet:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        return depth > 0

    result = tex
    # Find all \begin{tikzpicture} ... \end{tikzpicture} blocks
    pattern = _re.compile(
        r'(\\begin\{(?:tikzpicture|circuitikz)\}.*?\\end\{(?:tikzpicture|circuitikz)\})',
        _re.DOTALL,
    )

    offset = 0
    for m in pattern.finditer(tex):
        start = m.start() + offset
        end = m.end() + offset

        # Check if already wrapped in \begin{center}
        before = result[max(0, start - 50):start].strip()
        if before.endswith("\\begin{center}"):
            continue

        # Check if inside \def\Option (MCQ option diagram)
        if _is_inside_def(result, start):
            continue

        # Wrap in center
        replacement = "\\begin{center}\n" + m.group(1) + "\n\\end{center}"
        result = result[:start] + replacement + result[end:]
        offset += len(replacement) - len(m.group(1))

    return result
