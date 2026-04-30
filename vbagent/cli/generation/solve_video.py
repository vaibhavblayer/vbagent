"""CLI command for generating solution walkthrough videos."""

import subprocess
import time
from pathlib import Path

import click
from rich.console import Console


# Dimension presets (same as animate.py)
DIMENSION_PRESETS = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
    "square": (1080, 1080),
    "vertical-hd": (1080, 1920),
    "horizontal-hd": (1920, 1080),
    "vertical-4k": (2160, 3840),
    "horizontal-4k": (3840, 2160),
}

VOICE_CHOICES = ("alloy", "ash", "ballad", "coral", "echo",
                 "fable", "nova", "onyx", "sage", "shimmer")


@click.command("solve_video")
@click.option("-i", "--input", "input_path", type=click.Path(exists=True), default=None,
              help="Problem image (.png/.jpg) or LaTeX file (.tex)")
@click.option("-p", "--problem", "problem_text", type=str, default=None,
              help="Problem LaTeX text (inline)")
@click.option("-s", "--solution", "solution_text", type=str, default=None,
              help="Solution LaTeX text (inline)")
@click.option("-o", "--output", "output_dir", type=click.Path(), default=None,
              help="Output directory (default: agentic/solution_videos/)")
@click.option("--script-only", is_flag=True, help="Only generate the narration script")
@click.option("--video-only", is_flag=True, help="Only generate Manim code (skip voice + compose)")
@click.option("--voice-only", is_flag=True, help="Only generate voice from existing script")
@click.option("--compose-only", is_flag=True, help="Only compose existing video + audio")
@click.option("--render/--no-render", default=True, help="Render Manim after code generation")
@click.option("--quality", type=click.Choice(["l", "m", "h"]), default="l",
              help="Render quality: l=low, m=medium, h=high")
@click.option("--dim", type=click.Choice(list(DIMENSION_PRESETS.keys())),
              default="vertical", help="Dimension preset [default: vertical]")
@click.option("--fps", type=int, default=30, help="Frame rate [default: 30]")
@click.option("--voice", type=click.Choice(VOICE_CHOICES), default="nova",
              help="TTS voice [default: nova]")
@click.option("--voice-model", type=click.Choice(["tts-1", "tts-1-hd"]), default="tts-1-hd",
              help="TTS model [default: tts-1-hd]")
@click.option("--max-retries", type=int, default=2, help="Max fix attempts on render failure")
@click.option("--no-cache", is_flag=True, help="Skip cache, force fresh generation")
def solve_video(
    input_path: str | None,
    problem_text: str | None,
    solution_text: str | None,
    output_dir: str | None,
    script_only: bool,
    video_only: bool,
    voice_only: bool,
    compose_only: bool,
    render: bool,
    quality: str,
    dim: str,
    fps: int,
    voice: str,
    voice_model: str,
    max_retries: int,
    no_cache: bool,
):
    """Generate complete solution walkthrough videos.

    \b
    Full pipeline: script → Manim video → voice → compose
    Or run individual stages with --script-only, --video-only, etc.

    \b
    Examples:
        vbagent solve-video -i problem.png
        vbagent solve-video -i problem.tex
        vbagent solve-video -i problem.png --script-only
        vbagent solve-video -i problem.png --video-only --no-render
        vbagent solve-video -i problem.png --voice nova --dim horizontal
        vbagent solve-video -i problem.png --quality h --fps 60
    """
    console = Console()

    if not input_path and not problem_text:
        console.print(
            "[red]Error:[/red] Provide -i (input file) or -p (problem text).")
        raise SystemExit(1)

    # Resolve dimensions
    pixel_width, pixel_height = DIMENSION_PRESETS[dim]
    dim_config = {"pixel_width": pixel_width,
                  "pixel_height": pixel_height, "frame_rate": fps}
    console.print(
        f"[dim]Config: {pixel_width}x{pixel_height} @ {fps}fps ({dim})[/dim]")

    # Resolve output directory
    if output_dir is None:
        if input_path:
            stem = Path(input_path).stem
        else:
            import hashlib
            stem = "inline_" + \
                hashlib.sha256((problem_text or "")[
                               :100].encode()).hexdigest()[:8]
        output_dir = f"agentic/solution_videos/{stem}"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load problem and solution from file if needed
    problem_latex, solution_latex, image_path = _load_input(
        input_path, problem_text, solution_text, console
    )

    use_cache = not no_cache
    t0 = time.time()

    try:
        from vbagent.utils.caffeinate import prevent_sleep

        with prevent_sleep("vbagent solve-video"):
            _run_pipeline(
                console=console,
                problem_latex=problem_latex,
                solution_latex=solution_latex,
                image_path=image_path,
                output_dir=out_path,
                dim_config=dim_config,
                quality=quality,
                voice_name=voice,
                voice_model=voice_model,
                max_retries=max_retries,
                use_cache=use_cache,
                render=render,
                script_only=script_only,
                video_only=video_only,
                voice_only=voice_only,
                compose_only=compose_only,
            )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise SystemExit(1)

    elapsed = time.time() - t0
    console.print(f"\n[bold green]Done[/bold green] in {elapsed:.1f}s")
    console.print(f"Output: {out_path}/")


