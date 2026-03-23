"""CLI command for generating problems from ideas, sketches, or topics.

Unified generation command that handles all input modes:
- Sketch images (-i sketch.png)
- Existing ideas (--from-ideas agentic/ideas/)
- Topic strings (--topic "Electromagnetic Induction")
- Ranges for batch processing (--from 1 --to 5)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import click

from vbagent.cli.common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _slugify(text: str) -> str:
    """Turn a topic string into a safe filename slug."""
    s = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s-]+", "_", s)[:60] or "topic"


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-i", "--input", "image_path", type=click.Path(), default=None,
              help="Sketch/scribble image path (supports --from/--to for ranges)")
@click.option("--from", "from_index", type=int, default=None,
              help="Start index for range (1-based)")
@click.option("--to", "to_index", type=int, default=None,
              help="End index for range (1-based)")
@click.option("--item", type=int, default=None,
              help="Single item (shorthand for --from N --to N)")
@click.option("--from-ideas", "ideas_dir", type=click.Path(exists=True), default=None,
              help="Directory with ideas/*.json files")
@click.option("--from-scans", "scans_dir", type=click.Path(exists=True), default=None,
              help="Directory with scans/*.tex (extracts \\begin{idea} blocks)")
@click.option("-t", "--topic", default=None, help="Topic for generation")
@click.option("--idea", default=None, help="Specific idea description")
@click.option("--type", "question_type", default="subjective",
              type=click.Choice(["mcq_sc", "mcq_mc", "subjective", "integer",
                                 "passage", "match", "assertion_reason"]),
              help="Question type [default: subjective]")
@click.option("-d", "--difficulty", default="medium",
              type=click.Choice(["easy", "medium", "hard"]),
              help="Difficulty [default: medium]")
@click.option("-c", "--count", default=1, type=int,
              help="Number of problems to generate per input [default: 1]")
@click.option("--solve/--no-solve", default=True,
              help="Generate solution [default: on]")
@click.option("--diagram/--no-diagram", default=True,
              help="Generate TikZ diagram [default: on]")
@click.option("-o", "--output", default="agentic/generated",
              help="Output directory [default: agentic/generated]")
@click.option("--no-cache", "no_cache", is_flag=True,
              help="Skip cache — always re-generate even if cached")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def generate(
    image_path, from_index, to_index, item,
    ideas_dir, scans_dir,
    topic, idea, question_type, difficulty, count,
    solve, diagram, output, no_cache, verbose,
):
    """Generate problems from sketches, ideas, or topics.

    \b
    Input Modes:
        -i sketch.png                      From a handwritten sketch image
        -i sketch_1.png --from 1 --to 5   Batch sketch processing
        --from-ideas agentic/ideas/        From extracted idea JSONs
        --from-scans agentic/scans/        From idea blocks in scans
        --from-scans agentic/scans/ --from 1 --to 5   Range filter
        --topic "RC circuits"              From a topic string

    \b
    Output Structure (mirrors `run` command):
        agentic/generated/
        ├── scans/                   # --from-scans mode
        │   ├── problems/problem_1.tex
        │   ├── tikz/problem_1.tex
        │   ├── generation/problem_1.json
        │   └── llm_calls/problem_1/
        ├── ideas/                   # --from-ideas mode
        │   ├── problems/idea_1.tex
        │   └── ...
        ├── sketches/                # -i mode
        │   ├── problems/sketch_1.tex
        │   └── ...
        ├── topics/                  # --topic mode
        │   ├── problems/rc_circuits.tex
        │   └── ...
        └── generation_cache.json    # Cache index

    \b
    Examples:
        vbagent generate -i sketch.png
        vbagent generate -i sketch_1.png --from 1 --to 5
        vbagent generate --from-ideas agentic/ideas/ --type mcq_sc
        vbagent generate --from-scans agentic/scans/ --difficulty hard
        vbagent generate --from-scans agentic/scans/ --from 1 --to 5
        vbagent generate --topic "Electromagnetic Induction" --type integer
        vbagent generate --topic "SHM" --idea "spring-mass on incline" -c 3
        vbagent generate --from-scans agentic/scans/ --no-cache
    """
    from vbagent.pipeline.generate import (
        GenerationResult,
        generate_from_sketch,
        generate_from_ideas_dir,
        generate_from_topic,
        _save_generation,
    )
    from vbagent.pipeline.io import generate_image_paths_from_range
    from vbagent.config import get_config

    console = _get_console()
    output_base = Path(output)

    # Handle --item shorthand
    if item:
        from_index = to_index = item
    if from_index and to_index and from_index > to_index:
        console.print("[red]Error:[/red] --from must be <= --to")
        raise SystemExit(1)

    item_range = None
    if from_index or to_index:
        item_range = (from_index or 1, to_index or 999999)

    # Validate: at least one input mode
    if not image_path and not ideas_dir and not scans_dir and not topic:
        console.print("[red]Error:[/red] Provide at least one of: -i, --from-ideas, --from-scans, or --topic")
        raise SystemExit(1)

    # Determine source-mode subdir
    if image_path:
        source_mode = "sketches"
    elif scans_dir:
        source_mode = "scans"
    elif ideas_dir:
        source_mode = "ideas"
    else:
        source_mode = "topics"

    mode_dir = output_base / source_mode

    # Clear generation output if --no-cache (forces re-generation)
    if no_cache:
        problems_dir = mode_dir / "problems"
        if problems_dir.exists():
            import shutil
            shutil.rmtree(problems_dir)
            console.print("[yellow]Cache cleared — will re-generate all[/yellow]")

    all_results: list[GenerationResult] = []
    t0 = time.time()

    try:
        # Mode 1: Sketch images
        if image_path:
            if item_range:
                image_paths = generate_image_paths_from_range(image_path, item_range)
            else:
                p = Path(image_path)
                if not p.exists():
                    console.print(f"[red]Error:[/red] Image not found: {image_path}")
                    raise SystemExit(1)
                image_paths = [image_path]

            console.print(f"[cyan]Generating from {len(image_paths)} sketch(es)...[/cyan]")

            for idx, img in enumerate(image_paths):
                img_name = Path(img).stem  # e.g. sketch_1
                for c in range(count):
                    base_name = img_name if count == 1 else f"{img_name}_v{c+1}"
                    console.print(f"\n[bold]{base_name}" +
                                  (f" ({c+1}/{count})" if count > 1 else "") + "[/bold]")

                    t_start = time.time()
                    problem_tex, solution_tex, tikz_code, sketch_dict, idea_tex = generate_from_sketch(
                        image_path=img,
                        question_type=question_type,
                        difficulty=difficulty,
                        topic_hint=topic or "",
                        with_solution=solve,
                        with_diagram=diagram,
                        output_dir=mode_dir,
                        base_name=base_name,
                        console=console,
                    )

                    result = GenerationResult(
                        base_name=base_name, output_dir=mode_dir,
                        problem_tex=problem_tex, solution_tex=solution_tex,
                        tikz_code=tikz_code, idea_latex=idea_tex,
                        sketch_analysis=sketch_dict,
                        generation_meta={"image": img, "question_type": question_type,
                                         "difficulty": difficulty},
                        source="sketch", elapsed=time.time() - t_start,
                    )
                    saved = _save_generation(result)
                    all_results.append(result)
                    console.print(f"  [green]✓[/green] {saved.get('problem', base_name)}")

        # Mode 2: From ideas / scans directory
        elif ideas_dir or scans_dir:
            ideas_path = Path(ideas_dir) if ideas_dir else None
            scans_path = Path(scans_dir) if scans_dir else None

            gen_results = generate_from_ideas_dir(
                ideas_dir=ideas_path or Path("agentic/ideas"),
                scans_dir=scans_path,
                question_type=question_type,
                difficulty=difficulty,
                topic=topic or "",
                with_solution=solve,
                with_diagram=diagram,
                item_range=item_range,
                output_base=mode_dir,
                console=console,
            )

            for problem_tex, solution_tex, tikz_code, meta, idea_latex in gen_results:
                base_name = meta.get("base_name", "problem")

                result = GenerationResult(
                    base_name=base_name, output_dir=mode_dir,
                    problem_tex=problem_tex, solution_tex=solution_tex,
                    tikz_code=tikz_code, idea_latex=idea_latex,
                    generation_meta={**meta, "question_type": question_type,
                                     "difficulty": difficulty},
                    source=source_mode,
                )
                if not meta.get("cached"):
                    saved = _save_generation(result)
                all_results.append(result)
                if meta.get("cached"):
                    console.print(f"  [green]✓[/green] {base_name} (cached)")
                else:
                    console.print(f"  [green]✓[/green] {base_name}")

        # Mode 3: From topic
        elif topic:
            for c in range(count):
                slug = _slugify(topic)
                base_name = slug if count == 1 else f"{slug}_{c+1}"
                console.print(f"\n[bold]{base_name}" +
                              (f" ({c+1}/{count})" if count > 1 else "") + "[/bold]")

                t_start = time.time()
                problem_tex, solution_tex, tikz_code, meta, idea_latex = generate_from_topic(
                    topic=topic,
                    question_type=question_type,
                    difficulty=difficulty,
                    idea=idea or "",
                    with_solution=solve,
                    with_diagram=diagram,
                    output_dir=mode_dir,
                    base_name=base_name,
                    console=console,
                )

                result = GenerationResult(
                    base_name=base_name, output_dir=mode_dir,
                    problem_tex=problem_tex, solution_tex=solution_tex,
                    tikz_code=tikz_code, idea_latex=idea_latex,
                    generation_meta={**meta, "question_type": question_type,
                                     "difficulty": difficulty},
                    source="topic", elapsed=time.time() - t_start,
                )
                if not meta.get("cached"):
                    saved = _save_generation(result)
                all_results.append(result)
                if meta.get("cached"):
                    console.print(f"  [green]✓[/green] {base_name} (cached)")
                else:
                    console.print(f"  [green]✓[/green] {base_name}")

        # Save manifest
        if all_results:
            manifest = {
                "total_generated": len(all_results),
                "output_dir": str(mode_dir),
                "source_mode": source_mode,
                "subject": get_config().subject,
                "entries": [
                    {
                        "base_name": r.base_name,
                        "source": r.source,
                        "elapsed": round(r.elapsed, 1),
                        "has_tikz": r.tikz_code is not None,
                        "has_solution": bool(r.solution_tex),
                    }
                    for r in all_results
                ],
            }
            manifest_path = mode_dir / "manifest.json"
            mode_dir.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=2))

        # Summary
        total_time = time.time() - t0
        console.print(f"\n[bold green]Generated {len(all_results)} problem(s)[/bold green] in {total_time:.1f}s")
        console.print(f"Output: {mode_dir}/")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Generation failed:[/red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise SystemExit(1)
