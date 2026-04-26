"""CLI command for generating Manim animations from problems."""

import subprocess
import time
from pathlib import Path

import click
from rich.console import Console


# Dimension presets: name -> (width, height)
DIMENSION_PRESETS = {
    "vertical": (1080, 1920),    # 9:16 portrait (default)
    "horizontal": (1920, 1080),  # 16:9 landscape
    "square": (1080, 1080),      # 1:1
    "vertical-hd": (1080, 1920),
    "horizontal-hd": (1920, 1080),
    "vertical-4k": (2160, 3840),
    "horizontal-4k": (3840, 2160),
}


@click.command()
@click.option("-i", "--input", "input_path", type=click.Path(exists=True), default=None,
              help="Problem image (.png/.jpg) or LaTeX file (.tex)")
@click.option("-p", "--prompt", "free_prompt", type=str, default=None,
              help="Free-form animation description (skips assessor)")
@click.option("-o", "--output", "output_path", type=click.Path(),
              default=None, help="Output .py file (default: agentic/animations/...)")
@click.option("--from", "from_index", type=int, default=None,
              help="Start index for batch (1-based)")
@click.option("--to", "to_index", type=int, default=None,
              help="End index for batch (1-based, inclusive)")
@click.option("--explain", is_flag=True,
              help="Multi-scene explainer mode (planner → per-scene coder → stitch)")
@click.option("--render", is_flag=True, help="Render the animation with manim after generation")
@click.option("--quality", type=click.Choice(["l", "m", "h"]), default="l",
              help="Render quality: l=low, m=medium, h=high")
@click.option("--dim", type=click.Choice(list(DIMENSION_PRESETS.keys())),
              default="vertical", help="Dimension preset [default: vertical (1080x1920)]")
