"""MCQ Option Diagram Coordinator.

Generates all MCQ option diagrams by routing to the appropriate
specialized agent via the standard TikZ router. The agent's system
prompt provides domain expertise (gates, circuits, graphs, organic
structures, etc.) while the user message includes MCQ-option
formatting instructions.
"""

from typing import Optional

# MCQ option format instructions prepended to the description
_OPTION_FORMAT = """OUTPUT FORMAT — MCQ option diagrams:
Generate exactly {n} option diagrams. Each MUST be a \\def\\Option{letters} command
containing a compact \\begin{{tikzpicture}} ... \\end{{tikzpicture}}.

Requirements for each option tikzpicture:
- Use scale=0.8 (or smaller if needed to fit)
- Add baseline=(current bounding box.center) so options align with text
- Keep diagrams compact — these sit inside a tasks environment
- Label inputs/outputs clearly

Example skeleton:
\\def\\OptionA{{%
\\begin{{tikzpicture}}[scale=0.8, baseline=(current bounding box.center)]
  ... diagram code ...
\\end{{tikzpicture}}}}

Output ALL {n} definitions consecutively with NO other text.

---

"""


def _build_option_description(
    option_descriptions: Optional[list[str]],
    num_options: int,
) -> str:
    """Build the MCQ format prefix + per-option descriptions."""
    letters = [chr(65 + i) for i in range(num_options)]  # A, B, C, ...
    letter_list = ", ".join(letters)

    header = _OPTION_FORMAT.format(n=num_options, letters=letter_list)

    if option_descriptions:
        lines = []
        for i, desc in enumerate(option_descriptions[:num_options]):
            lines.append(f"({letters[i]}) {desc}")
        header += "\n".join(lines)
    else:
        header += f"Generate {num_options} distinct option diagrams based on the image."

    return header


def generate_mcq_options(
    image_path: str,
    subject: str,
    option_diagram_type: str,
    option_descriptions: Optional[list[str]] = None,
    diagram_analysis: Optional[dict] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate MCQ option diagrams using the appropriate specialized agent.

    Routes through the standard TikZ router so every diagram type
    (gates, circuits, graphs, organic structures, etc.) uses its
    specialized agent with MCQ-option formatting instructions.

    Args:
        image_path: Path to problem image
        subject: Subject (physics, chemistry, mathematics)
        option_diagram_type: Type of diagrams in options
        option_descriptions: Per-option descriptions from classifier
        diagram_analysis: Full diagram analysis dict
        use_context: Whether to use reference context
        show_spinner: Whether to show progress spinner

    Returns:
        String with \\def\\OptionA{...}\\def\\OptionB{...} etc.
    """
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing

    # Determine number of options
    num_options = 4
    if diagram_analysis and isinstance(diagram_analysis, dict):
        num_options = diagram_analysis.get("num_option_diagrams", 4)
    elif diagram_analysis and hasattr(diagram_analysis, "num_option_diagrams"):
        num_options = diagram_analysis.num_option_diagrams
    num_options = max(2, min(num_options, 6))  # clamp 2–6

    # Trim descriptions to actual count
    if option_descriptions and len(option_descriptions) > num_options:
        option_descriptions = option_descriptions[:num_options]

    # Build description with MCQ format instructions
    description = _build_option_description(option_descriptions, num_options)

    # Route through the standard TikZ router — picks the right
    # specialized agent (gates, circuit, graph, organic_structure, etc.)
    # IMPORTANT: Pass mcq_options=True so agents generate \def\OptionA{...} format
    tikz_code, _agent_used = generate_tikz_with_routing(
        image_path=image_path,
        description=description,
        diagram=None,
        primary=None,
        use_context=use_context,
        show_spinner=show_spinner,
        subject=subject,
        diagram_type=option_diagram_type,
        mcq_options=True,  # This tells agents to generate \def\OptionA{...} format
    )
    return tikz_code
