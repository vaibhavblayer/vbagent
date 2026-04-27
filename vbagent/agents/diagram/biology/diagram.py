"""Biology diagram generation using gpt-image-2 via the Responses API.

Biology diagrams (cells, organisms, anatomical structures, life cycles, etc.)
are organic and curved — TikZ is the wrong tool. This agent calls the
OpenAI Responses API with the image_generation tool (backed by gpt-image-2)
to generate a PNG and returns a \\includegraphics LaTeX snippet.

API: client.responses.create(model="gpt-5.5", tools=[{"type": "image_generation"}])
The image_generation tool uses gpt-image-2 internally.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BiologyDiagramResult:
    """Result from biology diagram generation."""
    image_path: str          # Absolute path to saved PNG
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
    """Generate a biology diagram using gpt-image-2 via the Responses API.

    Args:
        description: What to draw (e.g. "cross-section of a mitochondrion")
        output_path: Where to save the PNG (e.g. agentic/diagrams/problem_10.png)
        image_path: Optional source image for reference
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
        console.print(f"[cyan]Generating biology diagram:[/cyan] {description[:80]}...")

    t0 = time.time()

    try:
        # Use the Responses API with image_generation tool.
        # gpt-image-2 is the model behind the image_generation tool.
        # The mainline model (gpt-5.5) orchestrates; the tool generates the image.
        response = client.responses.create(
            model="gpt-5.5",
            input=prompt,
            tools=[{
                "type": "image_generation",
                "quality": "high",
                "size": "1024x1024",
            }],
        )

        # Extract the generated image from the response output
        image_data = None
        for output in response.output:
            if output.type == "image_generation_call":
                image_data = output.result
                break

        if not image_data:
            raise ValueError("No image_generation_call found in response output")

        # Decode and save the PNG
        png_bytes = base64.b64decode(image_data)
        output_path.write_bytes(png_bytes)

        elapsed = time.time() - t0
        if show_spinner:
            console.print(f"[green]✓ Biology diagram saved in {elapsed:.1f}s:[/green] {output_path}")

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
        "Scientific biology textbook illustration. "
        "Clean white background. "
        "Accurate biological structures with smooth organic curves. "
        "Clear sans-serif labels in black. "
        "No artistic style, no shadows, no gradients. "
        "Textbook quality, suitable for NEET/JEE biology. "
        f"Draw: {description}."
    )

    if labels:
        label_str = ", ".join(labels)
        prompt += f" Label the following structures clearly: {label_str}."

    if context:
        prompt += f" Context: {context}."

    prompt += (
        " Use thin black outlines. "
        "Organelles and structures should be anatomically accurate. "
        "No decorative elements."
    )

    return prompt


def _build_latex_include(image_path: Path) -> str:
    """Build a \\includegraphics LaTeX snippet for the saved image."""
    try:
        rel_path = image_path.relative_to(Path.cwd())
        path_str = str(rel_path)
    except ValueError:
        path_str = str(image_path)

    return (
        "\\begin{center}\n"
        f"    \\includegraphics[width=0.75\\linewidth]{{{path_str}}}\n"
        "\\end{center}"
    )
