"""Notes stitcher — combines preamble, sections, and diagrams into a complete .tex file."""

from __future__ import annotations

from pathlib import Path

from vbagent.agents.notes.models import DocumentPlan, SectionContent


# The preamble template — stable, not LLM-generated
PREAMBLE_TEMPLATE = r"""\documentclass[11pt,a4paper]{{article}}

% ---------- packages ----------
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{amsmath,amssymb}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{tikz}}
\usepackage{{pgfplots}}
\pgfplotsset{{compat=1.18}}
\usetikzlibrary{{arrows.meta,decorations.pathreplacing,calc,patterns,positioning,intersections}}
\usepackage{{booktabs}}
\usepackage{{xcolor}}
\usepackage{{caption}}
\usepackage{{enumitem}}
\usepackage{{hyperref}}
\hypersetup{{colorlinks=true,linkcolor=blue!60!black,urlcolor=blue!60!black}}

% ---------- tikz styles ----------
\tikzset{{
  ray/.style       = {{-{{Stealth[length=2.2mm]}}, red!75!black, thick}},
  faintray/.style  = {{red!50, dashed, thick}},
  wavearrow/.style = {{-{{Stealth[length=2mm]}}, blue!70!black, thick}},
  axis line/.style = {{dashed, gray!70}},
  barrier/.style   = {{fill=black}},
  screen/.style    = {{ultra thick, black}},
  slab/.style      = {{pattern=north east lines, pattern color=cyan!70!black, draw=cyan!70!black, thick}}
}}

% ---------- title ----------
\title{{\textbf{{{title}}}\\[2pt]\large {subtitle}}}
\author{{{author}}}
\date{{\today}}

\begin{{document}}
\maketitle
\tableofcontents
\bigskip
\hrule
\bigskip
"""

DOCUMENT_END = r"""
\end{document}
"""


def stitch_notes(
    plan: DocumentPlan,
    section_contents: list[SectionContent],
    output_path: str | Path,
    diagrams_dir: str = "diagrams",
) -> str:
    """Combine all parts into a complete .tex file.

    Args:
        plan: The document plan (for title, author, etc.).
        section_contents: LaTeX content for each section (in order).
        output_path: Path to write the .tex file.
        diagrams_dir: Relative path to diagrams directory (for \\input paths).

    Returns:
        Path to the generated .tex file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build preamble
    preamble = PREAMBLE_TEMPLATE.format(
        title=_escape_latex(plan.title),
        subtitle=_escape_latex(plan.subtitle),
        author=_escape_latex(plan.author),
    )

    # Combine sections with separators
    body_parts = []
    for i, sc in enumerate(section_contents):
        if i > 0:
            body_parts.append(r"\bigskip")
            body_parts.append(r"\hrule")
            body_parts.append(r"\bigskip")
            body_parts.append("")

        body_parts.append(sc.latex)
        body_parts.append("")

    body = "\n".join(body_parts)

    # Full document
    document = preamble + "\n" + body + "\n" + DOCUMENT_END

    output_path.write_text(document, encoding="utf-8")
    return str(output_path)


def _escape_latex(text: str) -> str:
    """Minimal LaTeX escaping for title/author fields."""
    # Don't escape backslashes or braces — they might be intentional LaTeX
    # Only escape characters that would break in a title context
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("#", r"\#")
    return text
