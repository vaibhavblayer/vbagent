"""Biology diagram generation using gpt-image-2 directly via the Images API.

Biology diagrams (cells, organisms, anatomical structures, life cycles, etc.)
are organic and curved — TikZ is the wrong tool. This agent calls
client.images.generate(model="gpt-image-2") directly and returns a
\\includegraphics LaTeX snippet.

Model is fixed to gpt-image-2 regardless of vbagent config — this is an
image generation model, not a chat model, and cannot be swapped via
`vbagent config set default`.

API: POST /v1/images/generations
  model: gpt-image-2
  quality: high | medium | low
  size: 1024x1024 (or other valid sizes)
  Returns: response.data[0].b64_json (base64-encoded PNG)
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# gpt-image-2 is the fixed model for biology diagrams.
# It cannot be changed via vbagent config — image generation requires
# a dedicated image model, not a chat/reasoning model.
BIOLOGY_DIAGRAM_MODEL = "gpt-image-2"


@dataclass
class BiologyDiagramResult:
    """Result from biology diagram generation."""
    image_path: str          # Path to saved PNG
    latex_include: str       # Ready-to-use LaTeX snippet
    description: str         # What was generated
    success: bool = True
    error: str = ""


def generate_biology_diagram(
    description: str,
    output_path: Path,
    image_path: Optional[str] = None,
    labels: Optional[list[str]] = None,
    context: Optional[str] = None,
    show_spinner: bool = True,
) -> BiologyDiagramResult:
    """Generate a biology diagram using gpt-image-2.

    Uses the OpenAI Images API directly. The model is fixed to gpt-image-2
    regardless of the vbagent config setting.

    Args:
        description: What to draw (e.g. "cross-section of a mitochondrion")
        output_path: Where to save the PNG (e.g. agentic/diagrams/problem_10.png)
        image_path: Optional source image for reference (not used currently)
        labels: List of labels that must appear in the diagram
        context: Additional biological context
        show_spinner: Show progress indicator

    Returns:
        BiologyDiagramResult with image_path and latex_include
    """
    import os
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = _build_prompt(description, labels, context)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if show_spinner:
        from rich.console import Console
        console = Console()
        console.print(
            f"[cyan]Generating biology diagram[/cyan] "
            f"[dim](model: {BIOLOGY_DIAGRAM_MODEL})[/dim]"
        )
        console.print(f"[dim]{description[:100]}[/dim]")

    t0 = time.time()

    try:
        # Direct Images API call — gpt-image-2 returns b64_json by default.
        # Do NOT pass response_format — it is not supported by gpt-image-2.
        response = client.images.generate(
            model=BIOLOGY_DIAGRAM_MODEL,
            prompt=prompt,
            size="480x480",
            quality="high",
            n=1,
        )

        image_data = response.data[0].b64_json
        if not image_data:
            raise ValueError("gpt-image-2 returned no image data")

        png_bytes = base64.b64decode(image_data)
        output_path.write_bytes(png_bytes)

        elapsed = time.time() - t0
        if show_spinner:
            console.print(
                f"[green]✓ Biology diagram saved in {elapsed:.1f}s:[/green] {output_path}"
            )

        latex_include = _build_latex_include(output_path)

        return BiologyDiagramResult(
            image_path=str(output_path),
            latex_include=latex_include,
            description=description,
            success=True,
        )

    except Exception as e:
        elapsed = time.time() - t0
        if show_spinner:
            console.print(f"[red]✗ Biology diagram failed in {elapsed:.1f}s:[/red] {e}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()[-500:]}[/dim]")

        return BiologyDiagramResult(
            image_path="",
            latex_include=f"% Biology diagram generation failed: {e}",
            description=description,
            success=False,
            error=str(e),
        )


def _build_prompt(
    description: str,
    labels: Optional[list[str]] = None,
    context: Optional[str] = None,
) -> str:
    """Build an optimized image generation prompt for biology diagrams."""
    prompt = (
        "Clean scientific biology textbook illustration. "
        "White background, thin black outlines, clear sans-serif labels. "
        "Anatomically accurate, textbook quality for NEET/JEE biology. "
        "No artistic style, no shadows, no gradients. "
        f"Draw: {description}."
    )

    if labels:
        prompt += f" Label clearly: {', '.join(labels)}."

    if context:
        prompt += f" Context: {context}."

    return prompt


def _build_latex_include(image_path: Path) -> str:
    """Build a \\includegraphics LaTeX snippet.

    Uses a path relative to the agentic/ directory so the .tex file
    compiles correctly when run from agentic/.
    """
    # Try to make path relative to agentic/ (where .tex files live)
    agentic_dir = Path("agentic")
    try:
        rel_path = image_path.relative_to(agentic_dir)
        path_str = str(rel_path)
    except ValueError:
        # Fall back to relative to cwd
        try:
            path_str = str(image_path.relative_to(Path.cwd()))
        except ValueError:
            path_str = str(image_path)

    return (
        "\\begin{center}\n"
        f"    \\includegraphics[width=0.75\\linewidth]{{{path_str}}}\n"
        "\\end{center}"
    )