@click.option("--fps", type=int, default=60, help="Frame rate [default: 60]")
@click.option("--max-retries", type=int, default=2, help="Max fix attempts on render failure")
@click.option("--assess-only", is_flag=True, help="Only run assessment, don't generate code")
@click.option("--no-cache", is_flag=True, help="Skip cache, force fresh generation")
def animate(
    input_path: str | None,
    free_prompt: str | None,
    output_path: str | None,
    from_index: int | None,
    to_index: int | None,
    explain: bool,
    render: bool,
    quality: str,
    dim: str,
    fps: int,
    max_retries: int,
    assess_only: bool,
    no_cache: bool,
):
    """Generate Manim animations for physics/math problems.

    \b
    Three modes:
      1. From problem: -i image.png (assessor decides what to animate)
      2. Free-form: -p "animate sin(x) → |sin(x)|" (direct to coder)
      3. Explain: -p "Explain polarisation" --explain (multi-scene)

    \b
    Examples:
        vbagent animate -i images/problem_5.png
        vbagent animate -i images/problem_1.png --from 1 --to 5
        vbagent animate -p "Show sin(x) transforming to |sin(x)| then sin(|x|)"
        vbagent animate -p "Explain polarisation of light" --explain --render
        vbagent animate -p "Projectile at 45° with velocity decomposition" --dim horizontal
        vbagent animate -i question.png -p "Focus on energy conservation" --render
        vbagent animate -i images/problem_1.png --from 1 --to 10 --render --fps 30
    """
    console = Console()

    if not input_path and not free_prompt:
        console.print("[red]Error:[/red] Provide -i (input file) or -p (prompt) or both.")
        raise SystemExit(1)

    # Resolve dimensions
    pixel_width, pixel_height = DIMENSION_PRESETS[dim]
    dim_config = {"pixel_width": pixel_width, "pixel_height": pixel_height, "frame_rate": fps}
    console.print(f"[dim]Config: {pixel_width}x{pixel_height} @ {fps}fps ({dim})[/dim]")

    try:
        from vbagent.utils.caffeinate import prevent_sleep

        with prevent_sleep("vbagent animate"):
            if explain and free_prompt:
                # Multi-scene explain mode
                _process_explain(
                    console=console,
                    topic=free_prompt,
                    output_path=output_path,
                    render=render,
                    quality=quality,
                    max_retries=max_retries,
                    dim_config=dim_config,
                )
            elif free_prompt and not input_path:
                # Free-form mode — skip assessor, go straight to coder
                _process_free_prompt(
                    console=console,
                    prompt=free_prompt,
                    output_path=output_path,
                    render=render,
                    quality=quality,
                    max_retries=max_retries,
                    dim_config=dim_config,
                    use_cache=not no_cache,
                )
            elif input_path:
                # Problem mode — with optional prompt override
                inputs = _resolve_inputs(input_path, from_index, to_index)

                for idx, inp in enumerate(inputs):
                    if len(inputs) > 1:
                        console.print(f"\n[bold]━━━ [{idx + 1}/{len(inputs)}] {inp.name} ━━━[/bold]")

                    _process_single(
                        console=console,
                        path=inp,
                        output_path=output_path if len(inputs) == 1 else None,
                        prompt_override=free_prompt,
                        render=render,
                        quality=quality,
                        max_retries=max_retries,
                        assess_only=assess_only,
                        dim_config=dim_config,
                        use_cache=not no_cache,
                    )

                if len(inputs) > 1:
                    console.print(f"\n[bold green]Batch complete: {len(inputs)} problem(s)[/bold green]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Animation failed:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


def _process_explain(
    console: Console,
    topic: str,
    output_path: str | None,
    render: bool,
    quality: str,
    max_retries: int,
    dim_config: dict,
):
    """Multi-scene explain mode: planner → per-scene coder → stitch."""
    from vbagent.agents.animation.planner import plan_animation
    from vbagent.agents.animation.scene_coder import generate_scene
    from vbagent.agents.animation.stitcher import stitch_scenes
    from vbagent.config import get_model

    # Step 1: Plan
    planner_model = get_model("animation_assessor")
    console.print(f"[cyan]Planning multi-scene animation...[/cyan] [dim](model: {planner_model})[/dim]")
    t0 = time.time()

    plan = plan_animation(topic=topic)

    elapsed = time.time() - t0
    console.print(f"[green]✓ Plan ready in {elapsed:.1f}s — {len(plan.scenes)} scenes[/green]")

    for i, scene in enumerate(plan.scenes, 1):
        console.print(f"  {i}. [bold]{scene.scene_name}[/bold] (~{scene.duration_hint}s) — {scene.key_concept}")

    total_duration = sum(s.duration_hint for s in plan.scenes)
    console.print(f"  [dim]Total: ~{total_duration:.0f}s[/dim]")

    # Step 2: Generate each scene
    scene_codes = []
    previous_summaries = []

    for i, scene_plan in enumerate(plan.scenes, 1):
        coder_model = get_model("animation_coder")
        console.print(f"\n[cyan]Generating scene {i}/{len(plan.scenes)}: {scene_plan.scene_name}[/cyan] [dim](model: {coder_model})[/dim]")
        t0 = time.time()

        scene_code = generate_scene(
            scene_plan=scene_plan,
            scene_index=i,
            total_scenes=len(plan.scenes),
            previous_summaries=previous_summaries,
            dim_config=dim_config,
        )

        elapsed = time.time() - t0
        console.print(f"[green]✓ {scene_plan.scene_name} generated in {elapsed:.1f}s[/green]")

        scene_codes.append(scene_code)
        previous_summaries.append(scene_plan.key_concept)

    # Step 3: Stitch
    console.print(f"\n[cyan]Stitching {len(scene_codes)} scenes...[/cyan]")
    final_code = stitch_scenes(scene_codes, dim_config)

    # Write output
    if output_path:
        out = Path(output_path)
    else:
        import re
        anim_dir = Path("agentic/animations")
        anim_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r'[^a-z0-9]+', '_', topic[:40].lower()).strip('_')
        out = anim_dir / f"explain_{slug}.py"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(final_code, encoding="utf-8")
    console.print(f"[cyan]Output:[/cyan] {out}")

    scene_names = [sc.scene_name for sc in scene_codes]
    console.print(f"[dim]Scenes: {', '.join(scene_names)}[/dim]")

    # Step 4: Render (optional)
    if render:
        for sc in scene_codes:
            console.print(f"\n[cyan]Rendering {sc.scene_name}...[/cyan]")
            _render_with_retries(
                console=console,
                py_file=out,
                scene_name=sc.scene_name,
                quality_flag=f"-pq{quality}",
                max_retries=max_retries,
                cwd=out.parent,
            )

    console.print(f"\n[bold green]✓ Explain animation complete: {len(scene_codes)} scenes[/bold green]")
    console.print(f"[dim]Render all: manim -pq{quality} {out.name} {' '.join(scene_names)}[/dim]")


