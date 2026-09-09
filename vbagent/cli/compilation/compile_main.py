"""CLI command for generating main LaTeX compilation file.

Generates a main.tex file that compiles all processed problems with proper
preamble, packages, and structure.
"""

import os
import re
from pathlib import Path
from typing import List, Optional

import click

from vbagent.cli.item_selection import item_selection_options, resolve_item_range
from vbagent.utils.latex import DISPLAY_FRACTION_PREAMBLE

from ..common import _get_console

_MISSING_DIAGRAM_PREFIX = "VBAGENT MISSING DIAGRAM: "


def discover_problem_files(scans_dir: Path) -> List[str]:
    """Discover all problem files in scans directory.
    
    Returns list of problem identifiers (e.g., ['problem_1', 'problem_2', ...])
    """
    if not scans_dir.exists():
        return []
    
    tex_files = sorted(scans_dir.glob("*.tex"))
    
    # Extract problem identifiers
    problems = []
    for f in tex_files:
        # Extract number or identifier from filename
        stem = f.stem
        problems.append(stem)
    
    return problems


def natural_sort_key(s: str) -> List:
    """Natural sort key for strings with numbers."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def _assemble_problem_for_compile(
    scans_path: Path,
    problem: str,
) -> tuple[str, bool, bool]:
    """Resolve one scan's generic diagram placeholder for final compilation.

    Returns the problem content, whether a missing-diagram fallback was needed,
    and whether the scan originally contained a diagram placeholder. Matching
    TikZ artifacts live beside ``scans`` in ``tikz``.
    """
    scan_path = scans_path / f"{problem}.tex"
    if not scan_path.exists():
        raise ValueError(f"Problem file not found: {scan_path}")

    from vbagent.pipeline.io import (
        has_main_diagram_placeholder,
        insert_tikz_into_latex,
        replace_main_diagram_placeholder,
    )

    content = scan_path.read_text()
    if not has_main_diagram_placeholder(content):
        return content, False, False

    tikz_path = scans_path.parent / "tikz" / f"{problem}.tex"
    if tikz_path.exists():
        assembled = insert_tikz_into_latex(content, tikz_path.read_text())
        if has_main_diagram_placeholder(assembled):
            raise ValueError(
                f"Could not assemble diagram placeholder in {scan_path} "
                f"using {tikz_path}"
            )
        return assembled, False, True

    fallback = (
        "\\fbox{\\texttt{\\detokenize{[DIAGRAM NOT AVAILABLE: "
        f"{problem}"
        "]}}}"
    )
    return replace_main_diagram_placeholder(content, fallback), True, True


def _missing_diagram_names(content: str) -> list[str]:
    """Extract compile-time diagram fallback names from generated main TeX."""
    pattern = rf"{re.escape(_MISSING_DIAGRAM_PREFIX)}([^\n]+)"
    return re.findall(pattern, content)


def generate_preamble(
    subject: str = "physics",
    title: str = "Problems",
    include_all: bool = False,
    *,
    include_solution: bool = True,
    include_alternate_solution: bool = True,
) -> str:
    """Generate LaTeX preamble based on subject.
    
    Args:
        subject: Subject (physics, chemistry, mathematics)
        title: Document title
        include_all: Include packages for all subjects (for mixed content)
        include_solution: Show solution environments (default True)
        include_alternate_solution: Show alternatesolution environments (default True)
        
    Returns:
        LaTeX preamble string
    """
    # Base packages (common to all subjects)
    base_packages = r"""\documentclass{article}
\usepackage{tikz, tasks, geometry, xcolor}
\usetikzlibrary{arrows.meta, patterns, calc, intersections, quotes, angles}
\usepackage{amsmath, amssymb, amsfonts, mathtools}
\DeclareMathOperator{\cosec}{cosec}
\usepackage{comment, multicol}
\usepackage{multirow}
\setlength{\columnsep}{10pt}
\setlength{\columnseprule}{0.4pt}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\geometry{a4paper, margin=0.65in}"""
    
    # Subject-specific packages
    subject_packages = {
        "physics": r"""
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{tikzphysics}
\usepgfplotslibrary{groupplots}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}""",
        
        "chemistry": r"""
\usepackage{chemfig}
\usepackage[version=4]{mhchem}
\usepackage[modules=all]{chemmacros}
\usepackage{pgfplots}
\usepgfplotslibrary{groupplots}
\pgfplotsset{compat=1.18}""",
        
        "mathematics": r"""
