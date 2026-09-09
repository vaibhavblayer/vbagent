"""CLI command for regenerating parts of already-generated problems.

Two modes:
    --tikz-only   Re-run only the TikZ diagram agent (keeps problem/solution)
    --full        Re-generate everything (problem + solution + diagram)

Works with both output layouts:
    agentic/generated/scans/          (flat: problems/, tikz/, generation/)
    agentic/generated/originals/…/    (per-problem dirs with meta.json)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import click

from vbagent.cli.common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


_SOLUTION_START_RE = re.compile(r"\\begin\s*\{solution\}", re.IGNORECASE)
_DIAGRAM_ENV_RE = re.compile(
    r"\\begin\{(?P<env>tikzpicture|circuitikz)\}"
    r"(?:\[[^\]]*\])?.*?\\end\{(?P=env)\}",
    re.DOTALL,
)
_CENTER_BEFORE_RE = re.compile(r"\\begin\{center\}\s*$", re.DOTALL)
_CENTER_AFTER_RE = re.compile(r"^\s*\\end\{center\}", re.DOTALL)
_DEFINITION_START_RE = re.compile(r"\\def\\(?:Option|Match)[A-Za-z]+\s*\{")


def _scan_workspace_dir(target: Path) -> Path | None:
    """Resolve a current scan project, scan directory, or individual TeX file."""
    if target.is_file():
        return target.parent if target.suffix.lower() == ".tex" else None

    candidates = [
        target / "agentic" / "scans",
        target / "scans",
        target,
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.tex")):
            return candidate
    return None


def _scan_workspace_files(target: Path) -> list[Path]:
    """Return naturally ordered current-layout scan files for *target*."""
    from vbagent.cli.generation.solve import sort_tex_files

    if target.is_file():
        return [target] if target.suffix.lower() == ".tex" else []
    scans_dir = _scan_workspace_dir(target)
    return sort_tex_files(scans_dir.glob("*.tex")) if scans_dir else []


def _is_current_scan_target(target: Path) -> bool:
    """Distinguish current scan workspaces from legacy single-problem folders."""
    if target.is_file():
        return target.suffix.lower() == ".tex"
    if (target / "agentic" / "scans").is_dir():
        return True
    if target.name == "scans" and any(target.glob("*.tex")):
        return True
    top_level_tex = list(target.glob("*.tex")) if target.is_dir() else []
    legacy_markers = (target / "meta.json", target / "concepts.json")
    return bool(top_level_tex) and not any(path.exists() for path in legacy_markers)


def _problem_number(path: Path, fallback: int) -> int:
    """Use a trailing problem number when present, matching solve/run selection."""
    match = re.search(r"(\d+)(?!.*\d)", path.stem)
    return int(match.group(1)) if match else fallback


def _selected_scan_files(
    files: list[Path],
    items: list[str],
    from_index: int | None,
    to_index: int | None,
    excluded: set[int],
) -> list[Path]:
    """Select current-layout scan files by numeric suffix or explicit name."""
    numbered = [
        (_problem_number(path, index), path)
        for index, path in enumerate(files, 1)
    ]
    if items:
        if from_index is not None or to_index is not None:
            raise click.UsageError("Use --item or --from/--to, not both")
        if len(items) != 1 or not items[0].strip().isdigit():
            raise click.BadParameter(
                "Scoped scan regeneration accepts one positive problem number",
                param_hint="--item",
            )
        requested_number = int(items[0])
        if requested_number < 1:
            raise click.BadParameter(
                "must be positive (1-based)",
                param_hint="--item",
            )
        return [
            path
            for number, path in numbered
            if number == requested_number and number not in excluded
        ]

    start = 1 if from_index is None else from_index
    end = (
        max((number for number, _ in numbered), default=0)
        if to_index is None
        else to_index
    )
    if start > end:
        raise click.BadParameter("--from must be <= --to")
    return [
        path
        for number, path in numbered
        if start <= number <= end and number not in excluded
    ]


def _parse_excluded(values: tuple[str, ...]) -> set[int]:
    """Parse repeated comma-separated exclusions."""
    from vbagent.cli.generation.solve import parse_excluded_indices

    return parse_excluded_indices(values)


def _definition_ranges(text: str) -> list[tuple[int, int]]:
    """Return balanced ranges for Option/Match diagram macro definitions."""
    ranges: list[tuple[int, int]] = []
    for match in _DEFINITION_START_RE.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
                depth += 1
            elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
                depth -= 1
            index += 1
        if depth == 0:
            ranges.append((match.start(), index))
    return ranges


def _standalone_diagram_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate standalone diagrams, excluding Option/Match macro definitions."""
    definition_ranges = _definition_ranges(text)
    spans: list[tuple[int, int, str]] = []
    for match in _DIAGRAM_ENV_RE.finditer(text):
        if any(start <= match.start() < end for start, end in definition_ranges):
            continue

        start, end = match.span()
        prefix = text[:start]
        suffix = text[end:]
        before = _CENTER_BEFORE_RE.search(prefix)
        after = _CENTER_AFTER_RE.search(suffix)
        if before and after:
            start = before.start()
            end += after.end()
        spans.append((start, end, match.group(0)))
    return spans


