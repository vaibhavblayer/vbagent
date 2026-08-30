"""Pipeline I/O helpers.

File saving, TeX manipulation, metadata merging, and path generation utilities
used across the pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from vbagent.cli.common import format_latex, extract_problem_solution
from vbagent.cli.item_selection import OPEN_ENDED_ITEM
from vbagent.tex import extract_items


_OPTION_ARTIFACT_MARKER = "% VBAGENT_OPTION_DIAGRAMS_BEGIN"
_OPTION_DEF_START_RE = re.compile(r"\\def\s*\\Option([A-Z])\s*\{")
_MATCH_ARTIFACT_MARKER = "% VBAGENT_MATCH_DIAGRAMS_BEGIN"
_MATCH_DEF_START_RE = re.compile(r"\\def\s*\\Match([A-Z])\s*\{")
_CENTERED_MAIN_DIAGRAM_RE = re.compile(
    r"\\begin\{center\}\s*%?\s*\\input\{diagram\}\s*\\end\{center\}"
)
_MAIN_DIAGRAM_INPUT_RE = re.compile(r"\\input\{diagram\}")
_COMMENTED_MAIN_DIAGRAM_INPUT_RE = re.compile(
    r"^[ \t]*%[ \t]*\\input\{diagram\}[ \t]*$",
    flags=re.MULTILINE,
)
_LEGACY_DIAGRAM_TEXT = r"\\text\s*\{\s*\[\s*diagram\s*\]\s*\}"
_CENTERED_LEGACY_DIAGRAM_RE = re.compile(
    rf"\\begin\{{center\}}\s*(?:{_LEGACY_DIAGRAM_TEXT}|\[\s*diagram\s*\])"
    r"\s*\\end\{center\}",
    flags=re.IGNORECASE,
)
_LEGACY_DIAGRAM_TEXT_RE = re.compile(_LEGACY_DIAGRAM_TEXT, flags=re.IGNORECASE)

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

    if diagram and primary.has_diagram:
        comments.append("% has_diagram: true")
        comments.append(f"% diagram_type: {diagram.diagram_type}")
        if diagram.diagram_elements:
            comments.append(f"% diagram_elements: {', '.join(diagram.diagram_elements)}")
    elif primary.has_diagram:
        comments.append("% has_diagram: true")

    if diagram and diagram.has_option_diagrams:
        comments.append("% has_option_diagrams: true")
        comments.append(f"% num_option_diagrams: {diagram.num_option_diagrams}")
        if diagram.option_diagram_type:
            comments.append(f"% option_diagram_type: {diagram.option_diagram_type}")

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


def _assembled_latex_for_save(result: "PipelineResult") -> str:
    """Return normalized LaTeX with any available TikZ deterministically merged."""
    latex = result.latex
    if result.tikz_code and has_tikz_placeholder(latex):
        latex = insert_tikz_into_latex(latex, result.tikz_code)
    return format_latex(latex)


def has_main_diagram_placeholder(latex: Optional[str]) -> bool:
    r"""Return whether LaTeX contains a current or legacy main placeholder."""
    if not latex:
        return False
    return bool(
        _MAIN_DIAGRAM_INPUT_RE.search(latex)
        or _CENTERED_LEGACY_DIAGRAM_RE.search(latex)
        or _LEGACY_DIAGRAM_TEXT_RE.search(latex)
    )


def has_tikz_placeholder(latex: Optional[str]) -> bool:
    r"""Return whether LaTeX contains a main, option, or match-cell placeholder."""
    if not latex:
        return False
    return bool(
        has_main_diagram_placeholder(latex)
        or re.search(r"\\(?:Option|Match)[A-Z]\b", latex)
    )


def replace_main_diagram_placeholder(latex: str, replacement: str) -> str:
    r"""Replace current and legacy main-diagram placeholders consistently."""
    if replacement and r"\begin{center}" not in replacement:
        centered_replacement = (
            f"\\begin{{center}}\n{replacement}\n\\end{{center}}"
        )
    else:
        centered_replacement = replacement

    result = _CENTERED_MAIN_DIAGRAM_RE.sub(
        lambda _: centered_replacement,
        latex,
    )
    result = _CENTERED_LEGACY_DIAGRAM_RE.sub(
        lambda _: centered_replacement,
        result,
    )
    result = _COMMENTED_MAIN_DIAGRAM_INPUT_RE.sub(
        lambda _: replacement,
        result,
    )
    result = _MAIN_DIAGRAM_INPUT_RE.sub(lambda _: replacement, result)
    return _LEGACY_DIAGRAM_TEXT_RE.sub(lambda _: replacement, result)


def insert_tikz_into_latex(latex: str, tikz_code: str) -> str:
    """Replace diagram placeholders with actual TikZ code.

    Handles three diagram roles:
    1. Main diagram: \\begin{center}\\input{diagram}\\end{center}
    2. Matching-table cells: \\def\\MatchA{...} consumed by \\MatchA
    3. MCQ option diagrams: \\def\\OptionA{...} through \\def\\OptionD{...}

    When tikz_code contains BOTH a main diagram and option defs
    (e.g. merged by ProblemOrchestrator), splits them and handles
    each independently.
    """
    if tikz_code is None:
        return latex

    # Split tikz_code into standalone, matching-table, and option artifacts.
    main_tikz, option_tikz = _split_main_and_options(tikz_code)
    main_tikz, match_tikz = _split_main_and_match(main_tikz)

    result = latex

    # 1. Replace current or legacy main-diagram placeholder.
    if main_tikz:
        result = replace_main_diagram_placeholder(result, main_tikz)

    # 2. Insert matching-table definitions before the table that consumes them.
    if match_tikz and re.search(r"\\Match[A-Z]\b", result):
        result = _remove_match_definitions(result)

        match_support = _clean_definition_support(
            _remove_match_definitions(match_tikz)
        )
        if match_support:
            result = result.replace(match_support, "", 1)

        result = re.sub(r'%\s*MATCH_DIAGRAMS:.*?(?:\n|$)', '', result)
        table_pattern = r'(\s*\\begin\{(?:tabular|tabularx|tabular\*)\})'

        def insert_before_table(match):
            return f"\n{match_tikz.strip()}\n{match.group(1)}"

        result = re.sub(table_pattern, insert_before_table, result, count=1)

    # 3. Insert option defs before \begin{tasks}
    if option_tikz:
        # Remove existing option defs in the LaTeX (will be replaced). This
        # uses balanced-brace parsing because TikZ definitions are nested much
        # more deeply than a regular expression can safely match.
        result = _remove_option_definitions(result)

        # Option generators occasionally emit a shared top-level macro before
        # the definitions. Remove the exact previous support block as well so
        # save-time reassembly cannot duplicate it.
        option_support = _clean_definition_support(
            _remove_option_definitions(option_tikz)
        )
        if option_support:
            result = result.replace(option_support, "", 1)

        # Remove OPTIONS_DIAGRAMS comment
        result = re.sub(r'%\s*OPTIONS_DIAGRAMS:.*?(?:\n|$)', '', result)

        # Insert option defs before \begin{tasks}
        tasks_pattern = r'(\s*\\begin\{tasks\})'

        def insert_before_tasks(match):
            return f"\n{option_tikz.strip()}\n{match.group(1)}"

        result = re.sub(tasks_pattern, insert_before_tasks, result, count=1)

    return result


def _split_main_and_options(tikz_code: str) -> tuple[str, str]:
    r"""Split combined tikz_code into (main_diagram, option_defs).

    Option defs are lines starting with ``\def\OptionX{`` through
    their matching closing brace. An explicit artifact marker separates a
    genuine main diagram from option support code.
    """
    if _OPTION_ARTIFACT_MARKER in tikz_code:
        main_part, option_part = tikz_code.split(_OPTION_ARTIFACT_MARKER, 1)
        return main_part.strip(), _normalize_option_artifact(option_part)

    spans = _option_definition_spans(tikz_code)
    if not spans:
        return tikz_code, ""

    prefix = tikz_code[:spans[0][1]].strip()
    # Legacy combined artifacts had no boundary marker. A standalone
    # tikzpicture before the first option definition is the main diagram;
    # otherwise the prefix is option support code (for example a shared macro).
    if r"\begin{tikzpicture}" in prefix:
        main_part = prefix
        option_source = tikz_code[spans[0][1]:]
    else:
        main_part = ""
        option_source = tikz_code

    return main_part, _normalize_option_artifact(option_source)


def _split_main_and_match(tikz_code: str) -> tuple[str, str]:
    r"""Split a standalone diagram from ``\def\MatchX`` definitions."""
    if _MATCH_ARTIFACT_MARKER in tikz_code:
        main_part, match_part = tikz_code.split(_MATCH_ARTIFACT_MARKER, 1)
        return main_part.strip(), _normalize_match_artifact(match_part)

    spans = _match_definition_spans(tikz_code)
    if not spans:
        return tikz_code, ""

    prefix = tikz_code[:spans[0][1]].strip()
    if r"\begin{tikzpicture}" in prefix:
        main_part = prefix
        match_source = tikz_code[spans[0][1]:]
    else:
        main_part = ""
        match_source = tikz_code

    return main_part, _normalize_match_artifact(match_source)


def split_tikz_artifacts(tikz_code: Optional[str]) -> tuple[str, str]:
    """Return normalized main and option portions of a TikZ artifact."""
    if not tikz_code:
        return "", ""
    return _split_main_and_options(tikz_code)


def has_standalone_main_tikz(tikz_code: Optional[str]) -> bool:
    """Return whether an artifact contains a non-table standalone diagram."""
    main_tikz, _ = split_tikz_artifacts(tikz_code)
    standalone_tikz, _ = _split_main_and_match(main_tikz)
    return bool(standalone_tikz.strip())


def combine_tikz_artifacts(
    main_tikz: Optional[str],
    option_tikz: Optional[str],
) -> Optional[str]:
    """Combine independently generated main and option artifacts safely."""
    main_source = (main_tikz or "").strip()
    embedded_options = ""
    if main_source and (r"\def\Option" in main_source
                        or _OPTION_ARTIFACT_MARKER in main_source):
        main_source, embedded_options = _split_main_and_options(main_source)

    main = main_source.strip()
    # A dedicated option agent is authoritative. Embedded option definitions
    # from a main agent are retained only as a fallback.
    options = (option_tikz or embedded_options or "").strip()
    if not options:
        return main or None
    if not main:
        return f"{_OPTION_ARTIFACT_MARKER}\n{options}"
    return f"{main}\n\n{_OPTION_ARTIFACT_MARKER}\n{options}"


def remove_main_diagram_placeholder(latex: str) -> str:
    """Remove a scanner placeholder when classification says options-only."""
    return replace_main_diagram_placeholder(latex, "")


def _is_escaped(text: str, index: int) -> bool:
    """Return whether the character at index is escaped by a backslash."""
    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _balanced_group_end(text: str, opening_brace: int) -> Optional[int]:
    """Find the exclusive end of a TeX group, skipping comments/escaped braces."""
    depth = 0
    index = opening_brace
    while index < len(text):
        char = text[index]
        if char == "%" and not _is_escaped(text, index):
            newline = text.find("\n", index)
            if newline == -1:
                return None
            index = newline + 1
            continue
        if char == "{" and not _is_escaped(text, index):
            depth += 1
        elif char == "}" and not _is_escaped(text, index):
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def _option_definition_spans(text: str) -> list[tuple[str, int, int]]:
    """Return ``(letter, start, end)`` spans for balanced option definitions."""
    return _definition_spans(text, _OPTION_DEF_START_RE)


def _match_definition_spans(text: str) -> list[tuple[str, int, int]]:
    """Return ``(letter, start, end)`` spans for matching-table definitions."""
    return _definition_spans(text, _MATCH_DEF_START_RE)


def _definition_spans(
    text: str,
    start_pattern: re.Pattern[str],
) -> list[tuple[str, int, int]]:
    """Return balanced macro-definition spans found by ``start_pattern``."""
    spans: list[tuple[str, int, int]] = []
    position = 0
    while match := start_pattern.search(text, position):
        end = _balanced_group_end(text, match.end() - 1)
        if end is None:
            position = match.end()
            continue
        spans.append((match.group(1), match.start(), end))
        position = end
    return spans


def _remove_option_definitions(text: str) -> str:
    """Remove every complete ``\\def\\OptionX{...}`` block from text."""
    return _remove_definition_spans(text, _option_definition_spans(text))


def _remove_match_definitions(text: str) -> str:
    """Remove every complete ``\\def\\MatchX{...}`` block from text."""
    return _remove_definition_spans(text, _match_definition_spans(text))


def _remove_definition_spans(
    text: str,
    spans: list[tuple[str, int, int]],
) -> str:
    """Remove the supplied balanced definition spans from text."""
    if not spans:
        return text
    pieces = []
    position = 0
    for _, start, end in spans:
        pieces.append(text[position:start])
        position = end
    pieces.append(text[position:])
    return "".join(pieces)


def _normalize_option_artifact(option_tikz: str) -> str:
    """Keep one definition per option, preferring the last generated set."""
    spans = _option_definition_spans(option_tikz)
    if not spans:
        return option_tikz.strip()

    latest: dict[str, str] = {}
    for letter, start, end in spans:
        latest[letter] = option_tikz[start:end].strip()

    support = _clean_definition_support(_remove_option_definitions(option_tikz))
    definitions = [latest[letter] for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                   if letter in latest]
    parts = ([support] if support else []) + definitions
    return "\n".join(parts)


def _normalize_match_artifact(match_tikz: str) -> str:
    """Keep one definition per matching row, preferring the last set."""
    spans = _match_definition_spans(match_tikz)
    if not spans:
        return match_tikz.strip()

    latest: dict[str, str] = {}
    for letter, start, end in spans:
        latest[letter] = match_tikz[start:end].strip()

    support = _clean_definition_support(_remove_match_definitions(match_tikz))
    definitions = [latest[letter] for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                   if letter in latest]
    parts = ([support] if support else []) + definitions
    return "\n".join(parts)


def _clean_definition_support(text: str) -> str:
    """Discard wrapper noise while retaining shared definition-level commands."""
    ignored = {
        "%", "```", "```latex",
        _OPTION_ARTIFACT_MARKER, _MATCH_ARTIFACT_MARKER,
    }
    lines = [line for line in text.splitlines() if line.strip() not in ignored]
    return "\n".join(lines).strip()


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
    if end == OPEN_ENDED_ITEM:
        numbered_stem = re.compile(rf"^{re.escape(prefix + separator)}(\d+)$")
        numbered_paths: list[tuple[int, str, Path]] = []
        for candidate in parent.iterdir():
            if candidate.suffix != suffix:
                continue
            candidate_match = numbered_stem.fullmatch(candidate.stem)
            if candidate_match:
                candidate_number = candidate_match.group(1)
                number = int(candidate_number)
                if (
                    number >= start
                    and candidate_number == str(number).zfill(num_width)
                ):
                    numbered_paths.append((number, candidate.name.casefold(), candidate))
        return [str(candidate) for _, _, candidate in sorted(numbered_paths)]

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
    scan_content = _assembled_latex_for_save(result)
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

    latex_content = _assembled_latex_for_save(result)
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