def _load_input(
    input_path: str | None,
    problem_text: str | None,
    solution_text: str | None,
    console: Console,
) -> tuple[str, str, str | None]:
    """Load problem and solution from input file or inline text."""
    problem_latex = problem_text or ""
    solution_latex = solution_text or ""
    image_path = None

    if input_path:
        p = Path(input_path)
        if p.suffix in (".png", ".jpg", ".jpeg", ".webp"):
            image_path = str(p)
            console.print(f"[dim]Input image: {p.name}[/dim]")
        elif p.suffix == ".tex":
            content = p.read_text(encoding="utf-8")
            # Try to split problem and solution
            if r"\begin{solution}" in content:
                parts = content.split(r"\begin{solution}", 1)
                problem_latex = parts[0].strip()
                solution_latex = r"\begin{solution}" + parts[1].strip()
            else:
                problem_latex = content
            console.print(
                f"[dim]Input TeX: {p.name} ({len(content)} chars)[/dim]")
        else:
            console.print(
                f"[yellow]Warning:[/yellow] Unknown file type {p.suffix}, treating as TeX")
            problem_latex = p.read_text(encoding="utf-8")

    return problem_latex, solution_latex, image_path


def _run_pipeline(
    console: Console,
    problem_latex: str,
    solution_latex: str,
    image_path: str | None,
    output_dir: Path,
    dim_config: dict,
    quality: str,
    voice_name: str,
    voice_model: str,
    max_retries: int,
    use_cache: bool,
    render: bool,
    script_only: bool,
    video_only: bool,
    voice_only: bool,
    compose_only: bool,
):
    """Run the solution video pipeline."""
    import json
    import hashlib

    script_path = output_dir / "script.json"
    code_path = output_dir / "scene.py"
    audio_dir = output_dir / "audio"
    voice_meta_path = output_dir / "voice.json"
    final_video_path = output_dir / "solution.mp4"

    # Derive a consistent problem_id for caching across all stages
    if image_path:
        problem_id = Path(image_path).stem
    elif problem_latex:
        problem_id = "tex_" + hashlib.sha256(
            problem_latex[:500].encode()).hexdigest()[:12]
    else:
        problem_id = None

    # ── Stage 1: Script ──────────────────────────────────────────────
    if not compose_only:
        script = _stage_script(
            console, problem_latex, solution_latex, image_path,
            script_path, use_cache,
        )

        if script_only:
            return

    # ── Stage 2: Video code + render ─────────────────────────────────
    if not voice_only and not compose_only:
        rendered_video = _stage_video(
            console, script, problem_latex, solution_latex, image_path,
            code_path, dim_config, quality, max_retries, use_cache, render,
        )

        if video_only:
            return
    else:
        rendered_video = None

    # ── Stage 3: Voice ───────────────────────────────────────────────
    if not video_only and not compose_only:
        voice_result = _stage_voice(
            console, script, audio_dir, voice_name, voice_model,
            voice_meta_path, use_cache, problem_id,
        )
    else:
        voice_result = None

    # ── Stage 4: Compose ─────────────────────────────────────────────
    if compose_only:
        # Load from existing files
        _stage_compose_from_files(console, output_dir, final_video_path)
    elif rendered_video and voice_result:
        _stage_compose(console, rendered_video, voice_result, final_video_path)
    elif rendered_video and not voice_result:
        console.print(
            "[yellow]Skipping compose — no voice audio generated[/yellow]")
    elif not rendered_video:
        console.print("[yellow]Skipping compose — no rendered video[/yellow]")