def _split_problem_and_solution(content: str) -> tuple[str, str]:
    """Split at the first solution environment without normalizing either side."""
    match = _SOLUTION_START_RE.search(content)
    if not match:
        return content, ""
    return content[:match.start()], content[match.start():]


def _center_diagram(code: str) -> str:
    """Return one consistently centered generated diagram."""
    code = code.strip()
    if code.startswith(r"\begin{center}") and code.endswith(r"\end{center}"):
        return code
    return "\\begin{center}\n" + code + "\n\\end{center}"


def _replace_problem_diagrams(problem_latex: str, tikz_code: str) -> str:
    """Replace only standalone problem-side diagrams, preserving macro diagrams."""
    spans = _standalone_diagram_spans(problem_latex)
    if not spans:
        raise ValueError("no standalone problem diagram found")

    replacement = _center_diagram(tikz_code)
    result = problem_latex
    for index, (start, end, _old_code) in enumerate(reversed(spans)):
        # Keep one regenerated composite at the first original diagram location.
        original_index = len(spans) - 1 - index
        new_text = replacement if original_index == 0 else ""
        result = result[:start] + new_text + result[end:]
    return result


def _replace_solution_diagrams(
    solution_latex: str,
    generator,
) -> tuple[str, int]:
    """Regenerate every standalone diagram inside the existing solution only."""
    spans = _standalone_diagram_spans(solution_latex)
    if not spans:
        return solution_latex, 0

    result = solution_latex
    generated: list[tuple[int, int, str]] = []
    for diagram_index, (start, end, old_code) in enumerate(spans, 1):
        new_code = generator(old_code, diagram_index, len(spans))
        generated.append((start, end, _center_diagram(new_code)))
    for start, end, new_code in reversed(generated):
        result = result[:start] + new_code + result[end:]
    return result, len(generated)


def _infer_diagram_type(subject: str, metadata: dict, content: str) -> str | None:
    """Choose a specialist route when legacy classification lacks diagram fields."""
    explicit = metadata.get("suggested_tikz_agent") or metadata.get("diagram_type")
    if explicit:
        return str(explicit)

    lowered = content.lower()
    if subject == "physics":
        rules = (
            ("circuit", ("circuit", "resistor", "capacitor", "battery")),
            ("optics", ("lens", "mirror", "ray diagram", "refraction")),
            ("wave", ("standing wave", "wavelength", "antinode")),
            ("graph", ("plot", "graph of", "versus")),
            ("mechanics", (
                "rod", "disc", "disk", "rolling", "pulley", "spring", "block",
                "projectile", "trajectory", "pivot", "rotation", "angular",
            )),
        )
        for diagram_type, keywords in rules:
            if any(keyword in lowered for keyword in keywords):
                return diagram_type
        return "setup"
    if subject == "mathematics":
        if any(word in lowered for word in ("graph", "function", "plot")):
            return "function_graph"
        return "geometric_figure"
    return None


def _generate_scoped_diagram(
    *,
    role: str,
    existing_code: str,
    problem_latex: str,
    solution_latex: str,
    metadata: dict,
    subject: str,
    question_type: str,
    extra_prompt: str | None,
    image_path: Path | None,
    console,
) -> str:
    """Generate one diagram without invoking the scanner or solution writer."""
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    from vbagent.models.classification import PrimaryClassification

    diagram_type = _infer_diagram_type(
        subject,
        metadata,
        problem_latex + "\n" + solution_latex + "\n" + existing_code,
    )
    primary = PrimaryClassification(
        subject=subject,
        question_type=question_type,
        has_diagram=True,
        chapter=metadata.get("chapter"),
        topic=metadata.get("topic"),
        confidence=1.0,
        classified_from="latex",
    )
    role_instruction = (
        "Reconstruct only the printed problem diagram from the source image. "
        "Preserve its physical meaning, geometry, motion arrows, dimensions, and "
        "indispensable labels. Do not reproduce passage text, questions, options, "
        "answers, or solution annotations. Improve spacing and visual clarity."
        if role == "problem"
        else
        "Recreate only this existing solution diagram. Preserve the scientific "
        "meaning and every indispensable construction, vector, and label while "
        "improving spacing and legibility. Do not rewrite or repeat solution prose."
    )
    description = (
        f"{role_instruction}\n\nExisting diagram code for semantic reference:\n"
        f"{existing_code.strip()}"
    )
    if extra_prompt:
        description += f"\n\nAdditional user instruction:\n{extra_prompt.strip()}"

    code, agent = generate_tikz_with_routing(
        image_path=str(image_path) if role == "problem" and image_path else None,
        description=description,
        primary=primary,
        subject=subject,
        diagram_type=diagram_type,
        problem_text=problem_latex,
        solution_context=solution_latex if role == "solution" else None,
        use_context=True,
        show_spinner=True,
        diagram_context=role,
    )
    console.print(f"  [green]OK[/green] {role} diagram [dim]{agent}[/dim]")
    return code


