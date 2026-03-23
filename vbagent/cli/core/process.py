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
    merge_metadata_into_latex,
    convert_primary_to_classification,
    extract_items_from_tex,
    filter_items_by_range,
    get_base_name,
    insert_tikz_into_latex,
    generate_image_paths_from_range,
    generate_context_file as _generate_context_file,
    save_pipeline_result_organized,
    save_pipeline_result,
)
from vbagent.pipeline.runner import (
    process_image_unified,
    process_tex_item,
    process_generated_problem,
    generate_alternate_solution,
)
from vbagent.cli.common import (
    format_latex,
    extract_problem_solution,
    _get_console,
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

    results = []
    output_path = Path(output_dir)
    lock = threading.Lock()
    # Track per-image results for summary
    image_results: list[dict] = []

    def process_single_image(img_path: str, worker_id: int):
        img_name = Path(img_path).name
        t0 = time.time()
        try:
            # quiet=True suppresses all per-image console output
            result = process_image_unified(
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
                quiet=True,
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
                worker_id = (idx % num_workers) + 1
                future = executor.submit(process_single_image, p, worker_id)
                future_to_info[future] = (p, worker_id)

            for future in concurrent.futures.as_completed(future_to_info):
                img_path, worker_id = future_to_info[future]
                img_name = Path(img_path).name
                try:
                    path, result, error, elapsed, wid = future.result()
                    if error:
                        with lock:
                            image_results.append({
                                "name": img_name, "status": "failed",
                                "time": elapsed, "error": error, "worker": wid,
                            })
                        progress.update(task, advance=1, description=f"[red]✗ {img_name}[/red]")
                    else:
                        with lock:
                            results.append(result)
                            image_results.append({
                                "name": img_name, "status": "success",
                                "time": elapsed, "error": None, "worker": wid,
                            })
                        progress.update(task, advance=1, description=f"[green]✓ {img_name}[/green]")
                except Exception as e:
                    with lock:
                        image_results.append({
                            "name": img_name, "status": "failed",
                            "time": 0, "error": str(e), "worker": worker_id,
                        })
                    progress.update(task, advance=1, description=f"[red]✗ {img_name}[/red]")

    # Print summary table
    failed_count = sum(1 for r in image_results if r["status"] == "failed")
    success_count = len(image_results) - failed_count

    if len(image_results) > 1:
        table = Table(title="Processing Summary", show_lines=False)
        table.add_column("Image", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Time", justify="right")
        table.add_column("Worker", justify="center", style="dim")

        for r in image_results:
            status = "[green]✓[/green]" if r["status"] == "success" else f"[red]✗[/red] {r.get('error', '')[:50]}"
            time_str = f"{r['time']:.1f}s"
            table.add_row(r["name"], status, time_str, f"W{r['worker']}")

        total_time = sum(r["time"] for r in image_results)
        table.add_section()
        table.add_row(
            f"[bold]{len(image_results)} total[/bold]",
            f"[green]{success_count}✓[/green] [red]{failed_count}✗[/red]",
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
@click.option("--alternate/--no-alternate", default=False, help="Generate alternate solutions")
@click.option("--ideas/--no-ideas", default=False, help="Extract key concepts and ideas")
@click.option("--ref", "ref_dirs", multiple=True, type=click.Path(exists=True), help="Reference directories for TikZ generation")
@click.option("-o", "--output", type=click.Path(), default="agentic", help="Output directory [default: agentic]")
@click.option("--context/--no-context", default=True, help="Use reference context [default: on]")
@click.option("-p", "--parallel", type=str, default="1", help="Number of parallel workers or 'auto' [default: 1, max: 20]")
@click.option("-c", "--compile", "do_compile", is_flag=True, help="Compile generated LaTeX to validate")
@click.option("--verbose-compile", "verbose_compile", is_flag=True, help="Show full LaTeX document before each compile")
@click.option("--assess-difficulty/--no-assess-difficulty", "assess_difficulty", default=False, help="Assess difficulty [default: off]")
@click.option("--solve/--no-solve", "solve", default=True, help="Generate solution [default: on]")
@click.option("--merge-metadata/--no-merge-metadata", "merge_metadata", default=True, help="Merge classification metadata [default: on]")
@click.option("--no-cache", is_flag=True, help="Disable pipeline cache")
@click.option("--clear-cache", is_flag=True, help="Clear pipeline cache before processing")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
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
    verbose: bool,
):
    """Full pipeline: Classify → Scan → TikZ → Solve.

    Processes question images through the unified pipeline with solution
    generation enabled by default. Use --no-solve to skip solutions.

    \b
    Pipeline:
        1. Unified Classification — subject + type + diagram (1 API call)
        2. Problem Orchestrator — scan ∥ TikZ (parallel, deterministic)
        3. Solution Orchestrator — subject agent → diagram dispatch → stitch
        4. Ideas — Extract key concepts (--ideas)
        5. Alternates — Generate alternate solutions (--alternate)
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
        vbagent run -i problems.tex --from 1 --to 5

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
        console.print("[yellow]✓[/yellow] Pipeline cache cleared")
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

        if image:
            results, failed_count = _process_image_input(
                image, item_range, variant_types, alternate, ideas, context, output,
                parallel, do_compile, verbose_compile, assess_difficulty,
                merge_metadata, use_cache, solve, console,
            )
        elif tex:
            results, failed_count = _process_tex_input(
                tex, item_range, variant_types, alternate, ideas, context,
                do_compile, verbose_compile, console,
            )
            # Save TeX results
            output_path = Path(output)
            if results:
                console.print(f"\n[cyan]Saving results to:[/cyan] {output_path}/")
                for result in results:
                    base_name = get_base_name(result.source_path)
                    saved = save_pipeline_result_organized(result, output_path, base_name)
                    console.print(f"\n[green]Saved {base_name}:[/green]")
                    for file_type, file_path in saved.items():
                        console.print(f"  • {file_type}: {file_path}")
            failed_count = 0

        # Generate CONTEXT.md
        output_path = Path(output)
        if results:
            _generate_context_file(output_path, len(results))
            console.print(f"\n[dim]Generated CONTEXT.md for external AI agents[/dim]")

        # Summary
        console.print(f"\n[bold green]Pipeline complete![/bold green]")
        if image:
            total = len(generate_image_paths_from_range(image, item_range)) if item_range else 1
            console.print(f"Processed {len(results)}/{total} image(s) successfully")
            if failed_count > 0:
                console.print(f"[yellow]Failed: {failed_count} image(s)[/yellow]")
        else:
            console.print(f"Processed {len(results)} item(s)")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Pipeline failed:[/red] {e}")
        raise SystemExit(1)


def _process_image_input(
    image, item_range, variant_types, alternate, ideas, context, output,
    parallel, do_compile, verbose_compile, assess_difficulty,
    merge_metadata, use_cache, solve, console,
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
        )
    else:
        for idx, img_path in enumerate(image_paths, 1):
            if len(image_paths) > 1:
                console.print(f"\n[bold]Image {idx}/{len(image_paths)}: {Path(img_path).name}[/bold]")
            try:
                result = process_image_unified(
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
                console.print(f"[green]✓ Saved {base_name}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed {Path(img_path).name}: {e}[/red]")
                failed_count += 1

    return results, failed_count


def _process_tex_input(
    tex, item_range, variant_types, alternate, ideas, context,
    do_compile, verbose_compile, console,
):
    """Handle TeX file input processing."""
    results = []

    content = parse_tex_file(tex)
    items = extract_items_from_tex(content)

    if items:
        items = filter_items_by_range(items, item_range)
        console.print(f"[cyan]Processing {len(items)} item(s)...[/cyan]")
        for idx, tex_item in enumerate(items, 1):
            console.print(f"\n[bold]Item {idx}/{len(items)}[/bold]")
            result = process_tex_item(
                tex_content=tex_item, source_path=tex,
                variant_types=variant_types, generate_alternate=alternate,
                generate_ideas=ideas, use_context=context,
            )
            if do_compile:
                _compile_result(result, console, verbose_compile)
            results.append(result)
    else:
        result = process_tex_item(
            tex_content=content, source_path=tex,
            variant_types=variant_types, generate_alternate=alternate,
            generate_ideas=ideas, use_context=context,
        )
        if do_compile:
            _compile_result(result, console, verbose_compile)
        results.append(result)

    return results, 0


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