def _process_free_prompt(
    console: Console,
    prompt: str,
    output_path: str | None,
    render: bool,
    quality: str,
    max_retries: int,
    dim_config: dict,
    use_cache: bool = True,
):
    """Free-form prompt mode — skip assessor, go straight to coder."""
    from vbagent.agents.animation.coder import generate_animation
    from vbagent.agents.animation.models import AnimationAssessment
    from vbagent.config import get_model

    # Build a synthetic assessment from the prompt
    assessment = AnimationAssessment(
        should_animate=True,
        mode="concept",
        animation_type="other",
        concept_description=prompt,
        duration_hint=20.0,
        reason="Free-form prompt",
    )

    coder_model = get_model("animation_coder")
    console.print(f"[cyan]Generating Manim code from prompt...[/cyan] [dim](model: {coder_model})[/dim]")
    t0 = time.time()

    result = generate_animation(
        assessment=assessment,
        problem_latex="",
        image_path=None,
        solution_latex="",
        show_spinner=True,
        use_cache=use_cache,
        dim_config=dim_config,
    )

    elapsed = time.time() - t0
    console.print(f"[green]✓ Code generated in {elapsed:.1f}s[/green]")

    # Write output
    if output_path:
        out = Path(output_path)
    else:
        anim_dir = Path("agentic/animations")
        anim_dir.mkdir(parents=True, exist_ok=True)
        # Generate name from prompt
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', prompt[:40].lower()).strip('_')
        out = anim_dir / f"{slug}.py"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.code, encoding="utf-8")
    console.print(f"[cyan]Output:[/cyan] {out}")

    if render:
        _render_with_retries(
            console=console, py_file=out, scene_name=result.scene_name,
            quality_flag=f"-pq{quality}", max_retries=max_retries, cwd=out.parent,
        )


def _resolve_inputs(input_path: str, from_index: int | None, to_index: int | None) -> list[Path]:
    """Resolve input path + range into a list of file paths."""
    import re

    path = Path(input_path)

    if from_index is None and to_index is None:
        return [path]

    match = re.search(r'(\d+)', path.stem)
    if not match:
        raise click.BadParameter(
            f"Cannot derive batch pattern from '{path.name}'. "
            f"File name must contain a number (e.g. problem_1.png)."
        )

    prefix = path.stem[:match.start()]
    suffix_part = path.stem[match.end():]
    ext = path.suffix
    parent = path.parent

    start = from_index or 1
    end = to_index or start

    paths = []
    for n in range(start, end + 1):
        candidate = parent / f"{prefix}{n}{suffix_part}{ext}"
        if candidate.exists():
            paths.append(candidate)

    if not paths:
        raise FileNotFoundError(
            f"No files found for range {start}–{end} with pattern "
            f"{parent}/{prefix}N{suffix_part}{ext}"
        )

    return paths