def _regenerate_current_scan_file(
    tex_file: Path,
    scope: str,
    extra_prompt: str | None,
    compile_result: bool,
    console,
    subject_override: str | None = None,
) -> tuple[bool, int]:
    """Regenerate selected diagram roles transactionally for one scan file."""
    from vbagent.cli.common import find_image_for_problem
    from vbagent.cli.generation.solve import _load_classification_metadata
    from vbagent.config import get_config

    original = tex_file.read_text(encoding="utf-8")
    problem_latex, solution_latex = _split_problem_and_solution(original)
    metadata = _load_classification_metadata(tex_file)
    subject = str(subject_override or metadata.get("subject") or get_config().subject)
    question_type = str(metadata.get("question_type") or "subjective")
    image_path = find_image_for_problem(tex_file)
    changed = False
    diagram_count = 0

    if scope in {"problem", "both"}:
        problem_spans = _standalone_diagram_spans(problem_latex)
        if problem_spans:
            old_code = "\n\n".join(span[2] for span in problem_spans)
            new_code = _generate_scoped_diagram(
                role="problem",
                existing_code=old_code,
                problem_latex=problem_latex,
                solution_latex=solution_latex,
                metadata=metadata,
                subject=subject,
                question_type=question_type,
                extra_prompt=extra_prompt,
                image_path=image_path,
                console=console,
            )
            problem_latex = _replace_problem_diagrams(problem_latex, new_code)
            changed = True
            diagram_count += len(problem_spans)
        else:
            console.print("  [dim]No standalone problem diagram; skipped[/dim]")

    if scope in {"solution", "both"}:
        if not solution_latex:
            console.print("  [dim]No solution environment; skipped solution diagrams[/dim]")
        else:
            def generate_solution(old_code: str, index: int, total: int) -> str:
                console.print(f"  Regenerating solution diagram {index}/{total}...")
                return _generate_scoped_diagram(
                    role="solution",
                    existing_code=old_code,
                    problem_latex=problem_latex,
                    solution_latex=solution_latex,
                    metadata=metadata,
                    subject=subject,
                    question_type=question_type,
                    extra_prompt=extra_prompt,
                    image_path=None,
                    console=console,
                )

            solution_latex, solution_count = _replace_solution_diagrams(
                solution_latex, generate_solution
            )
            if solution_count:
                changed = True
                diagram_count += solution_count
            else:
                console.print("  [dim]No standalone solution diagram; skipped[/dim]")

    if not changed:
        return False, 0

    candidate = problem_latex + solution_latex
    if compile_result:
        from vbagent.compile import compile_latex

        result = compile_latex(candidate, subject=subject)
        if not result.success:
            raise RuntimeError(
                "generated diagram failed LaTeX validation: " + result.error_summary
            )
        console.print("  [green]OK[/green] LaTeX validation")

    # Write only after every requested generation and validation step succeeds.
    tex_file.write_text(candidate, encoding="utf-8")
    return True, diagram_count


def _regenerate_current_scans(
    target: Path,
    scope: str,
    items: list[str],
    from_index: int | None,
    to_index: int | None,
    exclude: tuple[str, ...],
    extra_prompt: str | None,
    compile_result: bool,
    console,
    subject_override: str | None = None,
) -> int:
    """Run scoped diagram regeneration on the current agentic/scans layout."""
    files = _scan_workspace_files(target)
    selected = _selected_scan_files(
        files, items, from_index, to_index, _parse_excluded(exclude)
    )
    if not selected:
        raise click.ClickException("No scan files matched the requested selection")

    console.print(
        f"[cyan]Regenerating {scope} diagram(s) for {len(selected)} problem(s)[/cyan]"
    )
    updated = 0
    diagrams = 0
    failures: list[tuple[str, str]] = []
    for tex_file in selected:
        console.print(f"\n[bold]{tex_file.name}[/bold]")
        try:
            changed, count = _regenerate_current_scan_file(
                tex_file,
                scope,
                extra_prompt,
                compile_result,
                console,
                subject_override=subject_override,
            )
            if changed:
                updated += 1
                diagrams += count
                console.print(f"  [green]Saved[/green] {tex_file}")
        except Exception as exc:
            failures.append((tex_file.name, str(exc)))
            console.print(f"  [red]ERROR[/red] {exc}")

    console.print(
        f"\n[cyan]Updated {updated}/{len(selected)} problem(s); "
        f"regenerated {diagrams} diagram(s)[/cyan]"
    )
    if failures:
        names = ", ".join(name for name, _ in failures)
        raise click.ClickException(f"{len(failures)} problem(s) failed: {names}")
    return updated


