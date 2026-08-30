"""Generate solutions from already-scanned TeX projects."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import click

from vbagent.cli.common import (
    _get_console,
    configure_cli_verbosity,
    find_image_for_problem,
)
from vbagent.cli.item_selection import item_selection_options, resolve_item_range
from vbagent.tex import extract_items


QUESTION_TYPES = [
    "mcq_sc",
    "mcq_mc",
    "subjective",
    "integer",
    "assertion_reason",
    "passage",
    "match",
]
SUBJECTS = ["physics", "chemistry", "mathematics", "biology"]


def _natural_tex_file_sort_key(path: Path) -> tuple[tuple[int, object], ...]:
    """Sort TeX filenames naturally so numeric problem IDs stay numeric."""
    parts = re.split(r"(\d+)", path.name.casefold())
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part)
        for part in parts
        if part
    )


def sort_tex_files(files: Iterable[Path]) -> list[Path]:
    """Return TeX files in human/numeric filename order."""
    return sorted(files, key=_natural_tex_file_sort_key)


def _folder_units(files: list[Path]) -> list[tuple[int, Path]]:
    """Use trailing problem IDs when every folder file has a unique one."""
    numbered: list[tuple[int, Path]] = []
    for path in files:
        match = re.search(r"(\d+)(?!.*\d)", path.stem)
        if not match:
            return list(enumerate(files, 1))
        numbered.append((int(match.group(1)), path))
    if len({number for number, _ in numbered}) != len(numbered):
        return list(enumerate(files, 1))
    return numbered


def _select_folder_units(
    units: list[tuple[int, Path]],
    from_index: int | None,
    to_index: int | None,
    excluded: set[int],
) -> list[int]:
    """Select folder files by their problem-number suffix."""
    start = 1 if from_index is None else from_index
    end = max((number for number, _ in units), default=0) if to_index is None else to_index
    return [
        number
        for number, _ in units
        if start <= number <= end and number not in excluded
    ]


def _load_classification_metadata(source_path: Path) -> dict:
    """Load the organized classification sidecar for a scanned problem."""
    candidates = [
        source_path.parent.parent / "classifications" / f"{source_path.stem}.json",
        source_path.parent / "classifications" / f"{source_path.stem}.json",
        Path(".vbagent") / "metadata" / f"{source_path.stem}.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            metadata = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        nested = metadata.get("classification")
        if isinstance(nested, dict):
            return {**metadata, **nested}
        return metadata
    return {}


def parse_excluded_indices(values: Iterable[str]) -> set[int]:
    """Parse comma- or whitespace-separated 1-based item numbers."""
    excluded: set[int] = set()
    for value in values:
        for token in re.split(r"[\s,]+", value.strip()):
            if not token:
                continue
            try:
                item_number = int(token)
            except ValueError as exc:
                raise click.BadParameter(
                    f"Invalid item number in --exclude: {token!r}"
                ) from exc
            if item_number < 1:
                raise click.BadParameter(
                    "--exclude item numbers must be positive (1-based)"
                )
            excluded.add(item_number)
    return excluded


def select_item_indices(
    total: int,
    from_index: int | None = None,
    to_index: int | None = None,
    excluded: set[int] | None = None,
) -> list[int]:
    """Return selected 1-based item indices from an inclusive range."""
    start = 1 if from_index is None else from_index
    end = total if to_index is None else to_index
    if start < 1 or end < 1:
        raise click.BadParameter("--from and --to must be positive (1-based)")
    if start > end:
        raise click.BadParameter("--from must be <= --to")
    excluded = excluded or set()
    return [
        index
        for index in range(start, min(end, total) + 1)
        if index not in excluded
    ]


def _item_spans(content: str) -> list[tuple[int, int, str]]:
    """Locate extracted top-level items without changing project formatting."""
    items = extract_items(content)
    if not items:
        return [(0, len(content), content)] if content.strip() else []

    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for item in items:
        start = content.find(item, cursor)
        if start < 0:
            raise ValueError(
                "Could not map an extracted TeX item back to its source project"
            )
        end = start + len(item)
        spans.append((start, end, item))
        cursor = end
    return spans


def has_solution_environment(content: str) -> bool:
    """Return whether content contains a complete solution environment."""
    return bool(
        re.search(
            r"\\begin\{solution\}.*?\\end\{solution\}",
            content,
            flags=re.DOTALL,
        )
    )


def _replace_items(
    content: str,
    spans: list[tuple[int, int, str]],
    replacements: dict[int, str],
) -> str:
    """Replace selected items from right to left, preserving all other text."""
    result = content
    for item_number in sorted(replacements, reverse=True):
        start, end, _ = spans[item_number - 1]
        result = result[:start] + replacements[item_number] + result[end:]
    return result


def _metadata_value(content: str, key: str) -> str | None:
    match = re.search(rf"(?mi)^%\s*{re.escape(key)}\s*:\s*([^\s]+)", content)
    return match.group(1).strip().lower() if match else None


def _cache_problem_id(
    source_path: Path,
    item_number: int,
    item: str,
    subject: str,
    question_type: str,
    no_diagram: bool,
) -> str:
    """Build a safe cache key that changes when input or diagram mode changes."""
    payload = "\x1f".join(
        [
            str(source_path.resolve()),
            str(item_number),
            hashlib.sha256(item.encode("utf-8")).hexdigest(),
            subject,
            question_type,
            "no-diagram" if no_diagram else "diagrams",
        ]
    )
    return "solve_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _resolve_output_path(input_path: Path, output: str | None) -> Path:
    if output:
        output_path = Path(output)
        if output_path.suffix.lower() == ".tex":
            return output_path
        return output_path / f"{input_path.stem}-solutions.tex"
    return Path("agentic") / "solutions" / f"{input_path.stem}-solutions.tex"


def _resolve_folder_output_path(input_path: Path, output: str | None) -> Path:
    """Resolve the output directory for folder mode."""
    if output:
        output_path = Path(output)
        if output_path.suffix.lower() == ".tex":
            raise click.BadParameter(
                "Folder input requires --output to be a directory, not a .tex file"
            )
        return output_path
    return Path("agentic") / "solutions" / input_path.name


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-t",
    "--tex",
    "input_path",
    required=False,
    default=None,
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    help=(
        "Scanned TeX project, or folder containing one problem per .tex file "
        "(default: agentic/scans, updated in place)"
    ),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output .tex file for file input, or output directory for folder input",
)
@click.option("--subject", type=click.Choice(SUBJECTS), default=None, help="Subject override")
@click.option(
    "--type",
    "question_type",
    type=click.Choice(QUESTION_TYPES),
    default=None,
    help="Question type override (otherwise uses TeX metadata or subjective)",
)
@click.option("--chapter", default=None, help="Optional chapter for solution prompt routing")
@click.option("--topic", default=None, help="Optional topic for solution prompt routing")
@item_selection_options
@click.option(
    "--exclude",
    multiple=True,
    help="Items to skip (comma-separated, repeatable; e.g. --exclude 5,7,8)",
)
@click.option("--no-diagram", is_flag=True, help="Skip solution diagram agents")
@click.option(
    "--in-place",
    is_flag=True,
    help="Write successful solutions back into the input file(s)",
)
@click.option("--no-cache", is_flag=True, help="Regenerate solutions without using the pipeline cache")
@click.option(
    "-v/-q",
    "--verbose/--quiet",
    "verbose",
    default=True,
    callback=configure_cli_verbosity,
    help="Show agent telemetry [default: verbose]",
)
def solve(
    input_path: Path | None,
    output: Path | None,
    subject: str | None,
    question_type: str | None,
    chapter: str | None,
    topic: str | None,
    from_index: int | None,
    to_index: int | None,
    item: int | None,
    exclude: tuple[str, ...],
    no_diagram: bool,
    in_place: bool,
    no_cache: bool,
    verbose: bool,
) -> None:
    """Generate solutions for selected items or files in an existing TeX project.

    With no --tex, reads agentic/scans and writes successful solutions back to
    those files. Organized classification sidecars supply subject, type,
    chapter, topic, and diagram routing unless explicitly overridden.

    \b
    Examples:
        vbagent solve --from 1 --to 5
        vbagent solve --item 7 --no-cache
        vbagent solve -t scanned.tex -o solved.tex
        vbagent solve -t custom-scans/ --in-place --from 1 --to 5
    """
    del verbose  # The callback configures shared logging; no local use needed.

    console = _get_console()
    if input_path is None:
        input_path = Path("agentic/scans")
        if not input_path.exists():
            raise click.ClickException(
                "Default scan directory agentic/scans does not exist; "
                "run 'vbagent scan' first or pass --tex"
            )
        if output is None:
            in_place = True
        mode = (
            "solutions written in place"
            if in_place
            else f"solutions written to {output}"
        )
        console.print(f"[dim]Using default stage workspace: agentic/scans ({mode})[/dim]")

    item_range = resolve_item_range(from_index, to_index, item)
    if item_range is not None:
        from_index, to_index = item_range
    if in_place and output:
        raise click.UsageError("Use --in-place or --output, not both")

    excluded = parse_excluded_indices(exclude)

    if input_path.is_dir():
        source_files = sort_tex_files(input_path.glob("*.tex"))
        if not source_files:
            raise click.ClickException(f"No .tex files found in {input_path}")
        units = _folder_units(source_files)
        unit_contents = {
            index: source_file.read_text(encoding="utf-8")
            for index, source_file in units
        }
        output_dir = input_path if in_place else _resolve_folder_output_path(
            input_path, str(output) if output else None
        )
        if not in_place and output_dir.resolve() == input_path.resolve():
            raise click.ClickException("Output directory must differ from the input directory")
    else:
        content = input_path.read_text(encoding="utf-8")
        spans = _item_spans(content)
        if not spans:
            raise click.ClickException("The input TeX file is empty")
        units = [(index, input_path) for index in range(1, len(spans) + 1)]
        unit_contents = {
            index: item_content
            for index, (_, _, item_content) in enumerate(spans, 1)
        }
        output_dir = None

    candidates = (
        _select_folder_units(units, from_index, to_index, excluded)
        if input_path.is_dir()
        else select_item_indices(len(units), from_index, to_index, excluded)
    )
    existing_solution_indices = {
        index for index, item_content in unit_contents.items()
        if has_solution_environment(item_content)
    }
    skipped_existing = len(set(candidates) & existing_solution_indices)
    selected = [index for index in candidates if index not in existing_solution_indices]

    from vbagent.config import get_config
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated

    configured = get_config()
    project_metadata = content if not input_path.is_dir() else ""

    cache = None
    if not no_cache:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()

    failures: list[tuple[int, str]] = []
    available_numbers = {number for number, _ in units}
    excluded_count = len(available_numbers & excluded)
    console.print(
        f"[cyan]Candidates {len(candidates)}/{len(units)} "
        f"{'file(s)' if input_path.is_dir() else 'item(s)'}; "
        f"excluded {excluded_count}; "
        f"skipped existing solution {skipped_existing}; "
        f"to solve {len(selected)}[/cyan]"
    )

    def generate_for(source_path: Path, item_number: int, item_content: str):
        classification_metadata = _load_classification_metadata(source_path)
        resolved_subject = (
            subject
            or _metadata_value(item_content, "subject")
            or _metadata_value(project_metadata, "subject")
            or classification_metadata.get("subject")
            or configured.subject
        )
        resolved_type = (
            question_type
            or _metadata_value(item_content, "type")
            or _metadata_value(project_metadata, "type")
            or classification_metadata.get("question_type")
            or "subjective"
        )
        if resolved_subject not in SUBJECTS:
            raise click.ClickException(f"Unsupported subject: {resolved_subject}")
        if resolved_type not in QUESTION_TYPES:
            raise click.ClickException(
                f"Unsupported question type: {resolved_type}. Use --type to override it."
            )
        primary = PrimaryClassification(
            subject=resolved_subject,
            question_type=resolved_type,
            has_diagram=bool(classification_metadata.get("has_diagram", False)),
            confidence=1.0,
            classified_from="latex",
            chapter=chapter or classification_metadata.get("chapter"),
            topic=topic or classification_metadata.get("topic"),
        )
        source_image = (
            find_image_for_problem(source_path)
            if source_path.parent.name == "scans"
            else None
        )
        return generate_solution_orchestrated(
            image_path=str(source_image.resolve() if source_image else input_path),
            primary=primary,
            problem_latex=item_content,
            cache=cache,
            problem_id=_cache_problem_id(
                source_path, item_number, item_content,
                resolved_subject, resolved_type, no_diagram,
            ),
            console=console,
            return_result=True,
            generate_diagrams=not no_diagram,
        )

    if input_path.is_dir():
        import shutil

        source_by_number = dict(units)

        if not in_place:
            output_dir.mkdir(parents=True, exist_ok=True)
            for _, source_file in units:
                shutil.copy2(source_file, output_dir / source_file.name)

        for file_number in selected:
            source_file = source_by_number[file_number]
            console.print(f"\n[bold]Problem {file_number}: {source_file.name}[/bold]")
            try:
                result = generate_for(
                    source_file,
                    file_number,
                    unit_contents[file_number],
                )
                (output_dir / source_file.name).write_text(
                    result.latex, encoding="utf-8"
                )
                console.print(f"[green]OK[/green] {source_file.name} solved")
            except Exception as exc:
                failures.append((file_number, str(exc)))
                console.print(f"[red]ERROR[/red] {source_file.name}: {exc}")

        action = "Updated input project" if in_place else "Saved solution project"
        console.print(f"\n[green]{action}:[/green] {output_dir}")
    else:
        replacements: dict[int, str] = {}
        for item_number in selected:
            item_content = unit_contents[item_number]
            console.print(f"\n[bold]Item {item_number}/{len(spans)}[/bold]")
            try:
                result = generate_for(input_path, item_number, item_content)
                replacements[item_number] = result.latex
                console.print(f"[green]OK[/green] Item {item_number} solved")
            except Exception as exc:
                failures.append((item_number, str(exc)))
                console.print(f"[red]ERROR[/red] Item {item_number}: {exc}")

        output_path = input_path if in_place else _resolve_output_path(
            input_path, str(output) if output else None
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _replace_items(content, spans, replacements), encoding="utf-8"
        )
        action = "Updated input project" if in_place else "Saved solution project"
        console.print(f"\n[green]{action}:[/green] {output_path}")

    console.print(
        f"[cyan]Solved {len(selected) - len(failures)}/{len(selected)} "
        f"selected {'file(s)' if input_path.is_dir() else 'item(s)'}[/cyan]"
    )

    if failures:
        raise click.ClickException(
            f"{len(failures)} item(s) failed; successful results were saved"
        )


__all__ = [
    "solve",
    "has_solution_environment",
    "sort_tex_files",
    "parse_excluded_indices",
    "select_item_indices",
]
