"""Stitcher — combines multiple scene classes into one runnable Manim file."""

from __future__ import annotations

import re

from vbagent.agents.animation.models import SceneCode


def stitch_scenes(
    scene_codes: list[SceneCode],
    dim_config: dict,
) -> str:
    """Combine multiple scene classes into a single Manim file.

    Args:
        scene_codes: List of SceneCode objects (in order).
        dim_config: Dimension config (pixel_width, pixel_height, frame_rate).

    Returns:
        Complete Python file content.
    """
    # Header
    lines = [
        "from manim import *",
        "import numpy as np",
        "",
        f"config.frame_rate = {dim_config['frame_rate']}",
        f"config.pixel_width = {dim_config['pixel_width']}",
        f"config.pixel_height = {dim_config['pixel_height']}",
        "",
        "",
    ]

    scene_names = []

    for sc in scene_codes:
        # Clean the code — extract just the class definition
        class_code = _extract_class(sc.code, sc.scene_name)
        lines.append(class_code)
        lines.append("")
        lines.append("")
        scene_names.append(sc.scene_name)

    # Add a combined scene that plays all scenes in sequence
    # (Manim can render individual scenes, but this gives a single-render option)
    if len(scene_names) > 1:
        lines.append(f"# To render all scenes in sequence:")
        lines.append(f"# manim -pql filename.py {' '.join(scene_names)}")
        lines.append(f"#")
        lines.append(f"# Or render individually:")
        for name in scene_names:
            lines.append(f"# manim -pql filename.py {name}")
        lines.append("")

    return "\n".join(lines)


def _extract_class(code: str, expected_name: str) -> str:
    """Extract just the class definition from generated code.

    The scene coder might include imports or config lines despite instructions.
    This strips everything except the class definition.
    """
    # Remove common unwanted lines
    cleaned_lines = []
    skip_patterns = [
        re.compile(r'^\s*from manim import'),
        re.compile(r'^\s*import numpy'),
        re.compile(r'^\s*import manim'),
        re.compile(r'^\s*config\.\w+\s*='),
    ]

    in_class = False
    class_indent = 0

    for line in code.split("\n"):
        # Skip unwanted import/config lines
        if any(p.match(line) for p in skip_patterns):
            continue

        # Detect class start
        class_match = re.match(r'^(class\s+\w+\s*\(.*?\)\s*:)', line)
        if class_match:
            in_class = True
            class_indent = 0
            cleaned_lines.append(line)
            continue

        if in_class:
            # Check if we've left the class (non-indented, non-empty line that isn't a decorator)
            if line.strip() and not line[0].isspace() and not line.startswith("class ") and not line.startswith("@"):
                break
            cleaned_lines.append(line)
        elif not line.strip():
            # Preserve blank lines between classes
            if cleaned_lines:
                cleaned_lines.append(line)

    result = "\n".join(cleaned_lines).strip()

    # If extraction failed, return the original code (minus imports)
    if not result or "class " not in result:
        return code.strip()

    return result