def _find_problem_dirs(target: Path) -> list[Path]:
    """Resolve target into a list of problem directories/files.

    Handles:
      - A concepts dir          (has concepts.json)
      - A single originals dir  (has meta.json)
      - A parent dir containing multiple originals dirs
      - A scans-style dir       (has problems/ subdir)
    """
    results: list[Path] = []

    # Concepts layout
    if (target / "concepts.json").exists():
        return [target]

    # Single originals-style dir
    if (target / "meta.json").exists():
        return [target]

    # Parent of multiple originals dirs
    for child in sorted(target.rglob("meta.json")):
        results.append(child.parent)

    if results:
        return results

    # Scans-style: target has problems/ subdir
    if (target / "problems").is_dir():
        return [target]

    return []


def _detect_layout(problem_dir: Path) -> str:
    """Detect whether this is 'originals', 'scans', or 'concepts' layout."""
    if (problem_dir / "concepts.json").exists():
        return "concepts"
    if (problem_dir / "meta.json").exists():
        return "originals"
    if (problem_dir / "problems").is_dir():
        return "scans"
    return "unknown"


# ------------------------------------------------------------------
# Originals layout helpers
# ------------------------------------------------------------------

def _regen_tikz_originals(problem_dir: Path, subject: str, force: bool, console) -> bool:
    """Regenerate only the TikZ diagram for an originals-style problem."""
    from vbagent.pipeline.combine import _generate_tikz, _insert_tikz_into_latex

    problem_path = problem_dir / "problem.tex"
    meta_path = problem_dir / "meta.json"

    if not problem_path.exists():
        console.print(f"  [yellow]No problem.tex in {problem_dir.name}[/yellow]")
        return False

    # Resume: skip if tikz already exists
    tikz_file = problem_dir / "tikz" / "diagram.tex"
    if not force and tikz_file.exists():
        console.print(f"  [dim]skipped (already done)[/dim]")
        return False

    problem_tex = problem_path.read_text()
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    # Extract diagram description from meta or infer from problem text
    diagram_desc = meta.get("diagram_description", "")
    if not diagram_desc:
        # Use the problem text itself as the description hint
        diagram_desc = problem_tex[:500]

    t0 = time.time()
    tikz_code = _generate_tikz(diagram_desc, subject, problem_tex=problem_tex, console=console)
    elapsed = time.time() - t0

    if not tikz_code:
        console.print(f"  [yellow]TikZ generation returned empty[/yellow]")
        return False

    # Save TikZ separately
    tikz_dir = problem_dir / "tikz"
    tikz_dir.mkdir(exist_ok=True)
    (tikz_dir / "diagram.tex").write_text(tikz_code)

    # Re-inject into problem.tex — strip old TikZ block first, then inject new
    clean_tex = _strip_existing_tikz(problem_tex)
    updated_tex = _insert_tikz_into_latex(clean_tex, tikz_code)
    problem_path.write_text(updated_tex)

    console.print(f"  [green]OK[/green] TikZ regenerated ({elapsed:.1f}s)")
    return True


def _regen_full_originals(problem_dir: Path, subject: str, console) -> bool:
    """Regenerate everything for an originals-style problem."""
    from vbagent.pipeline.combine import (
        generate_combined_problem,
        _generate_tikz,
        _insert_tikz_into_latex,
        _save_combined,
        _infer_primary_topic,
    )
    from vbagent.ideas.store import IdeaStore
    from vbagent.ideas.models import Idea, CombinationRecord

    meta_path = problem_dir / "meta.json"
    if not meta_path.exists():
        console.print(f"  [yellow]No meta.json — cannot reconstruct inputs[/yellow]")
        return False

    meta = json.loads(meta_path.read_text())

    # Load the idea store to get full idea objects
    store_path = Path(f"agentic/idea_store/{subject}.json")
    if not store_path.exists():
        console.print(f"  [red]Idea store not found: {store_path}[/red]")
        return False

    store = IdeaStore(store_path, subject=subject)

    # Reconstruct parameters from meta
    idea_ids = meta.get("selected_idea_ids", [])
    lenses = meta.get("lenses", [])
    difficulty = meta.get("difficulty", 5)
    question_type = meta.get("question_type", "mcq_sc")
    combo_id = meta.get("id", problem_dir.name)

    # Find the actual idea objects
    candidates = [i for i in store.ideas if i.id in idea_ids]
    if len(candidates) < 2:
        # Fallback: try candidate_ideas from meta
        candidate_meta = meta.get("candidate_ideas", [])
        candidate_ids = [c["id"] for c in candidate_meta]
        candidates = [i for i in store.ideas if i.id in candidate_ids]

    if len(candidates) < 2:
        console.print(f"  [yellow]Not enough ideas found in store for {combo_id}[/yellow]")
        return False

    console.print(f"  Regenerating with {len(candidates)} ideas, lenses={lenses}, difficulty={difficulty}")

    t0 = time.time()
    result_dict = generate_combined_problem(
        store=store,
        pick=len(candidates) + 2,  # pick more so the agent has choices
        lenses=lenses or None,
        difficulty=difficulty,
        question_type=question_type,
        topic=meta.get("topic"),
        with_diagram=True,
        output_base=problem_dir.parent.parent.parent.parent,  # back to generated/
        subject=subject,
        console=console,
    )
    elapsed = time.time() - t0

    if result_dict:
        console.print(f"  [green]OK[/green] Full regeneration ({elapsed:.1f}s)")
        return True
    else:
        console.print(f"  [yellow]Regeneration returned no result[/yellow]")
        return False


