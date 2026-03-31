"""Pipeline I/O helpers.

File saving, TeX manipulation, metadata merging, and path generation utilities
used across the pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from vbagent.cli.common import format_latex, extract_problem_solution
from vbagent.tex import extract_items

if TYPE_CHECKING:
    from vbagent.models.pipeline import PipelineResult
    from vbagent.models.classification import (
        PrimaryClassification,
        DiagramAnalysis,
        DifficultyAssessment,
    )


def merge_metadata_into_latex(
    latex: str,
    primary: "PrimaryClassification",
    diagram: Optional["DiagramAnalysis"] = None,
    difficulty: Optional["DifficultyAssessment"] = None,
) -> str:
    """Prepend classification metadata as comments to LaTeX content."""
    comments = []

    comments.append(f"% subject: {primary.subject}")
    comments.append(f"% type: {primary.question_type}")
    comments.append(f"% has_diagram: {primary.has_diagram}")

    if difficulty:
        comments.append(f"% difficulty: {difficulty.difficulty}")

    if difficulty and difficulty.tags_auto:
        comments.append(f"% tags: {', '.join(difficulty.tags_auto)}")

    if diagram:
        comments.append("% has_diagram: true")
        comments.append(f"% diagram_type: {diagram.diagram_type}")
        if diagram.diagram_elements:
            comments.append(f"% diagram_elements: {', '.join(diagram.diagram_elements)}")
    elif primary.has_diagram:
        comments.append("% has_diagram: true")

    if difficulty:
        if difficulty.prerequisite_concepts:
            comments.append(f"% prerequisites: {', '.join(difficulty.prerequisite_concepts)}")
        if difficulty.cognitive_level:
            comments.append(f"% cognitive_level: {difficulty.cognitive_level}")
        comments.append(f"% estimated_time: {difficulty.expected_solve_time_minutes} min")

    metadata_block = "\n".join(comments)
    return f"{metadata_block}\n\n{latex}"


def convert_primary_to_classification(primary: "PrimaryClassification") -> "ClassificationResult":
    """Convert PrimaryClassification to ClassificationResult for compatibility."""
    from vbagent.models.classification import ClassificationResult

    return ClassificationResult(
        subject=primary.subject,
        question_type=primary.question_type,
        has_diagram=primary.has_diagram,
        confidence=primary.confidence,
        classified_from=primary.classified_from,
    )


def extract_items_from_tex(content: str) -> list[str]:
    """Extract individual items from a TeX file."""
    return extract_items(content)


def filter_items_by_range(
    items: list[str],
    item_range: Optional[tuple[int, int]],
) -> list[str]:
    """Filter items by the specified range (1-based, inclusive)."""
    if not item_range:
        return items
    start, end = item_range
    start_idx = max(0, start - 1)
    end_idx = min(len(items), end)
    return items[start_idx:end_idx]


def get_base_name(source_path: str) -> str:
    """Extract base name from source path (without extension)."""
    return Path(source_path).stem


def insert_tikz_into_latex(latex: str, tikz_code: str) -> str:
    """Replace diagram placeholders with actual TikZ code.

    Handles two types of placeholders:
    1. Main diagram: \\begin{center}\\input{diagram}\\end{center}
    2. MCQ option diagrams: \\def\\OptionA{...} through \\def\\OptionD{...}

    When tikz_code contains BOTH a main diagram and option defs
    (e.g. merged by ProblemOrchestrator), splits them and handles
    each independently.
    """
    if tikz_code is None:
        return latex

    # Split tikz_code into main diagram and option defs
    main_tikz, option_tikz = _split_main_and_options(tikz_code)

    result = latex

    # 1. Replace \input{diagram} with main diagram
    if main_tikz:
        placeholder_pattern = r'\\begin\{center\}\s*\\input\{diagram\}\s*\\end\{center\}'

        if "\\begin{center}" not in main_tikz:
            tikz_wrapped = f"\\begin{{center}}\n{main_tikz}\n\\end{{center}}"
        else:
            tikz_wrapped = main_tikz

        result = re.sub(placeholder_pattern, lambda m: tikz_wrapped, result)

        if result == latex:
            simple_pattern = r'\\input\{diagram\}'
            if re.search(simple_pattern, latex):
                result = re.sub(simple_pattern, lambda m: main_tikz, result)

    # 2. Insert option defs before \begin{tasks}
    if option_tikz:
        # Remove existing option defs in the LaTeX (will be replaced)
        for option in ["A", "B", "C", "D", "E", "F"]:
            pattern = rf'\\def\\Option{option}\{{[^{{}}]*(?:\{{[^{{}}]*\}}[^{{}}]*)*\}}'
            result = re.sub(pattern, "", result)

        # Remove OPTIONS_DIAGRAMS comment
        result = re.sub(r'%\s*OPTIONS_DIAGRAMS:.*?(?:\n|$)', '', result)

        # Insert option defs before \begin{tasks}
        tasks_pattern = r'(\s*\\begin\{tasks\})'

        def insert_before_tasks(match):
            return f"\n{option_tikz.strip()}\n{match.group(1)}"

        result = re.sub(tasks_pattern, insert_before_tasks, result)

    return result


def _split_main_and_options(tikz_code: str) -> tuple[str, str]:
    r"""Split combined tikz_code into (main_diagram, option_defs).

    Option defs are lines starting with ``\def\OptionX{`` through
    their matching closing brace. Everything else is the main diagram.
    """
    has_options = r'\def\Option' in tikz_code

    if not has_options:
        return tikz_code, ""

    # Find where option defs start — first \def\Option
    idx = tikz_code.find(r'\def\Option')
    if idx == -1:
        return tikz_code, ""

    main_part = tikz_code[:idx].strip()
    option_part = tikz_code[idx:].strip()

    return main_part, option_part


def generate_image_paths_from_range(
    image_path: str,
    item_range: tuple[int, int],
) -> list[str]:
    """Generate image paths from a template and range.

    Given an image path like 'images/Problem_3.png' and range (1, 5),
    generates paths: Problem_1.png, Problem_2.png, ..., Problem_5.png
    """
    from vbagent.cli.common import _get_console

    path = Path(image_path)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    match = re.search(r'([_\-]?)(\d+)$', stem)
    if not match:
        return [image_path]

    prefix = stem[: match.start()]
    separator = match.group(1)
    num_str = match.group(2)
    num_width = len(num_str)

    start, end = item_range
    paths = []
    for i in range(start, end + 1):
        new_num = str(i).zfill(num_width)
        new_stem = f"{prefix}{separator}{new_num}"
        new_path = parent / f"{new_stem}{suffix}"
        if new_path.exists():
            paths.append(str(new_path))
        else:
            _get_console().print(f"[yellow]Warning:[/yellow] Image not found: {new_path}")

    return paths


def generate_context_file(output_path: Path, problem_count: int) -> None:
    """Generate CONTEXT.md file for external AI agents."""
    from vbagent.templates.agentic_context import generate_context_file as _gen

    output_path.mkdir(parents=True, exist_ok=True)
    content = _gen(directory_name=output_path.name, problem_count=problem_count)
    context_file = output_path / "CONTEXT.md"
    context_file.write_text(content)


def save_pipeline_result_organized(
    result: "PipelineResult",
    base_dir: Path,
    base_name: str,
) -> dict[str, str]:
    """Save pipeline result to organized directory structure.

    Structure:
        agentic/
        ├── scans/{base_name}.tex
        ├── classifications/{base_name}.json
        ├── alternates/{base_name}.tex
        ├── variants/{type}/{base_name}.tex
        ├── ideas/{base_name}.json
        └── tikz/{base_name}.tex
    """
    saved_files = {}

    scans_dir = base_dir / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)

    # Build the scan content — append idea block and alternate inline
    scan_content = format_latex(result.latex)
    if result.idea_latex:
        from vbagent.agents.content_generation.idea import has_idea_environment
        if not has_idea_environment(scan_content):
            if not scan_content.endswith('\n'):
                scan_content += '\n'
            scan_content += '\n' + result.idea_latex.strip() + '\n'

    if result.alternate_solutions:
        for alt in result.alternate_solutions:
            alt_stripped = alt.strip()
            if alt_stripped and "\\begin{alternatesolution}" not in scan_content:
                if not scan_content.endswith('\n'):
                    scan_content += '\n'
                scan_content += '\n' + alt_stripped + '\n'

    latex_path = scans_dir / f"{base_name}.tex"
    latex_path.write_text(scan_content)
    saved_files["scan"] = str(latex_path)

    class_dir = base_dir / "classifications"
    class_dir.mkdir(parents=True, exist_ok=True)
    class_path = class_dir / f"{base_name}.json"
    class_path.write_text(result.classification.model_dump_json(indent=2))
    saved_files["classification"] = str(class_path)

    if result.tikz_code:
        tikz_dir = base_dir / "tikz"
        tikz_dir.mkdir(parents=True, exist_ok=True)
        tikz_path = tikz_dir / f"{base_name}.tex"
        tikz_path.write_text(format_latex(result.tikz_code))
        saved_files["tikz"] = str(tikz_path)

    if result.ideas:
        ideas_dir = base_dir / "ideas"
        ideas_dir.mkdir(parents=True, exist_ok=True)
        ideas_path = ideas_dir / f"{base_name}.json"
        ideas_path.write_text(result.ideas.model_dump_json(indent=2))
        saved_files["ideas"] = str(ideas_path)

    if result.alternate_solutions:
        alt_dir = base_dir / "alternates"
        alt_dir.mkdir(parents=True, exist_ok=True)
        alt_path = alt_dir / f"{base_name}.tex"
        formatted_alts = [format_latex(alt) for alt in result.alternate_solutions]
        combined = "\n\n% --- Alternate Solution ---\n\n".join(formatted_alts)
        alt_path.write_text(combined)
        saved_files["alternates"] = str(alt_path)

    for variant_type, variant_latex in result.variants.items():
        variant_dir = base_dir / "variants" / variant_type
        variant_dir.mkdir(parents=True, exist_ok=True)
        variant_path = variant_dir / f"{base_name}.tex"
        variant_path.write_text(format_latex(variant_latex))
        saved_files[f"variant_{variant_type}"] = str(variant_path)

    return saved_files


def save_pipeline_result(result: "PipelineResult", output_dir: Path) -> dict[str, str]:
    """Save pipeline result to output directory (legacy flat structure)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}

    class_path = output_dir / "classification.json"
    class_path.write_text(result.classification.model_dump_json(indent=2))
    saved_files["classification"] = str(class_path)

    latex_content = format_latex(result.latex)
    if result.idea_latex:
        from vbagent.agents.content_generation.idea import has_idea_environment
        if not has_idea_environment(latex_content):
            if not latex_content.endswith('\n'):
                latex_content += '\n'
            latex_content += '\n' + result.idea_latex.strip() + '\n'

    if result.alternate_solutions:
        for alt in result.alternate_solutions:
            alt_stripped = alt.strip()
            if alt_stripped and "\\begin{alternatesolution}" not in latex_content:
                if not latex_content.endswith('\n'):
                    latex_content += '\n'
                latex_content += '\n' + alt_stripped + '\n'

    latex_path = output_dir / "scanned.tex"
    latex_path.write_text(latex_content)
    saved_files["latex"] = str(latex_path)

    if result.tikz_code:
        tikz_path = output_dir / "diagram.tex"
        tikz_path.write_text(format_latex(result.tikz_code))
        saved_files["tikz"] = str(tikz_path)

    if result.ideas:
        ideas_path = output_dir / "ideas.json"
        ideas_path.write_text(result.ideas.model_dump_json(indent=2))
        saved_files["ideas"] = str(ideas_path)

    if result.alternate_solutions:
        alt_path = output_dir / "alternates.tex"
        formatted_alts = [format_latex(alt) for alt in result.alternate_solutions]
        combined = "\n\n% --- Alternate Solution ---\n\n".join(formatted_alts)
        alt_path.write_text(combined)
        saved_files["alternates"] = str(alt_path)

    for variant_type, variant_latex in result.variants.items():
        variant_path = output_dir / f"variant_{variant_type}.tex"
        variant_path.write_text(format_latex(variant_latex))
        saved_files[f"variant_{variant_type}"] = str(variant_path)

    result_path = output_dir / "pipeline_result.json"
    result_path.write_text(result.model_dump_json(indent=2))
    saved_files["full_result"] = str(result_path)

    return saved_files
