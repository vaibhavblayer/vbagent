"""Generate LaTeX document from analysis data."""


def generate_analysis_latex(
    matched_data: dict,
    aggregated_ideas: dict,
    exam: str,
    year: str | int | None,
    subject: str,
    chapter_name: str,
    num_problems: int,
    chapter_note: str = None
) -> str:
    """Generate complete LaTeX document for exam analysis.
    
    Args:
        matched_data: Output from match_problems_to_syllabus
        aggregated_ideas: Output from aggregate_ideas_by_topic
        exam: Exam name (JEE Main, NEET, etc.)
        year: Exam year
        subject: Subject name
        chapter_name: Chapter being analyzed
        num_problems: Total number of problems
        chapter_note: Optional conceptual note about the chapter
        
    Returns:
        Complete LaTeX document as string
    """
    # Get chapter data
    chapter_data = matched_data.get(chapter_name, {})
    # aggregated_ideas is already organized by topic (from agent)
    chapter_ideas = aggregated_ideas
    
    # Build document
    doc = _generate_preamble()
    doc += _generate_title(exam, year, subject)
    doc += _generate_syllabus_box(chapter_name, chapter_data)
    if chapter_note:
        doc += _generate_note_box(chapter_note)
    doc += _generate_ideas_section(chapter_name, chapter_ideas)
    doc += _generate_problems_section(num_problems)
    doc += "\\end{document}\n"
    
    return doc


def _generate_preamble() -> str:
    """Generate LaTeX preamble with all packages and custom commands."""
    return r"""\documentclass[8pt]{extarticle}
\usepackage{tikz, tasks, geometry, xcolor}
\usepackage[most]{tcolorbox}
\usetikzlibrary{arrows.meta, patterns, calc, intersections, quotes, angles}
\usepackage{amsmath, amssymb, amsfonts, mathtools}
\setlength{\columnsep}{10pt}
\setlength{\columnseprule}{0.4pt}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\geometry{a4paper, margin=1.5cm}
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}
\usepackage{chemfig}
\usepackage[version=4]{mhchem}
\usepackage[modules=all]{chemmacros}
\usepackage{tkz-euclide}
\usepackage{venndiagram}
\pgfplotsset{compat=1.18}
\everymath{\displaystyle}

\newcommand{\ans}{\textcolor{blue!20!red}{\textit{\quad Ans.}}}
% \renewcommand{\ans}{}  % Uncomment to hide answers

\newenvironment{solution}{\par\noindent\color{red!80!black}$\Rightarrow$\enspace\ignorespaces}{\par}
\newenvironment{alternatesolution}{\par\noindent\color{blue!80!black}$\Rrightarrow$\enspace\ignorespaces}{\par}
\newenvironment{hint}{\par\noindent\color{red!50!black}$\looparrowright$\enspace\ignorespaces}{\par}
\newenvironment{idea}{\par\noindent\color{violet!80!black}$\diamond$\enspace\ignorespaces}{\par}
\newenvironment{remark}{\par\noindent\color{teal!80!black}$\circ$\enspace\ignorespaces}{\par}

% --- Global TikZ style (design uniformity across all diagrams) ---
\tikzset{
  >=latex,
  thick,
  every node/.append style={font=\small},
}

\newtcolorbox{syllabusbox}[1][]{
  colback=white,
  colframe=black,
  fonttitle=\scshape,
  title={Syllabus : #1},
  title style={left=0pt},
  boxrule=0pt,
  arc=4pt,
  left=6pt, right=6pt, top=6pt, bottom=6pt,
  before upper=\itshape
}

"""


def _generate_title(exam: str, year: str | int | None, subject: str) -> str:
    """Generate title section."""
    exam_display = exam.replace('_', ' ').title()
    subject_display = subject.capitalize()
    
    if year:
        title_text = f"{exam_display} : {year} --- {subject_display}"
    else:
        title_text = f"{exam_display} --- {subject_display}"
    
    return f"""\\title{{\\textsc{{{title_text}}}}}
\\begin{{document}}
\\maketitle

"""


def _generate_syllabus_box(chapter_name: str, chapter_data: dict) -> str:
    """Generate syllabus box with problem references."""
    description = chapter_data.get('description', '')
    topics = chapter_data.get('topics', [])
    
    content = f"\\begin{{syllabusbox}}[{chapter_name}]\n"
    
    # Add topics as comma-separated list (just topic names, no problem refs here)
    topic_texts = [topic_data['topic'] for topic_data in topics]
    content += ', '.join(topic_texts)
    
    # Add description/note on new line
    if description:
        content += f"\\par\n\\textcolor{{black!85}}{{{description}}}\n"
    
    content += "\\end{syllabusbox}\n\n"
    
    return content


