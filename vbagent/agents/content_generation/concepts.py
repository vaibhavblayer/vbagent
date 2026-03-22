"""Concept sheet generation agent.

Aggregates ideas from multiple problems into a deduplicated,
organized concept sheet. Supports JSON and LaTeX output.
"""

import json
import re
from pathlib import Path

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.content import ConceptSheet, IdeaResult
from vbagent.prompts.content_generation.concepts import (
    SYSTEM_PROMPT_JSON,
    SYSTEM_PROMPT_LATEX,
    USER_TEMPLATE_JSON,
    USER_TEMPLATE_LATEX,
    USER_TEMPLATE_FULL,
    USER_TEMPLATE_IDEA_BLOCKS,
)
from vbagent.utils.latex import clean_latex_output


def _format_ideas_text(ideas: dict[str, IdeaResult]) -> str:
    """Format collected ideas into text for the prompt."""
    parts = []
    for name, idea in ideas.items():
        lines = [f"### {name}"]
        if idea.topic:
            lines.append(f"Topic: {idea.topic}")
        if idea.subtopic:
            lines.append(f"Subtopic: {idea.subtopic}")
        if idea.concepts:
            lines.append(f"Concepts: {', '.join(idea.concepts)}")
        if idea.formulas:
            lines.append(f"Formulas: {', '.join(idea.formulas)}")
        if idea.techniques:
            lines.append(f"Techniques: {', '.join(idea.techniques)}")
        if idea.difficulty_factors:
            lines.append(f"Difficulty: {', '.join(idea.difficulty_factors)}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _format_full_content(scans: dict[str, str]) -> str:
    """Format full scan content for the prompt."""
    parts = []
    for name, content in scans.items():
        parts.append(f"=== {name} ===\n{content}")
    return "\n\n".join(parts)


def _format_idea_blocks(idea_blocks: dict[str, str]) -> str:
    """Format extracted idea blocks for the prompt."""
    parts = []
    for name, block in idea_blocks.items():
        parts.append(f"--- From {name} ---\n{block}")
    return "\n\n".join(parts)


def collect_ideas(ideas_dir: Path) -> dict[str, IdeaResult]:
    """Collect all IdeaResult JSONs from the ideas directory."""
    ideas = {}
    for f in sorted(ideas_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            ideas[f.stem] = IdeaResult.model_validate(data)
        except Exception:
            continue
    return ideas


def collect_scans(scans_dir: Path) -> dict[str, str]:
    """Collect all scanned .tex files."""
    scans = {}
    for f in sorted(scans_dir.glob("*.tex")):
        try:
            scans[f.stem] = f.read_text()
        except Exception:
            continue
    return scans


def collect_idea_blocks(scans_dir: Path) -> dict[str, str]:
    """Extract only \\begin{idea}...\\end{idea} blocks from scanned .tex files.

    Returns dict of filename stem -> idea block content.
    Files without idea environments are skipped.
    """
    pattern = re.compile(
        r"(\\begin\{idea\}.*?\\end\{idea\})",
        re.DOTALL,
    )
    blocks = {}
    for f in sorted(scans_dir.glob("*.tex")):
        try:
            content = f.read_text()
            matches = pattern.findall(content)
            if matches:
                blocks[f.stem] = "\n\n".join(matches)
        except Exception:
            continue
    return blocks


_concept_diagram_tool = None


def _get_concept_diagram_tool():
    """Get the generate_concept_diagram function tool (lazy-loaded)."""
    global _concept_diagram_tool
    if _concept_diagram_tool is None:
        from agents import function_tool

        @function_tool
        def generate_concept_diagram(description: str) -> str:
            """Generate a TikZ diagram for a concept in the revision sheet.

            Use this when a concept genuinely benefits from a visual
            (field lines, force diagrams, circuit topology, geometric constructions, etc.).

            Args:
                description: Clear description of what the diagram should show.
                    Example: "Electric field lines between two point charges (dipole pattern)"

            Returns:
                TikZ code wrapped in \\begin{center}...\\end{center}, ready to insert.
            """
            try:
                from vbagent.agents.diagram.tikz import generate_tikz
                tikz_code = generate_tikz(
                    description=f"Simple conceptual diagram for a revision sheet: {description}. "
                                "Keep it minimal and schematic — no colors, no fills, clean lines only.",
                    show_spinner=True,
                )
                if not tikz_code or not tikz_code.strip():
                    return "% Diagram generation failed"
                code = tikz_code.strip()
                if r"\begin{center}" not in code:
                    code = f"\\begin{{center}}\n{code}\n\\end{{center}}"
                return code
            except Exception as e:
                return f"% Diagram generation failed: {e}"

        _concept_diagram_tool = generate_concept_diagram
    return _concept_diagram_tool


def generate_concepts_json(
    ideas: dict[str, IdeaResult],
    subject: str = "physics",
    full_scans: dict[str, str] | None = None,
    idea_blocks: dict[str, str] | None = None,
) -> ConceptSheet:
    """Generate a structured concept sheet from collected ideas."""
    agent = create_agent(
        name="ConceptSheet",
        instructions=SYSTEM_PROMPT_JSON,
        output_type=ConceptSheet,
        agent_type="idea",
    )

    if idea_blocks:
        message = USER_TEMPLATE_IDEA_BLOCKS.format(
            count=len(idea_blocks),
            subject=subject,
            idea_text=_format_idea_blocks(idea_blocks),
        )
    elif full_scans:
        message = USER_TEMPLATE_FULL.format(
            count=len(full_scans),
            subject=subject,
            content_text=_format_full_content(full_scans),
        )
    else:
        message = USER_TEMPLATE_JSON.format(
            count=len(ideas),
            subject=subject,
            ideas_text=_format_ideas_text(ideas),
        )

    return run_agent_sync(agent, message)


def generate_concepts_latex(
    ideas: dict[str, IdeaResult],
    subject: str = "physics",
    full_scans: dict[str, str] | None = None,
    idea_blocks: dict[str, str] | None = None,
) -> str:
    """Generate a LaTeX concept sheet from collected ideas.

    The agent has access to a generate_concept_diagram tool for TikZ diagrams.
    """
    tool = _get_concept_diagram_tool()
    agent = create_agent(
        name="ConceptSheetLaTeX",
        instructions=SYSTEM_PROMPT_LATEX,
        tools=[tool],
        agent_type="idea",
    )

    if idea_blocks:
        message = USER_TEMPLATE_IDEA_BLOCKS.format(
            count=len(idea_blocks),
            subject=subject,
            idea_text=_format_idea_blocks(idea_blocks),
        )
    elif full_scans:
        message = USER_TEMPLATE_FULL.format(
            count=len(full_scans),
            subject=subject,
            content_text=_format_full_content(full_scans),
        )
    else:
        message = USER_TEMPLATE_LATEX.format(
            count=len(ideas),
            subject=subject,
            ideas_text=_format_ideas_text(ideas),
        )

    raw = run_agent_sync(agent, message)
    return clean_latex_output(raw)


def concept_sheet_to_latex(sheet: ConceptSheet, subject: str = "physics") -> str:
    """Convert a ConceptSheet JSON model to LaTeX.

    Uses itemize + align* formatting with \\hfill [N]\\\\ and \\textit{}.
    Generates TikZ diagrams for entries that need them.
    Appends a TikZ mindmap at the end.
    """
    lines = [f"\\section*{{{sheet.title}}}", ""]

    for group in sheet.groups:
        lines.append(f"\\subsection*{{{group.subtopic}}}")
        lines.append("\\begin{itemize}")
        for entry in group.entries:
            lines.append(f"\\item {entry.name} \\hfill [{entry.frequency}]\\\\")
            if entry.description:
                lines.append(f"\\textit{{{entry.description}}}")
            if entry.formulas:
                lines.append("    \\begin{align*}")
                for i, f in enumerate(entry.formulas):
                    formula = f.strip().strip("$").strip()
                    suffix = " \\\\" if i < len(entry.formulas) - 1 else ""
                    lines.append(f"    {formula}{suffix}")
                lines.append("    \\end{align*}")
            # Generate TikZ diagram if requested
            if entry.needs_diagram and entry.diagram_description:
                tikz = _generate_concept_diagram(entry.diagram_description, subject)
                if tikz:
                    lines.append(tikz)
        lines.append("\\end{itemize}")
        lines.append("")

    # Mindmap
    group_names = [g.subtopic for g in sheet.groups]
    if len(group_names) >= 2:
        lines.append(_build_mindmap(sheet.title or sheet.topic, group_names))

    return "\n".join(lines)


def _generate_concept_diagram(description: str, subject: str = "physics") -> str:
    """Generate a TikZ diagram for a concept using the TikZ agent.

    Returns the diagram wrapped in \\begin{center}...\\end{center},
    or empty string on failure.
    """
    try:
        from vbagent.agents.diagram.tikz import generate_tikz
        tikz_code = generate_tikz(
            description=f"Simple conceptual diagram for a revision sheet: {description}. "
                        "Keep it minimal and schematic — no colors, no fills, clean lines only.",
            show_spinner=True,
        )
        if not tikz_code or not tikz_code.strip():
            return ""
        # Ensure it's wrapped in center
        code = tikz_code.strip()
        if r"\begin{center}" not in code:
            code = f"\\begin{{center}}\n{code}\n\\end{{center}}"
        return code
    except Exception:
        return ""


def _build_mindmap(center_label: str, group_names: list[str]) -> str:
    """Build a TikZ mindmap from group names."""
    import math

    n = len(group_names)
    radius = 3.5
    nodes = []
    edges_center = []
    positions = []

    for i, name in enumerate(group_names):
        angle = 90 + i * (360 / n)
        x = radius * math.cos(math.radians(angle))
        y = radius * math.sin(math.radians(angle))
        node_id = f"g{i+1}"
        positions.append((node_id, x, y, name))
        nodes.append(
            f"\\node[topic] ({node_id}) at ({x:.1f},{y:.1f}) {{{name}}};"
        )
        edges_center.append(f"\\draw[->] (center) -- ({node_id});")

    tikz_lines = [
        "",
        "\\begin{center}",
        "\\begin{tikzpicture}[",
        "    topic/.style={draw, rounded corners, minimum width=2.5cm, minimum height=0.8cm, align=center, font=\\small},",
        "    >=Stealth",
        "]",
        f"\\node[topic] (center) at (0,0) {{{center_label}}};",
    ]
    tikz_lines.extend(nodes)
    tikz_lines.extend(edges_center)
    tikz_lines.append("\\end{tikzpicture}")
    tikz_lines.append("\\end{center}")
    tikz_lines.append("")

    return "\n".join(tikz_lines)