# ------------------------------------------------------------------
# Scans layout helpers
# ------------------------------------------------------------------

def _regen_tikz_scans(scans_dir: Path, items: list[str], subject: str, force: bool, console) -> int:
    """Regenerate TikZ for scans-style problems."""
    from vbagent.pipeline.combine import _generate_tikz, _insert_tikz_into_latex

    problems_dir = scans_dir / "problems"
    tikz_dir = scans_dir / "tikz"
    tikz_dir.mkdir(exist_ok=True)

    count = 0
    skipped = 0
    for tex_file in sorted(problems_dir.glob("*.tex")):
        name = tex_file.stem
        if items and name not in items:
            continue

        # Resume: skip if tikz already exists
        tikz_file = tikz_dir / f"{name}.tex"
        if not force and tikz_file.exists():
            skipped += 1
            continue

        console.print(f"\n[bold]{name}[/bold]")
        problem_tex = tex_file.read_text()

        # Use problem text as diagram hint
        t0 = time.time()
        tikz_code = _generate_tikz(
            problem_tex[:500], subject, problem_tex=problem_tex, console=console,
        )
        elapsed = time.time() - t0

        if tikz_code:
            (tikz_dir / f"{name}.tex").write_text(tikz_code)

            # Re-inject into problem.tex
            clean_tex = _strip_existing_tikz(problem_tex)
            updated_tex = _insert_tikz_into_latex(clean_tex, tikz_code)
            tex_file.write_text(updated_tex)

            console.print(f"  [green]OK[/green] TikZ regenerated ({elapsed:.1f}s)")
            count += 1
        else:
            console.print(f"  [yellow]TikZ generation returned empty[/yellow]")

    if skipped:
        console.print(f"\n  [dim]Skipped {skipped} (already done, use --force to redo)[/dim]")

    return count


def _regen_full_scans(scans_dir: Path, items: list[str], subject: str, console) -> int:
    """Regenerate full content for scans-style problems."""
    from vbagent.pipeline.generate import generate_from_ideas_dir

    problems_dir = scans_dir / "problems"
    gen_dir = scans_dir / "generation"

    count = 0
    for tex_file in sorted(problems_dir.glob("*.tex")):
        name = tex_file.stem
        if items and name not in items:
            continue

        # Read generation meta to get original params
        gen_meta_path = gen_dir / f"{name}.json"
        gen_meta = {}
        if gen_meta_path.exists():
            gen_meta = json.loads(gen_meta_path.read_text())

        console.print(f"\n[bold]{name}[/bold] (full regeneration)")

        # For scans, we re-run the generate pipeline on the source scan
        source_file = gen_meta.get("source_file", f"{name}.tex")
        scans_source = Path("agentic/scans")

        if not (scans_source / source_file).exists():
            console.print(f"  [yellow]Source scan not found: {source_file}[/yellow]")
            continue

        from vbagent.pipeline.generate import (
            generate_from_ideas_dir, _save_generation, GenerationResult,
        )

        t0 = time.time()
        results = generate_from_ideas_dir(
            ideas_dir=Path("agentic/ideas"),
            scans_dir=scans_source,
            question_type=gen_meta.get("question_type", "subjective"),
            difficulty=gen_meta.get("difficulty", "medium"),
            topic="",
            with_solution=True,
            with_diagram=True,
            item_range=None,
            output_base=scans_dir,
            console=console,
        )
        elapsed = time.time() - t0

        for problem_tex, solution_tex, tikz_code, meta, idea_latex in results:
            if meta.get("base_name") == name:
                result = GenerationResult(
                    base_name=name, output_dir=scans_dir,
                    problem_tex=problem_tex, solution_tex=solution_tex,
                    tikz_code=tikz_code, idea_latex=idea_latex,
                    generation_meta=meta, source="scans",
                    elapsed=elapsed,
                )
                _save_generation(result)
                console.print(f"  [green]OK[/green] Full regeneration ({elapsed:.1f}s)")
                count += 1
                break

    return count


# ------------------------------------------------------------------
# TikZ stripping helper
# ------------------------------------------------------------------

