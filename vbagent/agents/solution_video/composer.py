"""Composer — combines rendered Manim video with voice audio into final video."""

from __future__ import annotations

import subprocess
from pathlib import Path

from vbagent.agents.solution_video.models import ComposerResult, VoiceResult


def _get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        return float(result.stdout.strip())
    raise RuntimeError(f"Could not determine duration of {video_path}")


def _get_video_resolution(video_path: str) -> str:
    """Get video resolution using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            return f"{parts[0]}x{parts[1]}"
    return "unknown"


def compose_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path = "agentic/solution_videos/final/solution.mp4",
    show_spinner: bool = True,
) -> ComposerResult:
    """Combine a rendered Manim video with audio narration.

    Uses ffmpeg to merge the video and audio tracks. If the video is shorter
    than the audio, the last frame is held. If the audio is shorter, the
    video continues silently.

    Args:
        video_path: Path to the rendered Manim video (.mp4).
        audio_path: Path to the narration audio (.mp3).
        output_path: Path for the final composed video.
        show_spinner: Show progress spinner.

    Returns:
        ComposerResult with final video metadata.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    video_dur = _get_video_duration(str(video_path))
    audio_dur = _get_video_duration(
        str(audio_path))  # ffprobe works on audio too

    # Determine strategy based on duration mismatch
    if abs(video_dur - audio_dur) < 1.0:
        # Close enough — simple merge
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]
    elif video_dur < audio_dur:
        # Video shorter than audio — hold last frame
        # Use tpad filter to extend video to match audio
        pad_duration = audio_dur - video_dur + 0.5
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={pad_duration:.1f}[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]
    else:
        # Audio shorter than video — video continues silently, then audio fades
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

    if show_spinner:
        from rich.console import Console
        console = Console()
        with console.status("[bold green]Composing final video..."):
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300)
    else:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[:1000]}"
        )

    # Get final video metadata
    final_dur = _get_video_duration(str(output_path))
    resolution = _get_video_resolution(str(output_path))

    return ComposerResult(
        video_path=str(output_path),
        duration=final_dur,
        resolution=resolution,
    )


def compose_with_segments(
    video_path: str | Path,
    voice_result: VoiceResult,
    output_path: str | Path = "agentic/solution_videos/final/solution.mp4",
    show_spinner: bool = True,
) -> ComposerResult:
    """Compose video with per-segment audio files.

    Concatenates segment audio files first, then merges with video.

    Args:
        video_path: Path to the rendered Manim video.
        voice_result: VoiceResult with per-segment audio files.
        output_path: Path for the final composed video.
        show_spinner: Show progress spinner.

    Returns:
        ComposerResult with final video metadata.
    """
    output_path = Path(output_path)
    concat_audio = output_path.parent / "narration_combined.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create ffmpeg concat file
    concat_list = output_path.parent / "concat_list.txt"
    with open(concat_list, "w") as f:
        for seg in voice_result.segments:
            # ffmpeg concat requires escaped paths
            escaped = seg.audio_path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    # Concatenate audio segments
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(concat_audio),
    ]

    result = subprocess.run(
        concat_cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Audio concat failed:\n{result.stderr[:500]}")

    # Clean up concat list
    concat_list.unlink(missing_ok=True)

    # Now compose video + combined audio
    return compose_video(
        video_path=video_path,
        audio_path=str(concat_audio),
        output_path=output_path,
        show_spinner=show_spinner,
    )
