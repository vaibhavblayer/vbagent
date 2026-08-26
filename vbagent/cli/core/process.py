"""CLI command for full pipeline processing.

Thin CLI wrapper that delegates to vbagent.pipeline for actual processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

# Re-export everything that other modules import from here.
# Canonical implementations live in vbagent.pipeline.io and vbagent.pipeline.runner.
from vbagent.pipeline.io import (
    merge_metadata_into_latex as merge_metadata_into_latex,
    convert_primary_to_classification as convert_primary_to_classification,
    extract_items_from_tex,
    filter_items_by_range,
    get_base_name,
    insert_tikz_into_latex as insert_tikz_into_latex,
    generate_image_paths_from_range,
    generate_context_file as _generate_context_file,
    save_pipeline_result_organized,
    save_pipeline_result as save_pipeline_result,
)
from vbagent.pipeline.runner import (
    process_image,
    process_tex_item,
    generate_alternate_solution as generate_alternate_solution,
)
from vbagent.cli.common import (
    format_latex as format_latex,
    extract_problem_solution as extract_problem_solution,
    _get_console,
    configure_cli_verbosity,
)
from vbagent.tex import parse_tex_file


def _parse_parallel(value: str, image_count: int) -> int:
    """Parse --parallel value: integer or 'auto'."""
    if value.strip().lower() == "auto":
        return min(image_count, 5)
    try:
        n = int(value)
        return min(max(1, n), image_count, 20)
    except ValueError:
        return 1


def _process_images_parallel(
    image_paths: list[str],
    variant_types: list[str],
    generate_alternate: bool,
    generate_ideas: bool,
    use_context: bool,
    output_dir: str,
    num_workers: int,
    console,
    assess_difficulty: bool,
    merge_metadata: bool,
    use_cache: bool,
    solve: bool,
    do_compile: bool,
    verbose_compile: bool,
    verbose: bool,
) -> tuple[list, int]:
    """Process multiple images in parallel using ThreadPoolExecutor.

    Features:
    - Quiet mode: suppresses per-image console output to avoid garbled output
    - Per-image progress tracking with worker assignment
    - API rate limiting via semaphore (max 6 concurrent API calls)
    - Time tracking per image
    - Summary table at the end
    """
    import concurrent.futures
    import threading
    import time
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.table import Table

    results_by_index: dict[int, object] = {}
    output_path = Path(output_dir)
    lock = threading.Lock()
    worker_labels: dict[str, int] = {}
    # Track per-image results for summary
    image_results: list[dict] = []
    def process_single_image(img_path: str):
        t0 = time.time()
        thread_name = threading.current_thread().name
        with lock:
            if thread_name not in worker_labels:
                worker_labels[thread_name] = len(worker_labels) + 1
            worker_id = worker_labels[thread_name]
        try:
            # Verbose mode intentionally enables synchronized per-agent logs.
            result = process_image(
                image_path=img_path,
                variant_types=variant_types,
                generate_alternate=generate_alternate,
                generate_ideas=generate_ideas,
                use_context=use_context,
                assess_difficulty=assess_difficulty,
                merge_metadata=merge_metadata,
                use_cache=use_cache,
                use_orchestrator=solve,
                generate_solution=solve,
                quiet=not verbose,
            )
            if do_compile:
                from vbagent.compile import compile_and_retry
                from vbagent.agents.quality.latex_fixer import fix_latex
                from vbagent.config import get_config as _get_cfg
                _subj = _get_cfg().subject
                result.latex, _ = compile_and_retry(
                    result.latex, retry_fn=fix_latex, subject=_subj, console=None, verbose=verbose_compile,
                )
                if result.tikz_code:
                    result.tikz_code, _ = compile_and_retry(
                        result.tikz_code, retry_fn=fix_latex, subject=_subj, console=None, verbose=verbose_compile,
                    )
            base_name = get_base_name(result.source_path)
            save_pipeline_result_organized(result, output_path, base_name)
            elapsed = time.time() - t0
            return (img_path, result, None, elapsed, worker_id)
        except Exception as e:
            elapsed = time.time() - t0
            return (img_path, None, str(e), elapsed, worker_id)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]Processing {len(image_paths)} images ({num_workers} workers)...",
            total=len(image_paths),
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Assign worker IDs round-robin
            future_to_info = {}
            for idx, p in enumerate(image_paths):
                future = executor.submit(process_single_image, p)
                future_to_info[future] = (idx, p)

            for future in concurrent.futures.as_completed(future_to_info):
                image_index, img_path = future_to_info[future]
                img_name = Path(img_path).name
                try:
                    path, result, error, elapsed, wid = future.result()
                    if error:
                        with lock:
                            image_results.append({
                                "name": img_name, "status": "failed",
                                "time": elapsed, "error": error, "worker": wid,
                                "index": image_index,
                            })
                        progress.update(task, advance=1, description=f"[red]ERROR {img_name}[/red]")
                    else:
                        with lock:
                            results_by_index[image_index] = result
                            image_results.append({
                                "name": img_name, "status": "success",
                                "time": elapsed, "error": None, "worker": wid,
                                "index": image_index,
                            })
                        progress.update(task, advance=1, description=f"[green]OK {img_name}[/green]")
                except Exception as e:
                    with lock:
                        image_results.append({
                            "name": img_name, "status": "failed",
                            "time": 0, "error": str(e), "worker": None,
                            "index": image_index,
                        })
                    progress.update(task, advance=1, description=f"[red]ERROR {img_name}[/red]")

    # Print summary table
    image_results.sort(key=lambda item: item["index"])
    results = [results_by_index[index] for index in sorted(results_by_index)]
    failed_count = sum(1 for r in image_results if r["status"] == "failed")
    success_count = len(image_results) - failed_count

    if len(image_results) > 1:
        table = Table(title="Processing Summary", show_lines=False)
        table.add_column("Image", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Time", justify="right")
        table.add_column("Worker", justify="center", style="dim")

        for r in image_results:
            status = "[green]OK[/green]" if r["status"] == "success" else f"[red]ERROR[/red] {r.get('error', '')[:50]}"
            time_str = f"{r['time']:.1f}s"
            worker = f"W{r['worker']}" if r["worker"] is not None else "-"
            table.add_row(r["name"], status, time_str, worker)

        total_time = sum(r["time"] for r in image_results)
        table.add_section()
        table.add_row(
            f"[bold]{len(image_results)} total[/bold]",
            f"[green]{success_count} OK[/green] [red]{failed_count} ERROR[/red]",
            f"{total_time:.1f}s",
            "",
        )
        console.print()
        console.print(table)

    return results, failed_count


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-i", "--input", "input_path", type=click.Path(exists=True), help="Input file path (image or tex file)")
@click.option("--from", "from_index", type=int, default=None, help="Start index (1-based, inclusive)")
@click.option("--to", "to_index", type=int, default=None, help="End index (1-based, inclusive)")
@click.option("--item", type=int, default=None, help="Process single item (shorthand for --from N --to N)")
@click.option("--variants", "variant_types_str", type=str, default=None, help="Variant types (comma-separated: numerical,context,conceptual,calculus,cross_topic)")
@click.option(
    "--alternate/--no-alternate",
    default=False,
    help="Allow alternate generation when the solution agent recommends it",
)
@click.option("--ideas/--no-ideas", default=False, help="Extract key concepts and ideas")
@click.option("--ref", "ref_dirs", multiple=True, type=click.Path(exists=True), help="Reference directories for TikZ generation")
@click.option("-o", "--output", type=click.Path(), default="agentic", help="Output directory [default: agentic]")
@click.option("--context/--no-context", default=True, help="Use reference context [default: on]")
@click.option(
    "-p",
    "--parallel",
    type=str,
    default="1",
    help="Workers for image/TeX batches or 'auto' [default: 1, max: 20]",
)
@click.option("-c", "--compile", "do_compile", is_flag=True, help="Compile generated LaTeX to validate")
@click.option("--verbose-compile", "verbose_compile", is_flag=True, help="Show full LaTeX document before each compile")
@click.option("--assess-difficulty/--no-assess-difficulty", "assess_difficulty", default=False, help="Assess difficulty [default: off]")
@click.option("--solve/--no-solve", "solve", default=True, help="Generate solution [default: on]")
@click.option("--merge-metadata/--no-merge-metadata", "merge_metadata", default=False, help="Merge classification metadata into .tex [default: off]")
@click.option("--no-cache", is_flag=True, help="Disable pipeline cache")
@click.option("--clear-cache", is_flag=True, help="Clear pipeline cache before processing")
@click.option("--animate", is_flag=True, help="Generate Manim animations for suitable problems")
@click.option(
    "-v/-q",
    "--verbose/--quiet",
    "verbose",
    default=True,
    callback=configure_cli_verbosity,
    help="Show API profile, token, cache, and processing details [default: verbose]",
)
def run(
    input_path: Optional[str],
    from_index: Optional[int],
    to_index: Optional[int],
    item: Optional[int],
    variant_types_str: Optional[str],
    alternate: bool,
    ideas: bool,
    ref_dirs: tuple[str, ...],
    output: str,
    context: bool,
    parallel: str,
    do_compile: bool,
    verbose_compile: bool,
    assess_difficulty: bool,
    solve: bool,
    merge_metadata: bool,
    no_cache: bool,
    clear_cache: bool,
    animate: bool,
    verbose: bool,
):
    """Full pipeline: Classify → Scan → TikZ → Solve.

    Processes question images through the canonical pipeline with solution
    generation enabled by default. Use --no-solve to skip solutions.

    \b
    Pipeline:
        1. Unified Classification — subject + type + diagram (1 API call)
        2. Problem Orchestrator — scan ∥ TikZ (parallel, deterministic)
        3. Solution Orchestrator — subject agent → diagram dispatch → stitch
        4. Ideas — Extract key concepts (--ideas)
        5. Alternates — Generate recommended alternates (--alternate)
        6. Variants — Generate problem variants (--variants)

    \b
    Examples:
        vbagent run -i question.png
        vbagent run -i question.png --no-solve
        vbagent run -i question.png --ideas --alternate
        vbagent run -i question.png --variants numerical,context
        vbagent run -i question.png --from 1 --to 5
        vbagent run -i question.png --item 3
        vbagent run -i question.png -p 4 -c
        vbagent run -i problems.tex --from 1 --to 5 -p 4

    \b
    See Also:
        vbagent scan --help       Extract LaTeX only (no solution)
        vbagent classify --help   Classify only
        vbagent batch --help      Batch processing with resume
    """
    from vbagent.references.store import ReferenceStore
    from vbagent.cache import PipelineCache

    console = _get_console()

    # Handle --item shorthand
    if item:
        from_index = to_index = item
    if from_index and to_index and from_index > to_index:
        console.print("[red]Error:[/red] --from must be <= --to")
        raise SystemExit(1)

    item_range = None
    if from_index or to_index:
        item_range = (from_index or 1, to_index or 999999)

    # Determine input type
    image = None
    tex = None
    if input_path:
        input_file = Path(input_path)
        if input_file.suffix.lower() in ['.tex', '.txt']:
            tex = input_path
        else:
            image = input_path
        if verbose:
            console.print(f"[dim]Input: {input_path} (Type: {'TeX' if tex else 'Image'})[/dim]")

    # Handle cache flags
    use_cache = not no_cache
    if clear_cache:
        PipelineCache().clear()
        console.print("[yellow]OK[/yellow] Pipeline cache cleared")
        if not input_path:
            return

    # Parse variant types
    valid_variants = {"numerical", "context", "conceptual", "calculus", "cross_topic"}
    variant_types: list[str] = []
    if variant_types_str:
        for v in variant_types_str.replace(" ", "").split(","):
            if v and v in valid_variants:
                variant_types.append(v)
            elif v:
                console.print(f"[yellow]Warning:[/yellow] Unknown variant type '{v}', skipping")

    if not input_path:
        console.print("[red]Error:[/red] --input is required")
        raise SystemExit(1)

    try:
        # Initialize reference store
        if ref_dirs:
            store = ReferenceStore.get_instance(directories=list(ref_dirs))
            with console.status("[bold blue]Indexing reference files..."):
                indexed_count = store.index_files()
            console.print(f"[dim]Indexed {indexed_count} reference files[/dim]")

        results = []
        result_output_names: dict[int, str] = {}

        if image:
            results, failed_count = _process_image_input(
                image, item_range, variant_types, alternate, ideas, context, output,
                parallel, do_compile, verbose_compile, assess_difficulty,
                merge_metadata, use_cache, solve, console, verbose,
            )
        elif tex:
            tex_result_records, failed_count = _process_tex_input(
                tex, item_range, variant_types, alternate, ideas, context,
                do_compile, verbose_compile, console, parallel,
            )
            results = [result for _, result in tex_result_records]
            source_stem = get_base_name(tex)
            for item_number, result in tex_result_records:
                suffix = f"_item_{item_number}" if len(tex_result_records) > 1 else ""
                result_output_names[id(result)] = f"{source_stem}{suffix}"

            # Save TeX results with item-specific names so multiple items do
            # not overwrite one another in the organized output tree.
            output_path = Path(output)
            if tex_result_records:
                console.print(f"\n[cyan]Saving results to:[/cyan] {output_path}/")
                for _, result in tex_result_records:
                    base_name = result_output_names[id(result)]
                    saved = save_pipeline_result_organized(result, output_path, base_name)
                    console.print(f"\n[green]Saved {base_name}:[/green]")
                    for file_type, file_path in saved.items():
                        console.print(f"  • {file_type}: {file_path}")

        # Generate CONTEXT.md
        output_path = Path(output)
        if results:
            _generate_context_file(output_path, len(results))
            console.print("\n[dim]Generated CONTEXT.md for external AI agents[/dim]")

        # Animation step (if --animate)
        if animate and results:
            console.print(f"\n[cyan]Running animation pipeline for {len(results)} result(s)...[/cyan]")
            from vbagent.agents.animation.assessor import assess_animation
            from vbagent.agents.animation.coder import generate_animation

            anim_dir = Path(output) / "animations"
            anim_dir.mkdir(parents=True, exist_ok=True)
            anim_count = 0

            for result in results:
                base_name = result_output_names.get(
                    id(result), get_base_name(result.source_path)
                )
                console.print(f"\n[dim]  Assessing {base_name}...[/dim]")

                # Use image if available, otherwise use scanned LaTeX
                img = result.source_path if Path(result.source_path).suffix in ('.png', '.jpg', '.jpeg', '.webp', '.gif') else None
                problem_tex = result.latex or ""
                solution_tex = ""
                if hasattr(result, 'solution_latex') and result.solution_latex:
                    solution_tex = result.solution_latex

                try:
                    assessment = assess_animation(
                        problem_latex=problem_tex,
                        image_path=img,
                        solution_latex=solution_tex,
                        show_spinner=True,
                    )

                    if not assessment.should_animate:
                        console.print(f"  [yellow]Skip {base_name}[/yellow] — {assessment.reason[:80]}")
                        continue

                    console.print(f"  [green]Animating {base_name}[/green] — {assessment.mode}: {assessment.animation_type}")

                    code_result = generate_animation(
                        assessment=assessment,
                        problem_latex=problem_tex,
                        image_path=img,
                        solution_latex=solution_tex,
                        show_spinner=True,
                    )

                    out_file = anim_dir / f"{base_name}.py"
                    out_file.write_text(code_result.code, encoding="utf-8")
                    console.print(f"  [cyan]→ {out_file}[/cyan]")
                    anim_count += 1
                except Exception as e:
                    console.print(f"  [red]Animation failed for {base_name}: {e}[/red]")

            console.print(f"\n[green]OK Generated {anim_count} animation(s) in {anim_dir}[/green]")

        # Summary
        console.print("\n[bold green]Pipeline complete![/bold green]")
        if image:
            total = len(generate_image_paths_from_range(image, item_range)) if item_range else 1
            console.print(f"Processed {len(results)}/{total} image(s) successfully")
            if failed_count > 0:
                console.print(f"[yellow]Failed: {failed_count} image(s)[/yellow]")
        else:
            console.print(f"Processed {len(results)} item(s)")

        if failed_count > 0:
            raise SystemExit(1)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Pipeline failed:[/red] {e}")
        raise SystemExit(1)


def _process_image_input(
    image, item_range, variant_types, alternate, ideas, context, output,
    parallel, do_compile, verbose_compile, assess_difficulty,
    merge_metadata, use_cache, solve, console, verbose=False,
):
    """Handle image input processing (single or batch)."""
    results = []
    failed_count = 0

    if item_range:
        image_paths = generate_image_paths_from_range(image, item_range)
        if not image_paths:
            console.print("[red]Error:[/red] No images found in specified range")
            raise SystemExit(1)
        console.print(f"[cyan]Processing {len(image_paths)} image(s) in range {item_range[0]}-{item_range[1]}...[/cyan]")
    else:
        image_paths = [image]

    num_workers = _parse_parallel(parallel, len(image_paths))
    if num_workers > 1 and len(image_paths) > 1:
        console.print(f"[cyan]Using {num_workers} parallel workers[/cyan]")
        results, failed_count = _process_images_parallel(
            image_paths=image_paths, variant_types=variant_types,
            generate_alternate=alternate, generate_ideas=ideas,
            use_context=context, output_dir=output, num_workers=num_workers,
            console=console, assess_difficulty=assess_difficulty,
            merge_metadata=merge_metadata, use_cache=use_cache,
            solve=solve, do_compile=do_compile,
            verbose_compile=verbose_compile,
            verbose=verbose,
        )
    else:
        for idx, img_path in enumerate(image_paths, 1):
            if len(image_paths) > 1:
                console.print(f"\n[bold]Image {idx}/{len(image_paths)}: {Path(img_path).name}[/bold]")
            try:
                result = process_image(
                    image_path=img_path, variant_types=variant_types,
                    generate_alternate=alternate, generate_ideas=ideas,
                    use_context=context, assess_difficulty=assess_difficulty,
                    merge_metadata=merge_metadata, use_cache=use_cache,
                    use_orchestrator=solve, generate_solution=solve,
                )
                if do_compile:
                    from vbagent.compile import compile_and_retry
                    from vbagent.agents.quality.latex_fixer import fix_latex
                    from vbagent.config import get_config as _get_cfg
                    _subj = _get_cfg().subject
                    console.print("[dim]  → Compiling scanned LaTeX...[/dim]")
                    result.latex, _ = compile_and_retry(
                        result.latex, retry_fn=fix_latex, subject=_subj, console=console, verbose=verbose_compile,
                    )
                    if result.tikz_code:
                        console.print("[dim]  → Compiling TikZ...[/dim]")
                        result.tikz_code, _ = compile_and_retry(
                            result.tikz_code, retry_fn=fix_latex, subject=_subj, console=console, verbose=verbose_compile,
                        )
                results.append(result)
                output_path = Path(output)
                base_name = get_base_name(result.source_path)
                save_pipeline_result_organized(result, output_path, base_name)
                console.print(f"[green]OK Saved {base_name}[/green]")
            except Exception as e:
                console.print(f"[red]ERROR Failed {Path(img_path).name}: {e}[/red]")
                failed_count += 1

    return results, failed_count


def _process_tex_input(
    tex, item_range, variant_types, alternate, ideas, context,
    do_compile, verbose_compile, console, parallel="1",
):
    """Handle TeX file input processing, optionally in parallel.

    Returns ``(item_number, result)`` pairs so callers can preserve source
    item order and give each item a unique output name.
    """
    content = parse_tex_file(tex)
    all_items = extract_items_from_tex(content)

    if all_items:
        if item_range:
            start, end = item_range
            selected_items = [
                (item_number, item)
                for item_number, item in enumerate(all_items, 1)
                if start <= item_number <= end
            ]
        else:
            selected_items = list(enumerate(all_items, 1))
    else:
        selected_items = [(1, content)]

    if not selected_items:
        return [], 0

    console.print(f"[cyan]Processing {len(selected_items)} item(s)...[/cyan]")
    num_workers = _parse_parallel(parallel, len(selected_items))
    if num_workers > 1 and len(selected_items) > 1:
        console.print(f"[cyan]Using {num_workers} parallel workers[/cyan]")

    def process_one(item_number, tex_item):
        result = process_tex_item(
            tex_content=tex_item, source_path=tex,
            variant_types=variant_types, generate_alternate=alternate,
            generate_ideas=ideas, use_context=context,
        )
        if do_compile:
            _compile_result(result, console, verbose_compile)
        return item_number, result

    completed: dict[int, object] = {}
    failures: list[tuple[int, str]] = []

    if num_workers > 1 and len(selected_items) > 1:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(process_one, item_number, tex_item): item_number
                for item_number, tex_item in selected_items
            }
            for future in concurrent.futures.as_completed(futures):
                item_number = futures[future]
                try:
                    completed[item_number] = future.result()[1]
                    console.print(f"[green]OK Item {item_number}[/green]")
                except Exception as exc:
                    failures.append((item_number, str(exc)))
                    console.print(f"[red]ERROR Item {item_number}: {exc}[/red]")
    else:
        for item_number, tex_item in selected_items:
            console.print(f"\n[bold]Item {item_number}/{len(all_items) or 1}[/bold]")
            try:
                completed[item_number] = process_one(item_number, tex_item)[1]
            except Exception as exc:
                failures.append((item_number, str(exc)))
                console.print(f"[red]ERROR Item {item_number}: {exc}[/red]")

    records = [
        (item_number, completed[item_number])
        for item_number, _ in selected_items
        if item_number in completed
    ]
    return records, len(failures)


def _compile_result(result, console, verbose_compile):
    """Compile and validate a pipeline result's LaTeX."""
    from vbagent.compile import compile_and_retry
    from vbagent.agents.quality.latex_fixer import fix_latex
    from vbagent.config import get_config as _get_cfg

    _subj = _get_cfg().subject
    console.print("[dim]  → Compiling scanned LaTeX...[/dim]")
    result.latex, _ = compile_and_retry(
        result.latex, retry_fn=fix_latex, subject=_subj, console=console, verbose=verbose_compile,
    )
    if result.tikz_code:
        console.print("[dim]  → Compiling TikZ...[/dim]")
        result.tikz_code, _ = compile_and_retry(
            result.tikz_code, retry_fn=fix_latex, subject=_subj, console=console, verbose=verbose_compile,
        )