\usepackage{pgfplots, tkz-euclide}
\usepgfplotslibrary{groupplots}
\pgfplotsset{compat=1.18}
\usepackage{venndiagram}"""
    }
    
    # All packages (for mixed content)
    all_packages = r"""
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{tikzphysics}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}
\usepackage{chemfig}
\usepackage[version=4]{mhchem}
\usepackage[modules=all]{chemmacros}
\usepackage{tkz-euclide}
\usepackage{venndiagram}
\usepgfplotslibrary{groupplots}
\pgfplotsset{compat=1.18}"""
    
    # Custom commands
    custom_commands = r"""
\everymath{\displaystyle}
\newcommand{\ans}{\textcolor{blue!20!red}{\textit{\quad Ans.}}}
\renewcommand{\ans}{}
\newcommand{\ansint}[1]{\textcolor{red!95}{#1}}
\newenvironment{solution}{\par\noindent\color{red!80!black}$\Rightarrow$\enspace\ignorespaces}{\par}
\newenvironment{alternatesolution}{\par\noindent\color{blue!80!black}$\Rrightarrow$\enspace\ignorespaces}{\par}
\newenvironment{hint}{\par\noindent\color{red!50!black}$\looparrowright$\enspace\ignorespaces}{\par}
\newenvironment{idea}{\par\noindent\color{violet!80!black}$\diamond$\enspace\ignorespaces}{\par}
\newenvironment{remark}{\par\noindent\color{teal!80!black}$\circ$\enspace\ignorespaces}{\par}
\newenvironment{finalanswer}{\par\noindent\textbf{Answer: }\ignorespaces}{\par}
% \excludecomment{solution}
% \excludecomment{alternatesolution}
\excludecomment{hint}
\excludecomment{idea}
\excludecomment{remark}
\excludecomment{finalanswer}

% --- Global TikZ style (design uniformity across all diagrams) ---
\tikzset{
    >=latex,
    thick,
    every node/.append style={font=\small},
}"""
    for environment, visible in (
        ("solution", include_solution),
        ("alternatesolution", include_alternate_solution),
    ):
        if not visible:
            custom_commands = custom_commands.replace(
                rf"% \excludecomment{{{environment}}}",
                rf"\excludecomment{{{environment}}}",
            )
    
    # Combine
    preamble = base_packages
    if include_all:
        preamble += all_packages
    else:
        preamble += subject_packages.get(subject, "")
    preamble += custom_commands
    preamble += "\n" + DISPLAY_FRACTION_PREAMBLE
    preamble += f"\n\\title{{\\textsc{{{title}}}}}"
    
    return preamble


def generate_main_tex(
    scans_dir: str,
    output_file: str,
    title: str,
    subject: str,
    problem_range: Optional[tuple[int, int]] = None,
    problem_list: Optional[List[str]] = None,
    use_foreach: bool = True,
    include_all_packages: bool = False,
    *,
    include_solution: bool = True,
    include_alternate_solution: bool = True,
) -> str:
    """Generate main.tex file.
    
    Args:
        scans_dir: Directory containing scanned problems
        output_file: Output main.tex file path
        title: Document title
        subject: Subject (physics, chemistry, mathematics)
        problem_range: Optional (start, end) range for problems
        problem_list: Optional explicit list of problem numbers/identifiers
        use_foreach: Use \\foreach loop (True) or explicit \\input statements (False)
        include_all_packages: Include packages for every supported subject
        include_solution: Show solution environments (default True)
        include_alternate_solution: Show alternatesolution environments (default True)
        
    Returns:
        Generated LaTeX content
    """
    scans_path = Path(scans_dir)
    output_path = Path(output_file)
    relative_scans = Path(
        os.path.relpath(scans_path.resolve(), output_path.parent.resolve())
    ).as_posix()

    def problem_input(problem: str) -> str:
        filename = f"{problem}.tex"
        return filename if relative_scans == "." else f"{relative_scans}/{filename}"
    
    # Discover problems
    all_problems = discover_problem_files(scans_path)
    all_problems.sort(key=natural_sort_key)
    
    if not all_problems:
        raise ValueError(f"No problem files found in {scans_dir}")
    
    # Filter problems based on range or list
    if problem_list:
        # Use explicit list
        problems = problem_list
    elif problem_range:
        # Filter by range
        start, end = problem_range
        # Extract numeric problems in range
        problems = []
        for p in all_problems:
            match = re.search(r'(\d+)', p)
            if match:
                num = int(match.group(1))
                if start <= num <= end:
                    problems.append(p)
    else:
        # Use all problems
        problems = all_problems
    
    # Generate preamble
    preamble = generate_preamble(
        subject, title, include_all_packages,
        include_solution=include_solution,
        include_alternate_solution=include_alternate_solution,
    )
    
    # Assemble placeholders against sibling tikz/{problem}.tex artifacts.
    # If at least one scan needs assembly, materialize compile-ready copies so
    # main.tex retains per-problem \input statements for extans and other tools.
    assembled_problems: dict[str, str] = {}
    missing_diagrams: list[str] = []
    needs_staging = False
    for problem in problems:
        assembled, missing, had_placeholder = _assemble_problem_for_compile(
            scans_path, problem
        )
        needs_staging = needs_staging or had_placeholder
        assembled_problems[problem] = assembled
        if missing:
            missing_diagrams.append(problem)

    # Generate document body
    body = r"""\begin{document}
\maketitle
\begin{enumerate}"""

    if needs_staging:
        staging_dir = output_path.parent / ".vbagent_compile" / output_path.stem
        staging_dir.mkdir(parents=True, exist_ok=True)
        for p in problems:
            staged_path = staging_dir / f"{p}.tex"
            staged_path.write_text(assembled_problems[p].strip() + "\n")
            relative_path = Path(
                os.path.relpath(staged_path.resolve(), output_path.parent.resolve())
            ).as_posix()
            body += f"\n\\input{{{relative_path}}}"
    elif use_foreach and all(re.fullmatch(r"problem_\d+", p) for p in problems):
        # Use \foreach loop (compact)
        # Extract just the numbers
        numbers = []
        for p in problems:
            match = re.search(r'(\d+)', p)
            if match:
                numbers.append(match.group(1))
        
        if numbers:
            numbers_str = ", ".join(numbers)
            # Determine the pattern (e.g., "problem_\i" or "Problem_\i")
            if problems:
                first = problems[0]
                prefix = re.sub(r'\d+$', '', first)
                relative_pattern = f"{prefix}\\i.tex"
                if relative_scans != ".":
                    relative_pattern = f"{relative_scans}/{relative_pattern}"
                body += f"\n\\foreach \\i in {{{numbers_str}}} {{\n"
                body += f"  \\input{{{relative_pattern}}}\n"
                body += "}\n"
    else:
        # Use explicit \input statements
        for p in problems:
            body += f"\n\\input{{{problem_input(p)}}}"
    
    body += r"""
\end{enumerate}
\end{document}"""
    
    # Combine
    content = preamble + "\n" + body

    if missing_diagrams:
        missing_comments = "\n".join(
            f"% {_MISSING_DIAGRAM_PREFIX}{problem}"
            for problem in missing_diagrams
        )
        content = f"{missing_comments}\n{content}"
    
    return content


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS, name="compile")
@click.option(
    "-d", "--dir",
    "scans_dir",
    type=click.Path(exists=True),
    default="agentic/scans",
    help="Directory containing scanned problems (default: agentic/scans)"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="main.tex",
    help="Output main.tex file path (default: main.tex)"
)
@click.option(
    "-t", "--title",
    default="Problems",
    help="Document title (default: Problems)"
)
@click.option(
    "-s", "--subject",
    type=click.Choice(["physics", "chemistry", "mathematics"]),
    default="physics",
    help="Subject for appropriate packages (default: physics)"
)
@item_selection_options
@click.option(
    "--problems", "problem_list",
    type=str,
    default=None,
    help="Comma-separated list of problem numbers (e.g., '1,3,5,7,9')"
)
@click.option(
    "--all-packages",
    is_flag=True,
    help="Include packages for all subjects (physics, chemistry, mathematics)"
)
@click.option(
    "--solution/--no-solution", "include_solution",
    default=True,
    show_default=True,
    help="Show or hide solution environments in the generated document."
)
@click.option(
    "--alternatesolution/--no-alternatesolution", "include_alternate_solution",
    default=True,
    show_default=True,
    help="Show or hide alternate solutions independently of ordinary solutions."
)
@click.option(
    "--foreach/--explicit",
    default=True,
    help="Use \\\\foreach loop (default) or explicit \\\\input statements"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output"
)
def compile(
    scans_dir: str,
    output: str,
    title: str,
    subject: str,
    from_index: Optional[int],
    to_index: Optional[int],
    item: Optional[int],
    problem_list: Optional[str],
    all_packages: bool,
    include_solution: bool,
    include_alternate_solution: bool,
    foreach: bool,
    verbose: bool,
):
    """Generate main LaTeX file for compiling processed problems.
    
    Creates a main.tex file with proper preamble, packages, and structure
    that compiles all processed problems from the scans directory.
    
    \b
    Features:
        - Subject-specific packages (physics/chemistry/mathematics)
        - Automatic problem discovery
        - Range selection or explicit problem list
        - \\\\foreach loop or explicit \\\\input statements
        - Customizable title and output path
        - Independent solution and alternate-solution visibility (both shown by default)
    
    \b
    Examples:
        # Generate main.tex for all problems
        vbagent compile
        
        # Generate for specific range
        vbagent compile --from 1 --to 13

        # Generate for one item
        vbagent compile --item 5
        
        # Generate for specific problems
        vbagent compile --problems "1,3,5,7,9,11,13,16,19,22,25"
        
        # Chemistry problems with custom title
        vbagent compile -s chemistry -t "Organic Chemistry" -o chemistry_main.tex
        
        # Mathematics problems
        vbagent compile -s mathematics -t "Calculus Problems"
        
        # Use explicit \\\\input statements instead of \\\\foreach
        vbagent compile --explicit
        
        # Include all packages (for mixed physics/chemistry/math problems)
        vbagent compile --all-packages

        # Explicitly show both solution sections
        vbagent compile --solution --alternatesolution

        # Hide both solution sections
        vbagent compile --no-solution --no-alternatesolution
        
        # Custom scans directory
        vbagent compile -d output/scans -o output/main.tex
    
    \b
    Subject-Specific Packages:
        Physics:      tikzphysics, circuitikz, kinematikz, tzplot, pgfplots
        Chemistry:    chemfig, mhchem, pgfplots
        Mathematics:  pgfplots, tkz-euclide, venndiagram
    
    \b
    See Also:
        vbagent run --help        # For processing problems
        vbagent batch --help      # For batch processing
    """
    console = _get_console()
    problem_range = resolve_item_range(from_index, to_index, item)
    if problem_list and problem_range is not None:
        raise click.UsageError(
            "Use --problems or --item/--from/--to, not both"
        )
    
    try:
        # Parse problem list if provided
        problems = None
        if problem_list:
            problems = [f"problem_{n.strip()}" for n in problem_list.split(",")]
            if verbose:
                console.print(f"[dim]Using explicit problem list: {problems}[/dim]")
        
        # Report the normalized range when requested.
        if problem_range is not None:
            start, end = problem_range
            if verbose:
                console.print(f"[dim]Using range: {start} to {end}[/dim]")
        
        # Generate main.tex
        if verbose:
            console.print(f"[cyan]Discovering problems in {scans_dir}...[/cyan]")
        
        content = generate_main_tex(
            scans_dir=scans_dir,
            output_file=output,
            title=title,
            subject=subject,
            problem_range=problem_range,
            problem_list=problems,
            use_foreach=foreach,
            include_all_packages=all_packages,
            include_solution=include_solution,
            include_alternate_solution=include_alternate_solution,
        )

        missing_diagrams = _missing_diagram_names(content)
        if missing_diagrams:
            names = ", ".join(missing_diagrams)
            console.print(
                "[yellow]Warning:[/yellow] No matching TikZ artifact for "
                f"{names}; inserted a compilable placeholder."
            )
        
        # Write to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        
        console.print(f"[green]OK[/green] Generated {output}")
        
        if verbose:
            console.print("\n[dim]Preview:[/dim]")
            # Show first 20 lines
            lines = content.split("\n")
            preview = "\n".join(lines[:20])
            console.print(f"[dim]{preview}[/dim]")
            if len(lines) > 20:
                console.print(f"[dim]... ({len(lines) - 20} more lines)[/dim]")
        
        # Show compilation command
        console.print("\n[cyan]To compile:[/cyan]")
        console.print(f"  pdflatex {output}")
        console.print("  # or")
        console.print(f"  latexmk -pdf {output}")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Failed to generate main.tex:[/red] {e}")
        raise SystemExit(1)
