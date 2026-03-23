"""Combine pipeline — orchestrates idea selection, combination, TikZ, and saving.

Flow:
  idea_store → pick N ideas → IdeaCombiner agent → TikZ (if needed) → save to originals/
"""

from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Optional

from vbagent.ideas.models import (
    Idea,
    CombinationRecord,
    SUBJECT_CODES,
    TOPIC_CODES,
    parse_difficulty,
)
from vbagent.ideas.store import IdeaStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_primary_topic(ideas: list[Idea]) -> str:
    """Infer the primary topic from a set of ideas (most common topic)."""
    from collections import Counter
    topics = [i.topic for i in ideas if i.topic]
    if not topics:
        return "general"
    return Counter(topics).most_common(1)[0][0]


def _build_output_dir(
    base: Path, subject: str, topic: str, combo_id: str, lens_suffix: str = ""
) -> Path:
    """Build the output directory path.

    Structure: base/originals/{subject}/{topic}/{combo_id}[-{lens}]/
    """
    dirname = combo_id
    if lens_suffix:
        dirname = f"{combo_id}-{lens_suffix}"
    return base / "originals" / subject / topic / dirname


def _insert_tikz_into_latex(problem_tex: str, tikz_code: str) -> str:
    """Insert TikZ code into problem LaTeX.

    Looks for %TIKZ_PLACEHOLDER%, otherwise appends after problem text
    (before \\begin{tasks} if present).
    """
    if not tikz_code:
        return problem_tex

    wrapped = f"\n\\begin{{center}}\n{tikz_code.strip()}\n\\end{{center}}\n"

    if "%TIKZ_PLACEHOLDER%" in problem_tex:
        return problem_tex.replace("%TIKZ_PLACEHOLDER%", wrapped)

    # Insert before \begin{tasks} if present
    tasks_match = re.search(r"\\begin\{tasks\}", problem_tex)
    if tasks_match:
        pos = tasks_match.start()
        return problem_tex[:pos] + wrapped + "\n" + problem_tex[pos:]

    # Append after problem text
    return problem_tex + wrapped


# ---------------------------------------------------------------------------
# Core pipeline functions
# ---------------------------------------------------------------------------

def pick_ideas(
    store: IdeaStore,
    count: int = 5,
    topic: str | None = None,
    lens: str | None = None,
) -> list[Idea]:
    """Pick N candidate ideas from the store.

    Filters by topic and/or lens if provided, then randomly samples.
    Returns more than needed so the combiner agent can choose the best subset.
    """
    pool = store.ideas

    if topic:
        pool = [i for i in pool if i.topic.lower().strip() == topic.lower().strip()]

    if lens:
        pool = [
            i for i in pool
            if lens in i.natural_lenses or lens in i.compatible_lenses
        ]

    if not pool:
        return []

    # Sample up to count ideas
    n = min(count, len(pool))
    return random.sample(pool, n)


def generate_combined_problem(
    store: IdeaStore,
    pick: int = 5,
    lenses: list[str] | None = None,
    difficulty: int = 5,
    question_type: str = "mcq_sc",
    topic: str | None = None,
    concepts_context: str = "",
    with_diagram: bool = True,
    output_base: Path = Path("agentic/generated"),
    subject: str | None = None,
    console: object | None = None,
) -> dict | None:
    """Generate a single combined problem.

    1. Pick N ideas from store
    2. Run IdeaCombiner agent
    3. Generate TikZ if needed
    4. Save to originals/ directory
    5. Log combination

    Returns dict with output paths, or None on failure.
    """
    from vbagent.agents.classification.idea_combiner import combine_ideas, CombinedProblemOutput
    from vbagent.config import get_config

    if subject is None:
        subject = get_config().subject

    _print = _make_printer(console)

    # 1. Pick candidate ideas
    candidates = pick_ideas(store, count=pick, topic=topic, lens=lenses[0] if lenses else None)
    if len(candidates) < 2:
        _print(f"[yellow]Not enough ideas in store (found {len(candidates)}, need ≥2)[/yellow]")
        return None

    idea_ids = [i.id for i in candidates]
    _print(f"  Picked {len(candidates)} candidate ideas: {', '.join(idea_ids)}")

    # 2. Run combiner agent
    t0 = time.time()
    result: CombinedProblemOutput = combine_ideas(
        ideas=candidates,
        lenses=lenses,
        difficulty=difficulty,
        question_type=question_type,
        concepts_context=concepts_context,
        subject=subject,
    )
    elapsed_combine = time.time() - t0
    _print(f"  Combiner: {elapsed_combine:.1f}s")

    if not result.problem_latex:
        _print("[red]Combiner returned empty problem[/red]")
        return None

    # 3. TikZ generation (if needed)
    tikz_code = None
    if with_diagram and result.diagram_description:
        tikz_code = _generate_tikz(result.diagram_description, subject, console)

    # 4. Determine output path
    primary_topic = topic or _infer_primary_topic(candidates)
    lenses_used = result.lenses_applied or lenses or []
    lens_suffix = "_".join(sorted(lenses_used)) if lenses_used else ""

    # Check if this combo already exists
    if store.combo_exists(result.selected_idea_ids, lenses_used):
        _print("[yellow]⚠ This combination already exists (skipping)[/yellow]")
        return None

    combo_id = store._next_combo_id(primary_topic)
    out_dir = _build_output_dir(output_base, subject, primary_topic, combo_id, lens_suffix)

    # 5. Save files
    saved = _save_combined(
        out_dir=out_dir,
        combo_id=combo_id,
        result=result,
        tikz_code=tikz_code,
        candidates=candidates,
        lenses_used=lenses_used,
        difficulty=difficulty,
        question_type=question_type,
        subject=subject,
    )

    # 6. Log combination
    record = CombinationRecord(
        combo_id=combo_id,
        idea_ids=result.selected_idea_ids or idea_ids,
        lenses_used=lenses_used,
        difficulty=difficulty,
        question_type=question_type,
        output_file=str(out_dir / "problem.tex"),
    )
    store.log_combination(record)
    store.save()

    _print(f"  [green]✓[/green] {combo_id}" + (f"-{lens_suffix}" if lens_suffix else ""))
    return saved