def _process_single(
    console: Console,
    path: Path,
    output_path: str | None,
    prompt_override: str | None,
    render: bool,
    quality: str,
    max_retries: int,
    assess_only: bool,
    dim_config: dict,
    use_cache: bool = True,
):
    """Process a single problem file through the animation pipeline."""
    image_path = None
    problem_latex = ""
    solution_latex = ""

    if path.suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        image_path = str(path)
        console.print(f"[cyan]Input image:[/cyan] {path.name}")
    elif path.suffix == ".tex":
        from vbagent.analysis.extractor import extract_question, extract_solution
        content = path.read_text(encoding="utf-8")
        problem_latex = extract_question(content)
        solution_latex = extract_solution(content)
        console.print(f"[cyan]Input LaTeX:[/cyan] {path.name}")
    else:
        console.print(f"[red]Unsupported file type:[/red] {path.suffix}")
        return

    if prompt_override:
        # Prompt override — skip assessor, use prompt as description
        from vbagent.agents.animation.models import AnimationAssessment
        assessment = AnimationAssessment(
            should_animate=True,
            mode="concept",
            animation_type="other",
            concept_description=prompt_override,
            duration_hint=20.0,
            reason="Prompt override",
        )
    else:
        # Normal assessor path
        from vbagent.agents.animation.assessor import assess_animation
        from vbagent.config import get_model

        assessor_model = get_model("animation_assessor")
        console.print(f"[cyan]Assessing...[/cyan] [dim](model: {assessor_model})[/dim]")
        t0 = time.time()

        assessment = assess_animation(
            problem_latex=problem_latex,
            image_path=image_path,
            solution_latex=solution_latex,
            use_cache=use_cache,
        )

        elapsed = time.time() - t0
        console.print(f"[green]✓ Assessment in {elapsed:.1f}s[/green]")

        if not assessment.should_animate:
            console.print(f"[yellow]Skip[/yellow] — {assessment.reason[:80]}")
            return

        console.print(f"[green]Animate![/green]  {assessment.mode}: {assessment.animation_type}")

    if assess_only:
        console.print(f"  {assessment.concept_description[:200]}")
        return

    # Generate code
    from vbagent.agents.animation.coder import generate_animation
    from vbagent.config import get_model

    coder_model = get_model("animation_coder")
    console.print(f"[cyan]Generating Manim code...[/cyan] [dim](model: {coder_model})[/dim]")
    t0 = time.time()

    result = generate_animation(
        assessment=assessment,
        problem_latex=problem_latex,
        image_path=image_path,
        solution_latex=solution_latex,
        use_cache=use_cache,
        dim_config=dim_config,
    )

    elapsed = time.time() - t0
    console.print(f"[green]✓ Code generated in {elapsed:.1f}s[/green]")

    # Write output
    if output_path:
        out = Path(output_path)
    else:
        anim_dir = Path("agentic/animations")
        anim_dir.mkdir(parents=True, exist_ok=True)
        out = anim_dir / f"{path.stem}.py"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.code, encoding="utf-8")
    console.print(f"[cyan]Output:[/cyan] {out}")

    if render:
        _render_with_retries(
            console=console, py_file=out, scene_name=result.scene_name,
            quality_flag=f"-pq{quality}", max_retries=max_retries, cwd=out.parent,
        )


def _render_with_retries(
    console: Console,
    py_file: Path,
    scene_name: str,
    quality_flag: str,
    max_retries: int,
    cwd: Path | None = None,
):
    """Render with manim, retrying with fixer agent on failure."""
    import os
    work_dir = cwd or py_file.parent
    file_name = py_file.name
    env = {**os.environ, "PYTHONWARNINGS": "ignore::UserWarning"}

    for attempt in range(1 + max_retries):
        console.print(f"[cyan]Rendering{'  (retry ' + str(attempt) + ')' if attempt > 0 else ''}...[/cyan]")

        proc = subprocess.run(
            ["manim", quality_flag, file_name, scene_name],
            capture_output=True, text=True, timeout=180,
            cwd=str(work_dir), env=env,
        )

        if proc.returncode == 0:
            console.print(f"[green]✓ Rendered![/green]")
            media_dir = work_dir / "media"
            if media_dir.exists():
                videos = sorted(media_dir.rglob("*.mp4"),
                                key=lambda p: p.stat().st_mtime, reverse=True)
                if videos:
                    console.print(f"[cyan]Video:[/cyan] {videos[0]}")
            return

        error_output = (proc.stderr + "\n" + proc.stdout).strip()
        console.print(f"[red]Render failed[/red]")
        console.print(f"[dim]{error_output[:500]}[/dim]")

        if attempt < max_retries:
            from vbagent.agents.animation.fixer import fix_animation
            console.print("[cyan]Auto-fixing...[/cyan]")
            code = py_file.read_text(encoding="utf-8")
            fix = fix_animation(code=code, error_output=error_output)
            py_file.write_text(fix.code, encoding="utf-8")
            console.print(f"[green]Fix:[/green] {fix.what_changed}")
        else:
            console.print(f"[red]Failed after {max_retries} retries.[/red] File: {py_file}")
