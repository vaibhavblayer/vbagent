"""Video stitcher — combines per-segment Scene classes into one Manim file.

Each segment coder outputs a standalone Scene class. The stitcher:
1. Extracts the construct() body from each class
2. Merges them into a single SolutionVideo Scene (with FadeOut transitions)
3. Wraps with imports and config
"""

from __future__ import annotations

import re
import textwrap

from vbagent.agents.solution_video.models import SegmentSceneCode, VideoSceneCode


def stitch_segments(
    segment_codes: list[SegmentSceneCode],
    dim_config: dict,
    scene_name: str = "SolutionVideo",
) -> VideoSceneCode:
    """Combine per-segment Scene classes into a single Manim file.

    Args:
        segment_codes: List of SegmentSceneCode objects (in order).
        dim_config: Dimension config (pixel_width, pixel_height, frame_rate).
        scene_name: Name for the combined Scene class.

    Returns:
        VideoSceneCode with the complete file.
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
        f"class {scene_name}(Scene):",
        "    def construct(self):",
    ]

    if not segment_codes:
        lines.append("        pass")
        code = "\n".join(lines)
        return VideoSceneCode(scene_name=scene_name, code=code)

    for i, sc in enumerate(segment_codes):
        # Section separator
        lines.append("")
        lines.append(f"        # {'=' * 56}")
        lines.append(f"        # {sc.scene_name}")
        lines.append(f"        # {'=' * 56}")
        lines.append("")

        # Add FadeOut transition between segments (not before the first)
        if i > 0:
            lines.append(
                "        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)")
            lines.append("")

        # Extract construct body and indent into the combined class
        body = _extract_construct_body(sc.code)
        lines.append(body)

    # Final wait
    lines.append("")
    lines.append("        # End")
    lines.append("        self.wait(2)")
    lines.append("")

    code = "\n".join(lines)
    return VideoSceneCode(scene_name=scene_name, code=code)


def _extract_construct_body(class_code: str) -> str:
    """Extract the body of construct() from a Scene class definition.

    Given:
        class Segment01Intro(Scene):
            def construct(self):
                title = Text("Hello")
                self.play(Write(title))

    Returns the indented body lines (at 8-space indent for the combined class):
                title = Text("Hello")
                self.play(Write(title))
    """
    # Remove import/config lines the model might have included despite instructions
    skip_patterns = [
        re.compile(r'^\s*from manim import'),
        re.compile(r'^\s*import numpy'),
        re.compile(r'^\s*import manim'),
        re.compile(r'^\s*config\.\w+\s*='),
    ]

    filtered = []
    for line in class_code.split("\n"):
        if any(p.match(line) for p in skip_patterns):
            continue
        filtered.append(line)

    # Find the construct method and extract its body
    in_construct = False
    construct_indent = None
    body_lines = []

    for line in filtered:
        # Detect def construct(self):
        construct_match = re.match(
            r'^(\s*)def construct\s*\(\s*self\s*\)\s*:', line)
        if construct_match:
            in_construct = True
            construct_indent = len(construct_match.group(1))
            continue

        if in_construct:
            # Check if we've left construct (another def or class at same/lower indent)
            if line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= construct_indent and (
                    line.strip().startswith("def ") or
                    line.strip().startswith("class ")
                ):
                    break
            body_lines.append(line)

    # If extraction failed, use the whole code minus class/def lines
    if not body_lines:
        body_lines = [
            line for line in filtered
            if not re.match(r'^\s*class\s+', line)
            and not re.match(r'^\s*def\s+construct', line)
        ]

    # Strip trailing blank lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)

    if not body_lines:
        return "        pass"

    # Dedent to base level, then re-indent to 8 spaces
    joined = "\n".join(body_lines)
    dedented = textwrap.dedent(joined)

    result_lines = []
    for line in dedented.split("\n"):
        if line.strip():
            result_lines.append("        " + line)
        else:
            result_lines.append("")

    return "\n".join(result_lines)