def _stage_script(console, problem_latex, solution_latex, image_path, script_path, use_cache):
    """Generate narration script."""
    from vbagent.agents.solution_video.script_writer import generate_script
    import json

    console.print(
        "\n[bold cyan]Stage 1:[/bold cyan] Generating narration script...")

    script = generate_script(
        problem_latex=problem_latex,
        solution_latex=solution_latex,
        image_path=image_path,
        use_cache=use_cache,
    )

    # Save script
    with open(script_path, "w") as f:
        json.dump(script.model_dump(), f, indent=2)

    console.print(f"  Title: {script.title}")
    console.print(f"  Segments: {len(script.segments)}")
    console.print(f"  Est. duration: {script.total_duration_estimate:.0f}s")
    console.print(f"  Saved: {script_path}")

    return script


def _stage_video(
    console, script, problem_latex, solution_latex, image_path,
    code_path, dim_config, quality, max_retries, use_cache, render,
):
    """Generate Manim code per-segment and stitch, then optionally render."""
    from vbagent.agents.solution_video.video_coder import generate_video_code

    n = len(script.segments)
    console.print(
        f"\n[bold cyan]Stage 2:[/bold cyan] Generating Manim code "
        f"({n} segments, per-segment coding)..."
    )

    video_code = generate_video_code(
        script=script,
        problem_latex=problem_latex,
        solution_latex=solution_latex,
        image_path=image_path,
        dim_config=dim_config,
        use_cache=use_cache,
    )

    # Save code
    code_path.write_text(video_code.code, encoding="utf-8")
    console.print(f"  Scene: {video_code.scene_name}")
    console.print(f"  Saved: {code_path}")

    if not render:
        console.print("  [dim]Render skipped (--no-render)[/dim]")
        return None

    # Render with retry loop
    return _render_with_retries(
        console, code_path, video_code.scene_name, quality, max_retries, dim_config,
    )