def _generate_note_box(note: str) -> str:
    """Generate a note box with conceptual framework."""
    content = "\\begin{tcolorbox}[colback=yellow!5!white,colframe=orange!75!black,title=\\textsc{A Note on Mechanics}]\n"
    content += "\\small\\itshape\n"
    content += note
    content += "\n\\end{tcolorbox}\n\n"
    return content


def _generate_ideas_section(chapter_name: str, chapter_ideas: dict) -> str:
    """Generate key concepts and ideas section.
    
    Args:
        chapter_ideas: Organized concepts from agent (topic_name -> {concepts, formulas, techniques})
    """
    content = "\\section*{Key Concepts \\& Ideas}\n\n"
    
    # Iterate through topics
    for topic_name, topic_data in chapter_ideas.items():
        concepts = topic_data.get('concepts', [])
        formulas = topic_data.get('formulas', [])
        techniques = topic_data.get('techniques', [])
        
        # Skip if no content
        if not (concepts or formulas or techniques):
            continue
        
        # Shorten topic name for subsection (first part before comma)
        topic_short = topic_name.split(',')[0].strip()
        content += f"\\subsection*{{{topic_short}}}\n"
        content += "\\begin{itemize}\n"
        
        # Add concepts
        for concept in concepts:
            text = concept['text']
            problems = concept.get('problems', [])
            sub_items = concept.get('sub_items', [])
            text_clean = _clean_latex_text(text)
            
            if problems:
                problem_refs = ', '.join(str(p) for p in sorted(problems))
                content += f"\\item {text_clean} \\hfill [Problem: {problem_refs}]\n"
            else:
                content += f"\\item {text_clean}\n"
            
            # Add nested sub-items
            if sub_items:
                content += "\\begin{itemize}\n"
                for sub in sub_items:
                    sub_clean = _clean_latex_text(sub)
                    content += f"\\item {sub_clean}\n"
                content += "\\end{itemize}\n"
        
        # Add formulas
        for formula in formulas:
            latex_formula = formula['latex']
            description = formula.get('description', '')
            problems = formula.get('problems', [])
            latex_clean = _clean_latex_text(latex_formula)
            desc_clean = _clean_latex_text(description)
            
            if problems:
                problem_refs = ', '.join(str(p) for p in sorted(problems))
                if desc_clean:
                    content += f"\\item ${latex_clean}$ --- {desc_clean} \\hfill [Problem: {problem_refs}]\n"
                else:
                    content += f"\\item ${latex_clean}$ \\hfill [Problem: {problem_refs}]\n"
            else:
                if desc_clean:
                    content += f"\\item ${latex_clean}$ --- {desc_clean}\n"
                else:
                    content += f"\\item ${latex_clean}$\n"
        
        # Add techniques
        for technique in techniques:
            text = technique['text']
            problems = technique.get('problems', [])
            sub_items = technique.get('sub_items', [])
            text_clean = _clean_latex_text(text)
            
            if problems:
                problem_refs = ', '.join(str(p) for p in sorted(problems))
                content += f"\\item {text_clean} \\hfill [Problem: {problem_refs}]\n"
            else:
                content += f"\\item {text_clean}\n"
            
            # Add nested sub-items
            if sub_items:
                content += "\\begin{itemize}\n"
                for sub in sub_items:
                    sub_clean = _clean_latex_text(sub)
                    content += f"\\item {sub_clean}\n"
                content += "\\end{itemize}\n"
        
        content += "\\end{itemize}\n\n"
    
    content += "\\pagebreak\n\n"
    return content


def _generate_problems_section(num_problems: int) -> str:
    """Generate two-column problems section with foreach loop."""
    content = "\\twocolumn\n"
    content += "\\begin{enumerate}\n"
    content += f"\\foreach \\i in {{1,...,{num_problems}}} {{\n"
    content += "  \\input{agentic/scans/problem_\\i.tex}\n"
    content += "}\n"
    content += "\\end{enumerate}\n"
    
    return content


def _clean_latex_text(text: str) -> str:
    """Clean LaTeX text for safe inclusion.
    
    Args:
        text: Raw text that may contain LaTeX commands
        
    Returns:
        Cleaned text
    """
    import re
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove trailing backslashes
    text = re.sub(r'\\+$', '', text)
    
    # Remove \intertext commands
    text = re.sub(r'\\intertext\{([^}]+)\}', r'\1', text)
    
    return text.strip()
