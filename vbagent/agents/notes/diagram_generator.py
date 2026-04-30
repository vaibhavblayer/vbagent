"""Diagram generator — uses existing tikz agent to generate diagrams for notes."""

from __future__ import annotations

from pathlib import Path

from vbagent.agents.notes.models import DiagramSpec


def generate_diagram(
    spec: DiagramSpec,
    output_dir: str | Path,
    show_spinner: bool = True,
) -> str:
    """Generate a TikZ diagram using the existing tikz agent.

    Args:
        spec: Diagram specification from the planner.
        output_dir: Directory to save the .tex file.
        show_spinner: Show progress spinner.

    Returns:
        Path to the generated .tex file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    tex_path = out_path / f"{spec.diagram_id}.tex"

    if spec.diagram_type == "pgfplot":
        # pgfplots are formulaic — generate directly without the tikz agent
        code = _generate_pgfplot(spec)
    else:
        # Use the existing tikz agent
        from vbagent.agents.diagram.tikz import generate_tikz
        code = generate_tikz(
            description=spec.description,
            show_spinner=show_spinner,
        )

    tex_path.write_text(code, encoding="utf-8")
    return str(tex_path)


def _generate_pgfplot(spec: DiagramSpec) -> str:
    """Generate a pgfplot from description using the tikz agent.

    For pgfplots, we still use the tikz agent but with a pgfplot-specific
    description prefix so it knows to use pgfplots syntax.
    """
    from vbagent.agents.diagram.tikz import generate_tikz

    description = (
        f"Generate a pgfplots chart (using \\begin{{tikzpicture}} and "
        f"\\begin{{axis}}...\\end{{axis}}). "
        f"{spec.description}"
    )

    return generate_tikz(
        description=description,
        show_spinner=True,
    )
