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
import time
from pathlib import Path

import click

from vbagent.cli.common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _find_problem_dirs(target: Path) -> list[Path]:
    """Resolve target into a list of problem directories/files.

    Handles:
      - A single originals dir  (has meta.json)
      - A parent dir containing multiple originals dirs
      - A scans-style dir       (has problems/ subdir)
    """
    results: list[Path] = []

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
    """Detect whether this is 'originals' or 'scans' layout."""
    if (problem_dir / "meta.json").exists():
        return "originals"
    if (problem_dir / "problems").is_dir():
        return "scans"
    return "unknown"


# ------------------------------------------------------------------
# Originals layout helpers
# ------------------------------------------------------------------

def _regen_tikz_originals(problem_dir: Path, subject: str, console) -> bool:
    """Regenerate only the TikZ diagram for an originals-style problem."""
    from vbagent.pipeline.combine import _generate_tikz, _insert_tikz_into_latex

    problem_path = problem_dir / "problem.tex"
    meta_path = problem_dir / "meta.json"

    if not problem_path.exists():
        console.print(f"  [yellow]No problem.tex in {problem_dir.name}[/yellow]")
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

    console.print(f"  [green]✓[/green] TikZ regenerated ({elapsed:.1f}s)")
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
        console.print(f"  [green]✓[/green] Full regeneration ({elapsed:.1f}s)")
        return True
    else:
        console.print(f"  [yellow]Regeneration returned no result[/yellow]")
        return False


# ------------------------------------------------------------------
# Scans layout helpers
# ------------------------------------------------------------------

def _regen_tikz_scans(scans_dir: Path, items: list[str], subject: str, console) -> int:
    """Regenerate TikZ for scans-style problems."""
    from vbagent.pipeline.combine import _generate_tikz, _insert_tikz_into_latex

    problems_dir = scans_dir / "problems"
    tikz_dir = scans_dir / "tikz"
    tikz_dir.mkdir(exist_ok=True)

    count = 0
    for tex_file in sorted(problems_dir.glob("*.tex")):
        name = tex_file.stem
        if items and name not in items:
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

            console.print(f"  [green]✓[/green] TikZ regenerated ({elapsed:.1f}s)")
            count += 1
        else:
            console.print(f"  [yellow]TikZ generation returned empty[/yellow]")

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
                console.print(f"  [green]✓[/green] Full regeneration ({elapsed:.1f}s)")
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
# CLI command
# ------------------------------------------------------------------

@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("target", type=click.Path(exists=True))
@click.option("--tikz-only", is_flag=True, help="Regenerate only the TikZ diagram")
@click.option("--full", "full_regen", is_flag=True, help="Regenerate everything (problem + solution + diagram)")
@click.option("--item", multiple=True, help="Specific problem names to regenerate (scans mode)")
@click.option("--subject", default=None, help="Subject override")
@click.option("-v", "--verbose", is_flag=True)
def regenerate(target, tikz_only, full_regen, item, subject, verbose):
    """Regenerate diagrams or full content for existing problems.

    \b
    TARGET is a path to:
      - A single problem dir   (has meta.json or problem.tex)
      - A parent dir           (contains multiple problem dirs)
      - A scans output dir     (has problems/ subdir)

    \b
    Modes:
      --tikz-only    Re-run only the TikZ agent (keeps problem/solution text)
      --full         Re-generate everything from scratch using meta.json

    \b
    Default (no flag) = --tikz-only

    \b
    Examples:
      vbagent regenerate agentic/generated/originals/physics/magnetism/VBP-PHY-MAG-001-algebra_vectors --tikz-only
      vbagent regenerate agentic/generated/originals/physics/magnetism/ --tikz-only
      vbagent regenerate agentic/generated/originals/ --tikz-only
      vbagent regenerate agentic/generated/scans/ --tikz-only
      vbagent regenerate agentic/generated/scans/ --tikz-only --item problem_1 --item problem_6
      vbagent regenerate agentic/generated/originals/physics/magnetism/VBP-PHY-MAG-001-algebra_vectors --full
    """
    from vbagent.config import get_config

    console = _get_console()
    target_path = Path(target)

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

        if layout == "originals":
            console.print(f"\n[bold]{pdir.name}[/bold]")
            total_count += 1
            if tikz_only:
                if _regen_tikz_originals(pdir, subject, console):
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
                success_count += _regen_tikz_scans(pdir, items_list, subject, console)
            else:
                success_count += _regen_full_scans(pdir, items_list, subject, console)

        else:
            console.print(f"  [yellow]Unknown layout for {pdir}[/yellow]")

    elapsed = time.time() - t0
    mode_label = "TikZ" if tikz_only else "full"
    console.print(f"\n[bold green]Regenerated {success_count}/{total_count} problems[/bold green] ({mode_label}, {elapsed:.1f}s)")