def _strip_existing_tikz(tex: str) -> str:
    """Remove existing TikZ/circuitikz blocks from LaTeX content."""
    import re
    # Remove \begin{tikzpicture}...\end{tikzpicture}
    tex = re.sub(
        r"\\begin\{center\}\s*\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}\s*\\end\{center\}",
        "", tex, flags=re.DOTALL,
    )
    # Remove \begin{circuitikz}...\end{circuitikz}
    tex = re.sub(
        r"\\begin\{center\}\s*\\begin\{circuitikz\}.*?\\end\{circuitikz\}\s*\\end\{center\}",
        "", tex, flags=re.DOTALL,
    )
    # Also handle bare tikzpicture without center
    tex = re.sub(
        r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
        "", tex, flags=re.DOTALL,
    )
    tex = re.sub(
        r"\\begin\{circuitikz\}.*?\\end\{circuitikz\}",
        "", tex, flags=re.DOTALL,
    )
    # Clean up double blank lines
    tex = re.sub(r"\n{3,}", "\n\n", tex)
    return tex.strip()


# ------------------------------------------------------------------
# Concepts layout helpers
# ------------------------------------------------------------------

def _slug(name: str) -> str:
    """Consistent slug for a concept entry name."""
    return name.lower().replace(" ", "_")[:40]


def _collect_diagram_entries(sheet) -> list[tuple[str, str, object]]:
    """Return flat list of (group_subtopic, slug, entry) for entries needing diagrams."""
    entries = []
    for group in sheet.groups:
        for entry in group.entries:
            if entry.needs_diagram and entry.diagram_description:
                entries.append((group.subtopic, _slug(entry.name), entry))
    return entries


def _parse_selection(raw: str, total: int) -> set[int] | None:
    """Parse user input like '1,3,7' or 'all' into a set of 0-based indices.

    Returns None for 'all', empty set for empty/skip input.
    """
    raw = raw.strip().lower()
    if raw in ("all", "a"):
        return None  # means select all
    if not raw:
        return set()  # skip

    indices: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            # Range like 3-7
            lo, hi = part.split("-", 1)
            lo_i, hi_i = int(lo.strip()), int(hi.strip())
            for i in range(lo_i, hi_i + 1):
                if 1 <= i <= total:
                    indices.add(i - 1)
        elif part.isdigit():
            idx = int(part)
            if 1 <= idx <= total:
                indices.add(idx - 1)
    return indices


def _show_diagram_list(entries, tikz_dir: Path, console) -> None:
    """Print numbered list of diagram entries with cached status."""
    console.print()
    for i, (subtopic, slug, entry) in enumerate(entries, 1):
        cached = (tikz_dir / f"{slug}.tex").exists()
        status = "[green]OK[/green]" if cached else "[red]ERROR[/red]"
        console.print(f"  {status} {i:>2}. {entry.name}  [dim]({subtopic})[/dim]")
    console.print()


def _regen_tikz_concepts(
    concepts_dir: Path, subject: str, items: list[str], force: bool, console,
) -> int:
    """Regenerate TikZ diagrams in a concepts sheet.

    Reads concepts.json, regenerates diagrams for entries with
    needs_diagram=true, then re-renders concepts.tex.

    Interactive mode: when no --item filter and not --force, shows a
    numbered list and prompts user to pick entries by number.
    """
    json_path = concepts_dir / "concepts.json"
    tex_path = concepts_dir / "concepts.tex"

    data = json.loads(json_path.read_text())

    from vbagent.agents.content_generation.concepts import (
        _generate_concept_diagram,
        _build_mindmap,
    )
    from vbagent.models.content import ConceptSheet

    sheet = ConceptSheet.model_validate(data)
    tikz_dir = concepts_dir / "tikz"

    all_entries = _collect_diagram_entries(sheet)

    # --- Resolve which entries to regenerate ---

    # --item flag: accept names or numbers (e.g. --item 1,3,7)
    if items:
        selected_indices: set[int] | None = set()
        # Check if items look like numbers
        joined = ",".join(items)
        parsed = _parse_selection(joined, len(all_entries))
        if parsed is not None and parsed:
            selected_indices = parsed
        else:
            # Match by name
            for i, (_sub, _slug, entry) in enumerate(all_entries):
                if entry.name in items:
                    selected_indices.add(i)
        force_selected = True  # --item implies force for those entries
    elif force:
        # --force: redo all
        selected_indices = None  # None = all
        force_selected = True
    else:
        # Interactive: show list and prompt
        _show_diagram_list(all_entries, tikz_dir, console)
        raw = click.prompt(
            "  Enter numbers to regenerate (e.g. 1,3,7 or 1-5 or 'all', empty to skip)",
            default="",
            show_default=False,
        )
        selected_indices = _parse_selection(raw, len(all_entries))
        if selected_indices is not None and len(selected_indices) == 0:
            console.print("  [dim]Nothing selected, skipping generation.[/dim]")
            # Still rebuild tex from cached
            console.print(f"\n  Re-rendering concepts.tex from cached diagrams...")
            latex = _rebuild_concepts_tex(sheet, tikz_dir, subject)
            tex_path.write_text(latex)
            console.print(f"  [green]OK[/green] concepts.tex updated")
            return 0
        force_selected = True  # user explicitly picked, so force those

    # --- Generate ---
    count = 0
    skipped = 0

    for i, (subtopic, slug, entry) in enumerate(all_entries):
        # Filter check
        if selected_indices is not None and i not in selected_indices:
            continue

        tikz_path = tikz_dir / f"{slug}.tex"

        # Resume: skip if already generated and not forced
        if not force_selected and tikz_path.exists():
            skipped += 1
            continue

        console.print(f"  {entry.name}...", end=" ")

        t0 = time.time()
        tikz = _generate_concept_diagram(entry.diagram_description, subject)
        elapsed = time.time() - t0

        if tikz:
            tikz_dir.mkdir(exist_ok=True)
            tikz_path.write_text(tikz)
            console.print(f"[green]OK[/green] ({elapsed:.1f}s)")
            count += 1
        else:
            console.print(f"[yellow]empty[/yellow]")

    if skipped:
        console.print(f"  [dim]Skipped {skipped} (already done, use --force to redo)[/dim]")

    # Always re-render concepts.tex using cached tikz files
    console.print(f"\n  Re-rendering concepts.tex from cached diagrams...")
    latex = _rebuild_concepts_tex(sheet, tikz_dir, subject)
    tex_path.write_text(latex)
    console.print(f"  [green]OK[/green] concepts.tex updated")

    return count


