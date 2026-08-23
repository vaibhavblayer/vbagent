"""Shared helpers for interactive TikZ quality-check sessions."""

from pathlib import Path
from typing import Optional

def _generate_tikz_for_placeholder(
    content: str,
    image_path: Optional[Path],
    diagram_type: Optional[str] = None,
    extra_prompt: Optional[str] = None,
    console = None,
) -> Optional[str]:
    """Generate TikZ code and replace \\input{diagram} placeholder.

    Uses the TikZ generator agent to create TikZ code from the problem
    description and optional image, then replaces the placeholder.

    Args:
        content: Full LaTeX content with \\input{diagram} placeholder
        image_path: Optional path to reference image
        diagram_type: Optional diagram type for reference matching
        extra_prompt: Optional additional instructions
        console: Rich console for output (optional)

    Returns:
        Content with placeholder replaced by generated TikZ, or None on failure
    """
    import re
    from vbagent.agents.diagram.tikz import generate_tikz, validate_tikz_output
    from vbagent.pipeline.io import replace_main_diagram_placeholder

    # Extract problem description for the generator
    # Try to get the problem statement (before solution)
    problem_match = re.search(r'\\item\s*(.*?)(?=\\begin\{solution\}|$)', content, re.DOTALL)
    if problem_match:
        description = problem_match.group(1).strip()
        # Clean up LaTeX commands for description
        description = re.sub(r'\\begin\{center\}.*?\\end\{center\}', '', description, flags=re.DOTALL)
        description = description.strip()
    else:
        description = "Generate a physics diagram based on the problem context."

    # Add extra prompt if provided
    if extra_prompt:
        description = f"{description}\n\nAdditional instructions: {extra_prompt}"

    if console:
        console.print("[dim]Generating TikZ... (Ctrl+C to quit)[/dim]")

    # Generate TikZ code
    tikz_code = generate_tikz(
        description=description,
        image_path=str(image_path) if image_path else None,
        use_context=True,
    )

    if not tikz_code or not validate_tikz_output(tikz_code):
        return None

    # Wrap in center environment if not already wrapped
    if not tikz_code.strip().startswith(r'\begin{center}'):
        tikz_code = f"\\begin{{center}}\n{tikz_code}\n\\end{{center}}"

    result = replace_main_diagram_placeholder(content, tikz_code)

    return result if result != content else None
