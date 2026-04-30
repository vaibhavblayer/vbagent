"""Video coder — orchestrates per-segment coding and stitching for solution videos.

Pipeline: script segments → per-segment coder (parallel) → stitcher → VideoSceneCode

Each segment coder outputs a standalone Scene class. The stitcher extracts
construct() bodies and merges them into one combined Scene with transitions.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from vbagent.agents.solution_video.models import (
    SolutionScript, SegmentSceneCode, VideoSceneCode,
)


def _get_problem_id(image_path: str | None, problem_latex: str) -> str | None:
    """Derive a problem_id for caching."""
    if image_path:
        return Path(image_path).stem
    if problem_latex:
        return "tex_" + hashlib.sha256(problem_latex[:500].encode()).hexdigest()[:12]
    return None


def _code_one_segment(
    segment,
    segment_index: int,
    total_segments: int,
    previous_summaries: list[str],
    dim_config: dict,
) -> tuple[int, SegmentSceneCode]:
    """Worker function for parallel segment coding.

    Returns (segment_index, result) so we can reassemble in order.
    """
    from vbagent.agents.solution_video.segment_coder import generate_segment_code

    result = generate_segment_code(
        segment=segment,
        segment_index=segment_index,
        total_segments=total_segments,
        previous_summaries=previous_summaries,
        dim_config=dim_config,
        show_spinner=False,  # critical for parallel safety
    )
    return segment_index, result


def generate_video_code(
    script: SolutionScript,
    problem_latex: str = "",
    solution_latex: str = "",
    image_path: str | None = None,
    show_spinner: bool = True,
    use_cache: bool = True,
    dim_config: dict | None = None,
    max_workers: int = 4,
) -> VideoSceneCode:
    """Generate Manim code for a solution walkthrough video.

    Splits the work into per-segment coding calls that run in parallel,
    then stitches the results into a single Scene.

    Args:
        script: The narration script to visualize.
        problem_latex: Original problem LaTeX (for context).
        solution_latex: Original solution LaTeX (for context).
        image_path: Optional problem image path.
        show_spinner: Show progress spinner (for the overall progress).
        use_cache: Use pipeline cache.
        dim_config: Video dimensions {pixel_width, pixel_height, frame_rate}.
        max_workers: Max parallel segment coders (default 4).

    Returns:
        VideoSceneCode with complete Manim scene.
    """
    if dim_config is None:
        dim_config = {"pixel_width": 1080,
                      "pixel_height": 1920, "frame_rate": 30}

    # Check cache for the final stitched code
    problem_id = _get_problem_id(image_path, problem_latex)
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        import re
        cache = PipelineCache()
        cached = cache.get(problem_id, "solution_video_code")
        if cached and isinstance(cached, str) and cached.strip():
            scene_match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', cached)
            scene_name = scene_match.group(
                1) if scene_match else "SolutionVideo"
            return VideoSceneCode(scene_name=scene_name, code=cached)

    # Build previous_summaries for each segment upfront.
    all_summaries = [seg.visual_cue for seg in script.segments]

    n = len(script.segments)
    results: dict[int, SegmentSceneCode] = {}
    errors: list[tuple[int, Exception]] = []

    if show_spinner:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        console = Console()
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        )
        progress.start()
        task = progress.add_task(
            f"Coding {n} segments (parallel, {min(max_workers, n)} workers)", total=n,
        )
    else:
        progress = None
        task = None

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {}
            for i, segment in enumerate(script.segments):
                future = executor.submit(
                    _code_one_segment,
                    segment=segment,
                    segment_index=i,
                    total_segments=n,
                    previous_summaries=all_summaries[:i],
                    dim_config=dim_config,
                )
                future_to_idx[future] = i

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    seg_idx, seg_result = future.result()
                    results[seg_idx] = seg_result
                except Exception as e:
                    errors.append((idx, e))

                if progress and task is not None:
                    progress.update(task, advance=1)
    finally:
        if progress:
            progress.stop()

    # Report errors
    if errors:
        from rich.console import Console
        err_console = Console(stderr=True)
        for idx, err in errors:
            err_console.print(
                f"[red]Segment {idx + 1} failed:[/red] {err}"
            )
        # Fill failed segments with placeholder Scene
        for idx, _ in errors:
            seg_type = script.segments[idx].segment_type
            name = f"Segment{idx + 1:02d}{seg_type.title()}"
            results[idx] = SegmentSceneCode(
                scene_name=name,
                code=(
                    f"class {name}(Scene):\n"
                    f"    def construct(self):\n"
                    f"        # Segment {idx + 1} failed to generate\n"
                    f"        self.wait(2)\n"
                ),
            )

    # Reassemble in order
    ordered = [results[i] for i in range(n) if i in results]

    # Stitch into one Scene
    from vbagent.agents.solution_video.video_stitcher import stitch_segments

    result = stitch_segments(
        segment_codes=ordered,
        dim_config=dim_config,
    )

    # Save to cache
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cache.set(problem_id, "solution_video_code", result.code)

    return result
