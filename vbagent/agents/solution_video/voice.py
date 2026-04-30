"""Voice agent — generates audio narration from script segments using OpenAI TTS."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from vbagent.agents.solution_video.models import SolutionScript, VoiceSegment, VoiceResult


# Supported OpenAI TTS voices
VOICES = ("alloy", "ash", "ballad", "coral", "echo",
          "fable", "nova", "onyx", "sage", "shimmer")

# TTS models
TTS_MODELS = ("tts-1", "tts-1-hd")


def _get_audio_duration(audio_path: str) -> float:
    """Get duration of an audio file in seconds using mutagen or ffprobe."""
    path = Path(audio_path)

    # Try mutagen first (lightweight)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(path))
        return audio.info.length
    except Exception:
        pass

    # Fallback: ffprobe
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    # Last resort: estimate from file size (~16kB/s for mp3 at 128kbps)
    size = path.stat().st_size
    return size / 16000.0


def generate_voice(
    script: SolutionScript,
    output_dir: str | Path = "agentic/solution_videos/audio",
    voice: str = "nova",
    model: str = "tts-1-hd",
    show_spinner: bool = True,
    use_cache: bool = True,
    problem_id: str | None = None,
) -> VoiceResult:
    """Generate audio narration for each script segment.

    Uses OpenAI's TTS API to convert narration text to speech.

    Args:
        script: The narration script with segments.
        output_dir: Directory to save audio files.
        voice: TTS voice to use (alloy, ash, coral, echo, fable, nova, onyx, sage, shimmer).
        model: TTS model (tts-1 for speed, tts-1-hd for quality).
        show_spinner: Show progress spinner.
        use_cache: Use pipeline cache to skip regeneration.
        problem_id: Problem ID for caching (derived from script title if None).

    Returns:
        VoiceResult with audio segments and timing info.
    """
    if voice not in VOICES:
        raise ValueError(
            f"Invalid voice '{voice}'. Choose from: {', '.join(VOICES)}")
    if model not in TTS_MODELS:
        raise ValueError(
            f"Invalid model '{model}'. Choose from: {', '.join(TTS_MODELS)}")

    # Derive problem_id for caching
    if problem_id is None and script.title:
        import hashlib
        problem_id = "sv_" + hashlib.sha256(
            script.title[:200].encode()).hexdigest()[:12]

    # Check cache — voice result is stored as JSON with audio paths
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cached = cache.get(problem_id, "solution_voice")
        if cached and isinstance(cached, dict):
            result = VoiceResult(**cached)
            # Verify audio files still exist
            all_exist = all(
                Path(seg.audio_path).exists() for seg in result.segments
            )
            if all_exist:
                return result

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Import OpenAI client
    from openai import OpenAI
    import os
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    segments: list[VoiceSegment] = []
    total_duration = 0.0

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
    else:
        progress = None

    task = None
    if progress:
        progress.start()
        task = progress.add_task(
            "Generating voice segments", total=len(script.segments))

    try:
        for i, seg in enumerate(script.segments):
            audio_filename = f"segment_{i:03d}_{seg.segment_type}.mp3"
            audio_path = out_path / audio_filename

            # Call OpenAI TTS
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=seg.narration,
                response_format="mp3",
            )

            # Save audio
            response.stream_to_file(str(audio_path))

            # Get actual duration
            duration = _get_audio_duration(str(audio_path))
            total_duration += duration

            segments.append(VoiceSegment(
                index=i,
                text=seg.narration,
                audio_path=str(audio_path),
                duration=duration,
            ))

            if progress and task is not None:
                progress.update(task, advance=1)

            # Small delay to avoid rate limits
            if i < len(script.segments) - 1:
                time.sleep(0.1)

    finally:
        if progress:
            progress.stop()

    result = VoiceResult(
        segments=segments,
        total_duration=total_duration,
        voice=voice,
        output_dir=str(out_path),
    )

    # Save to cache
    if use_cache and problem_id:
        from vbagent.cache import PipelineCache
        cache = PipelineCache()
        cache.set(problem_id, "solution_voice", result.model_dump())

    return result


def generate_voice_combined(
    script: SolutionScript,
    output_path: str | Path = "agentic/solution_videos/audio/narration.mp3",
    voice: str = "nova",
    model: str = "tts-1-hd",
    show_spinner: bool = True,
) -> tuple[str, float]:
    """Generate a single combined audio file for the entire script.

    Concatenates all segment narrations with natural pauses and generates
    one audio file. Simpler than per-segment but less flexible for syncing.

    Args:
        script: The narration script.
        output_path: Path for the output audio file.
        voice: TTS voice.
        model: TTS model.
        show_spinner: Show progress spinner.

    Returns:
        Tuple of (audio_path, duration_seconds).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Combine all narration with pauses
    full_narration = ""
    for seg in script.segments:
        full_narration += seg.narration.strip()
        # Add a pause between segments
        full_narration += " ... "

    full_narration = full_narration.strip().rstrip(".")

    from openai import OpenAI
    import os
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    if show_spinner:
        from rich.console import Console
        console = Console()
        with console.status("[bold green]Generating narration audio..."):
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=full_narration,
                response_format="mp3",
            )
            response.stream_to_file(str(out))
    else:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=full_narration,
            response_format="mp3",
        )
        response.stream_to_file(str(out))

    duration = _get_audio_duration(str(out))
    return str(out), duration
