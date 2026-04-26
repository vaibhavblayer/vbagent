"""Generate a compact revision-sheet LaTeX document.

The model outputs complete itemize blocks per topic — we just stitch them
together with topic headers and a preamble.
"""


def generate_brief_latex(
    revision_data: dict,
    exam: str,
    year_label: str | None,
    subject: str,
    chapter_name: str,
    num_problems: int,
) -> str:
    """Generate a concise one-glance revision sheet in LaTeX.

    Args:
        revision_data: {topic_name: latex_string, ...}
        exam: Exam display name
        year_label: Year string (e.g. "2026", "2024--2026", or None)
        subject: Subject name
        chapter_name: Chapter name
        num_problems: Number of problems analyzed

    Returns:
        Complete LaTeX document string
    """
    doc = _preamble()
    doc += _title(exam, year_label, subject, chapter_name, num_problems)

    for topic_name, latex in revision_data.items():
        if not latex or not latex.strip():
            continue
        short = topic_name.split(",")[0].strip()
        doc += f"\\subsection*{{{short}}}\n\n"
        doc += latex.strip() + "\n\n"

    doc += "\\end{multicols}\n"
    doc += "\\end{document}\n"
    return doc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _preamble() -> str:
    return r"""\documentclass[9pt]{extarticle}
\usepackage[a4paper, margin=1.2cm]{geometry}
\usepackage{amsmath, amssymb, mathtools}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{multicol}
\usepackage{titlesec}
\everymath{\displaystyle}

% Compact spacing
\setlength{\parindent}{0pt}
\setlength{\parskip}{2pt}
\setlength{\columnsep}{12pt}
\setlength{\columnseprule}{0.3pt}

% Redefine subsection*: small-caps, slightly larger, no bold
\titleformat{\subsection}[block]{\normalfont\normalsize\scshape}{}{0pt}{$^\ast$\enspace}
\titlespacing*{\subsection}{0pt}{8pt}{3pt}

\pagestyle{empty}

"""


def _title(exam: str, year_label: str | None, subject: str, chapter_name: str, num_problems: int) -> str:
    exam_display = exam.replace("_", " ").title()
    subj_display = subject.capitalize()
    # Build first line: "Jee Main 2024--2026 — Physics" or "Neet — Physics"
    if year_label:
        first_line = f"{exam_display} {year_label} — {subj_display}"
    else:
        first_line = f"{exam_display} — {subj_display}"
    return (
        f"\\begin{{document}}\n"
        f"\\begin{{center}}\n"
        f"{{\\large\\textsc{{{first_line}}}}}\\\\\n"
        f"{{\\textsc{{{chapter_name}}}}} "
        f"\\quad {{\\small\\color{{gray}}({num_problems} problems analyzed)}}\n"
        f"\\end{{center}}\n"
        f"\\vspace{{4pt}}\\hrule\\vspace{{6pt}}\n\n"
        f"\\begin{{multicols}}{{2}}\n\n"
    )