def _rebuild_concepts_tex(sheet, tikz_dir: Path, subject: str) -> str:
    """Rebuild concepts.tex from JSON + cached tikz files (no LLM calls)."""
    from vbagent.agents.content_generation.concepts import _build_mindmap

    lines = [f"\\section*{{{sheet.title}}}", ""]

    for group in sheet.groups:
        lines.append(f"\\subsection*{{{group.subtopic}}}")
        lines.append("\\begin{itemize}")
        for entry in group.entries:
            lines.append(f"\\item {entry.name} \\hfill [{entry.frequency}]\\\\")
            if entry.description:
                lines.append(f"\\textit{{{entry.description}}}")
            if entry.formulas:
                lines.append("    \\begin{align*}")
                for i, f in enumerate(entry.formulas):
                    formula = f.strip().strip("$").strip()
                    suffix = " \\\\" if i < len(entry.formulas) - 1 else ""
                    lines.append(f"    {formula}{suffix}")
                lines.append("    \\end{align*}")
            # Insert cached TikZ diagram if available
            if entry.needs_diagram and entry.diagram_description:
                slug = _slug(entry.name)
                tikz_path = tikz_dir / f"{slug}.tex"
                if tikz_path.exists():
                    lines.append(tikz_path.read_text().strip())
        lines.append("\\end{itemize}")
        lines.append("")

    # Mindmap
    group_names = [g.subtopic for g in sheet.groups]
    if len(group_names) >= 2:
        lines.append(_build_mindmap(sheet.title or sheet.topic, group_names))

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI command
# ------------------------------------------------------------------

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "target",
    required=False,
    default="agentic/scans",
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--tikz-only", is_flag=True, help="Regenerate only the TikZ diagram")
@click.option("--full", "full_regen", is_flag=True, help="Regenerate everything (problem + solution + diagram)")
@click.option("--force", is_flag=True, help="Redo all, even if already generated (default: resume/skip done)")
@click.option(
    "--item",
    multiple=True,
    help="Single problem number (legacy layouts also accept repeatable name filters)",
)
@click.option("--from", "from_index", type=click.IntRange(min=1), help="Start problem number (inclusive)")
@click.option("--to", "to_index", type=click.IntRange(min=1), help="End problem number (inclusive)")
@click.option("--exclude", multiple=True, help="Problem numbers to skip (comma-separated)")
@click.option("--problem-diagram", is_flag=True, help="Regenerate only problem-side diagrams")
@click.option("--solution-diagram", is_flag=True, help="Regenerate only diagrams inside solutions")
@click.option("--both-diagrams", is_flag=True, help="Regenerate problem and solution diagrams")
@click.option("--prompt", "extra_prompt", help="Additional diagram instruction")
@click.option("-c", "--compile", "compile_result", is_flag=True, help="Compile each candidate before saving")
@click.option(
    "--subject",
    type=click.Choice(["physics", "chemistry", "mathematics", "biology"]),
    default=None,
    help="Subject override",
)
@click.option("-v", "--verbose", is_flag=True)
def regenerate(
    target: Path,
    tikz_only: bool,
    full_regen: bool,
    force: bool,
    item: tuple[str, ...],
    from_index: int | None,
    to_index: int | None,
    exclude: tuple[str, ...],
    problem_diagram: bool,
    solution_diagram: bool,
    both_diagrams: bool,
    extra_prompt: str | None,
    compile_result: bool,
    subject: str | None,
    verbose: bool,
):
    """Regenerate diagrams or full content for existing problems.

    \b
    TARGET may be a current project folder, its agentic/scans directory, a
    single scan file, or one of the legacy generated/concepts layouts. It
    defaults to agentic/scans.

    \b
    Current scan modes (problem and solution prose is preserved):
      --problem-diagram   Replace only diagrams before the solution
      --solution-diagram  Replace only diagrams inside the existing solution
      --both-diagrams     Replace both diagram roles independently

    \b
    Legacy TARGET layouts:
      - A concepts dir         (has concepts.json — regenerates concept diagrams)
      - A single problem dir   (has meta.json or problem.tex)
      - A parent dir           (contains multiple problem dirs)
      - A scans output dir     (has problems/ subdir)

    \b
    Modes:
      --tikz-only    Re-run only the TikZ agent (keeps problem/solution text)
      --full         Re-generate everything from scratch using meta.json

    \b
    Legacy default (no flag) = --tikz-only. Current scan projects require one
    of the three explicit diagram-scope flags above.
    Legacy resume skips entries that already have a TikZ file. Use --force to
    redo all.

    \b
    Examples:
      vbagent regenerate --problem-diagram --item 2
      vbagent regenerate --solution-diagram --from 1 --to 3
      vbagent regenerate --both-diagrams --from 1 --to 3 --exclude 2 -c
      vbagent regenerate /path/to/project --problem-diagram --from 1 --to 3
      vbagent regenerate agentic/concepts/                      # Regen concept diagrams (resumes)
      vbagent regenerate agentic/concepts/ --force              # Redo all concept diagrams
      vbagent regenerate agentic/concepts/ --item "Cyclotron frequency and resonance"
      vbagent regenerate agentic/generated/originals/ --tikz-only
      vbagent regenerate agentic/generated/scans/ --tikz-only --item problem_1
      vbagent regenerate agentic/generated/originals/physics/magnetism/VBP-PHY-MAG-001-algebra_vectors --full
    """
    from vbagent.config import get_config

    console = _get_console()
    target_path = target
    del verbose

    selected_scopes = [
        scope for enabled, scope in (
            (problem_diagram, "problem"),
            (solution_diagram, "solution"),
            (both_diagrams, "both"),
        )
        if enabled
    ]
    if len(selected_scopes) > 1:
        raise click.UsageError(
            "Use only one of --problem-diagram, --solution-diagram, or --both-diagrams"
        )

    if selected_scopes:
        if tikz_only or full_regen or force:
            raise click.UsageError(
                "Scoped diagram modes cannot be combined with legacy "
                "--tikz-only, --full, or --force"
            )
        if not _scan_workspace_files(target_path):
            raise click.ClickException(
                "Scoped diagram regeneration requires a project containing "
                "agentic/scans, a scans directory, or a .tex scan file"
            )
        _regenerate_current_scans(
            target=target_path,
            scope=selected_scopes[0],
            items=list(item),
            from_index=from_index,
            to_index=to_index,
            exclude=exclude,
            extra_prompt=extra_prompt,
            compile_result=compile_result,
            console=console,
            subject_override=subject,
        )
        return

    if _is_current_scan_target(target_path):
        raise click.UsageError(
            "Choose --problem-diagram, --solution-diagram, or --both-diagrams "
            "for current agentic/scans projects"
        )

    if (
        from_index is not None
        or to_index is not None
        or exclude
        or extra_prompt
        or compile_result
    ):
        raise click.UsageError(
            "--from, --to, --exclude, --prompt, and --compile apply to scoped "
            "current scan regeneration"
        )

    if subject is None:
        subject = get_config().subject

    # Default to tikz-only if neither flag set
    if not tikz_only and not full_regen:
        tikz_only = True

    items_list = list(item) if item else []

    problem_dirs = _find_problem_dirs(target_path)

    if not problem_dirs:
        console.print(f"[red]No problems found in {target}[/red]")
        raise SystemExit(1)

    t0 = time.time()
    success_count = 0
    total_count = 0

    for pdir in problem_dirs:
        layout = _detect_layout(pdir)

        if layout == "concepts":
            console.print(f"\n[bold]Concepts: {pdir}[/bold]")
            success_count += _regen_tikz_concepts(pdir, subject, items_list, force, console)
            total_count += 1

        elif layout == "originals":
            console.print(f"\n[bold]{pdir.name}[/bold]")
            total_count += 1
            if tikz_only:
                if _regen_tikz_originals(pdir, subject, force, console):
                    success_count += 1
            else:
                if _regen_full_originals(pdir, subject, console):
                    success_count += 1

        elif layout == "scans":
            problems_dir = pdir / "problems"
            tex_files = sorted(problems_dir.glob("*.tex"))
            if items_list:
                tex_files = [f for f in tex_files if f.stem in items_list]
            total_count += len(tex_files)

            if tikz_only:
                success_count += _regen_tikz_scans(pdir, items_list, subject, force, console)
            else:
                success_count += _regen_full_scans(pdir, items_list, subject, console)

        else:
            console.print(f"  [yellow]Unknown layout for {pdir}[/yellow]")

    elapsed = time.time() - t0
    mode_label = "TikZ" if tikz_only else "full"
    console.print(f"\n[bold green]Regenerated {success_count}/{total_count} problems[/bold green] ({mode_label}, {elapsed:.1f}s)")