def _render_with_retries(console, code_path, scene_name, quality, max_retries, dim_config):
    """Render Manim scene with auto-fix retries."""
    quality_flag = {"l": "-ql", "m": "-qm", "h": "-qh"}[quality]

    for attempt in range(1 + max_retries):
        console.print(f"  Rendering (attempt {attempt + 1})...")

        cmd = [
            "manim", quality_flag,
            str(code_path), scene_name,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Find the rendered video
            video_file = _find_rendered_video(code_path, scene_name, quality)
            if video_file:
                console.print(f"  [green]Rendered:[/green] {video_file}")
                return str(video_file)
            else:
                console.print(
                    "  [yellow]Render succeeded but video file not found[/yellow]")
                return None

        # Render failed
        error = result.stderr[-2000:] if result.stderr else "No error output"
        console.print(f"  [red]Render failed[/red]")

        if attempt < max_retries:
            console.print(f"  Attempting auto-fix...")
            from vbagent.agents.solution_video.video_fixer import fix_video_code

            code_content = code_path.read_text(encoding="utf-8")
            fix = fix_video_code(code_content, error)
            code_path.write_text(fix.code, encoding="utf-8")
            console.print(f"  Fix: {fix.what_changed}")

            # Re-extract scene name in case it changed
            import re
            match = re.search(r'class\s+(\w+)\s*\(\s*Scene\s*\)', fix.code)
            if match:
                scene_name = match.group(1)
        else:
            console.print(
                f"  [red]All {max_retries} fix attempts exhausted[/red]")
            console.print(f"  Error:\n{error[:500]}")

    return None


def _find_rendered_video(code_path, scene_name, quality):
    """Find the rendered video file in Manim's output directory."""
    media_dir = code_path.parent / "media" / "videos" / code_path.stem
    quality_dirs = {
        "l": "480p15",
        "m": "720p30",
        "h": "1080p60",
    }

    # Manim output structure: media/videos/{filename}/{quality}/{SceneName}.mp4
    for q_dir_name in [quality_dirs.get(quality, ""), ""]:
        if q_dir_name:
            search_dir = media_dir / q_dir_name
        else:
            search_dir = media_dir

        if search_dir.exists():
            for mp4 in search_dir.glob("*.mp4"):
                if scene_name in mp4.stem or mp4.stem == scene_name:
                    return mp4

    # Broader search
    for mp4 in code_path.parent.rglob("*.mp4"):
        if scene_name in mp4.stem:
            return mp4

    return None


def _stage_voice(console, script, audio_dir, voice_name, voice_model,
                 voice_meta_path, use_cache=True, problem_id=None):
    """Generate voice narration."""
    from vbagent.agents.solution_video.voice import generate_voice
    import json

    console.print(
        f"\n[bold cyan]Stage 3:[/bold cyan] Generating voice ({voice_name})...")

    voice_result = generate_voice(
        script=script,
        output_dir=audio_dir,
        voice=voice_name,
        model=voice_model,
        use_cache=use_cache,
        problem_id=problem_id,
    )

    # Save metadata
    with open(voice_meta_path, "w") as f:
        json.dump(voice_result.model_dump(), f, indent=2)

    console.print(f"  Segments: {len(voice_result.segments)}")
    console.print(f"  Total duration: {voice_result.total_duration:.1f}s")
    console.print(f"  Audio dir: {audio_dir}")

    return voice_result


def _stage_compose(console, rendered_video, voice_result, final_video_path):
    """Compose video + audio."""
    from vbagent.agents.solution_video.composer import compose_with_segments

    console.print("\n[bold cyan]Stage 4:[/bold cyan] Composing final video...")

    result = compose_with_segments(
        video_path=rendered_video,
        voice_result=voice_result,
        output_path=final_video_path,
    )

    console.print(
        f"  [bold green]Final video:[/bold green] {result.video_path}")
    console.print(f"  Duration: {result.duration:.1f}s")
    console.print(f"  Resolution: {result.resolution}")


def _stage_compose_from_files(console, output_dir, final_video_path):
    """Compose from existing files on disk."""
    from vbagent.agents.solution_video.composer import compose_with_segments
    from vbagent.agents.solution_video.models import VoiceResult
    import json

    voice_meta = output_dir / "voice.json"
    if not voice_meta.exists():
        console.print("[red]No voice.json found — run voice stage first[/red]")
        raise SystemExit(1)

    with open(voice_meta) as f:
        voice_result = VoiceResult(**json.load(f))

    # Find rendered video
    video_files = list(output_dir.rglob("*.mp4"))
    video_files = [v for v in video_files if "final" not in str(
        v) and "solution" not in v.name]
    if not video_files:
        console.print(
            "[red]No rendered video found — run video stage first[/red]")
        raise SystemExit(1)

    rendered_video = str(video_files[0])
    console.print(f"  Using video: {rendered_video}")

    _stage_compose(console, rendered_video, voice_result, final_video_path)