def generate_batch(
    store: IdeaStore,
    count: int = 5,
    pick: int = 5,
    lenses: list[str] | None = None,
    all_lenses: bool = False,
    difficulty: int | tuple[int, int] = 5,
    question_type: str = "mcq_sc",
    topic: str | None = None,
    concepts_context: str = "",
    with_diagram: bool = True,
    output_base: Path = Path("agentic/generated"),
    subject: str | None = None,
    console: object | None = None,
) -> list[dict]:
    """Generate multiple combined problems.

    If all_lenses=True or multiple lenses provided, generates one problem
    per lens for each combination.
    """
    _print = _make_printer(console)
    results = []

    # Determine lens sets to generate
    if all_lenses:
        # For each combo, generate all compatible lenses
        lens_sets: list[list[str] | None] = [None]  # placeholder, resolved per combo
    elif lenses and len(lenses) > 1:
        # Generate one problem per lens
        lens_sets = [[l] for l in lenses]
    elif lenses:
        lens_sets = [lenses]
    else:
        lens_sets = [None]

    for i in range(count):
        # Resolve difficulty if it's a range
        if isinstance(difficulty, tuple):
            diff = random.randint(difficulty[0], difficulty[1])
        else:
            diff = difficulty

        _print(f"\n[bold]Combination {i+1}/{count}[/bold] (difficulty {diff}/10)")

        for lens_set in lens_sets:
            result = generate_combined_problem(
                store=store,
                pick=pick,
                lenses=lens_set,
                difficulty=diff,
                question_type=question_type,
                topic=topic,
                concepts_context=concepts_context,
                with_diagram=with_diagram,
                output_base=output_base,
                subject=subject,
                console=console,
            )
            if result:
                results.append(result)

    return results


# ---------------------------------------------------------------------------
# TikZ generation (reuses existing infrastructure)
# ---------------------------------------------------------------------------

def _generate_tikz(
    description: str, subject: str, console: object | None = None
) -> str | None:
    """Generate TikZ code using existing TikZ router."""
    try:
        from vbagent.pipeline.generate import _generate_tikz_for_problem

        # Use a no-op console if none provided
        class _NoopConsole:
            def print(self, *a, **kw): pass

        c = console if console is not None else _NoopConsole()

        return _generate_tikz_for_problem(
            diagram_desc=description,
            subject=subject,
            problem_tex="",
            image_path=None,
            sketch_type=None,
            console=c,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Save combined output
# ---------------------------------------------------------------------------

def _save_combined(
    out_dir: Path,
    combo_id: str,
    result,
    tikz_code: str | None,
    candidates: list[Idea],
    lenses_used: list[str],
    difficulty: int,
    question_type: str,
    subject: str,
) -> dict[str, str]:
    """Save combined problem to the originals/ directory structure."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, str] = {}

    # Problem tex (with TikZ injected)
    problem_tex = result.problem_latex or ""
    if tikz_code:
        problem_tex = _insert_tikz_into_latex(problem_tex, tikz_code)

    # Assemble final: problem → diagram (already injected) → solution → idea
    final_parts = [problem_tex]
    if result.solution_latex:
        final_parts.append(result.solution_latex)
    if result.idea_latex:
        idea_block = f"\\begin{{idea}}\n{result.idea_latex}\n\\end{{idea}}"
        final_parts.append(idea_block)

    final_tex = "\n\n".join(final_parts)
    problem_path = out_dir / "problem.tex"
    problem_path.write_text(final_tex)
    saved["problem"] = str(problem_path)

    # Solution separately
    if result.solution_latex:
        sol_path = out_dir / "solution.tex"
        sol_path.write_text(result.solution_latex)
        saved["solution"] = str(sol_path)

    # TikZ separately
    if tikz_code:
        tikz_dir = out_dir / "tikz"
        tikz_dir.mkdir(exist_ok=True)
        tikz_path = tikz_dir / "diagram.tex"
        tikz_path.write_text(tikz_code)
        saved["tikz"] = str(tikz_path)

    # Meta JSON
    meta = {
        "id": combo_id,
        "subject": subject,
        "topic": _infer_primary_topic(candidates),
        "difficulty": difficulty,
        "difficulty_breakdown": result.difficulty_breakdown if hasattr(result, "difficulty_breakdown") else {},
        "question_type": question_type,
        "lenses": lenses_used,
        "combination_strategy": result.combination_strategy if hasattr(result, "combination_strategy") else "",
        "combination_rationale": result.combination_rationale if hasattr(result, "combination_rationale") else "",
        "selected_idea_ids": result.selected_idea_ids if hasattr(result, "selected_idea_ids") else [],
        "candidate_ideas": [
            {"id": i.id, "text": i.text, "topic": i.topic}
            for i in candidates
        ],
        "generation_metadata": result.generation_metadata if hasattr(result, "generation_metadata") else {},
        "generated_at": __import__("datetime").datetime.now().isoformat(),
    }
    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    saved["meta"] = str(meta_path)

    return saved


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _make_printer(console):
    """Create a print function that works with or without Rich console."""
    if console is not None and hasattr(console, "print"):
        return console.print
    return lambda *a, **kw: None
