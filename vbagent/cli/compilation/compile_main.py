"""CLI command for generating main LaTeX compilation file.

Generates a main.tex file that compiles all processed problems with proper
preamble, packages, and structure.
"""

from pathlib import Path
from typing import Optional, List
import re

import click

from ..common import _get_console


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


def generate_preamble(subject: str = "physics", title: str = "Problems", include_all: bool = False) -> str:
    """Generate LaTeX preamble based on subject.
    
    Args:
        subject: Subject (physics, chemistry, mathematics)
        title: Document title
        include_all: Include packages for all subjects (for mixed content)
        
    Returns:
        LaTeX preamble string
    """
    # Base packages (common to all subjects)
    base_packages = r"""\documentclass{article}
\usepackage{tikz, tasks, geometry, xcolor}
\usetikzlibrary{arrows.meta, patterns, calc, intersections, quotes, angles}
\usepackage{amsmath, amssymb, amsfonts, mathtools}
\setlength{\columnsep}{10pt}
\setlength{\columnseprule}{0.4pt}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\geometry{a4paper, margin=1in}"""
    
    # Subject-specific packages
    subject_packages = {
        "physics": r"""
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}""",
        
        "chemistry": r"""
\usepackage{chemfig, mhchem}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}""",
        
        "mathematics": r"""
\usepackage{pgfplots, tkz-euclide}
\pgfplotsset{compat=1.18}
\usepackage{venndiagram}"""
    }
    
    # All packages (for mixed content)
    all_packages = r"""
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}
\usepackage{chemfig, mhchem}
\usepackage{tkz-euclide}
\usepackage{venndiagram}
\pgfplotsset{compat=1.18}"""
    
    # Custom commands
    custom_commands = r"""
\renewcommand{\frac}{\dfrac}
\newcommand{\ans}{\textcolor{blue!20!red}{\textit{\quad Ans.}}}
% \renewcommand{\ans}{}  % Uncomment to hide answers
\newenvironment{solution}{\par\noindent\color{red!95}\textbf{Solution: }\ignorespaces}{\par}
\newenvironment{alternatesolution}{\par\noindent\color{black!15!red!65!yellow}\textbf{Alternate Solution: }\ignorespaces}{\par}"""
    
    # Combine
    preamble = base_packages
    if include_all:
        preamble += all_packages
    else:
        preamble += subject_packages.get(subject, "")
    preamble += custom_commands
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
        
    Returns:
        Generated LaTeX content
    """
    scans_path = Path(scans_dir)
    
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
    preamble = generate_preamble(subject, title, include_all_packages)
    
    # Generate document body
    body = r"""\begin{document}
\maketitle
\begin{enumerate}"""
    
    if use_foreach and problem_range:
        # Use \foreach loop (compact)
        start, end = problem_range
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
                prefix = re.sub(r'\d+', '', first)
                body += f"\n\\foreach \\i in {{{numbers_str}}} {{\n"
                body += f"  \\input{{{scans_dir}/{prefix}\\i.tex}}\n"
                body += "}\n"
    else:
        # Use explicit \input statements
        for p in problems:
            body += f"\n\\input{{{scans_dir}/{p}.tex}}"
    
    body += r"""
\end{enumerate}
\end{document}"""
    
    # Combine
    content = preamble + "\n" + body
    
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
@click.option(
    "--from", "from_index",
    type=int,
    default=None,
    help="Start index (1-based, inclusive)"
)
@click.option(
    "--to", "to_index",
    type=int,
    default=None,
    help="End index (1-based, inclusive)"
)
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
    problem_list: Optional[str],
    all_packages: bool,
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
    
    \b
    Examples:
        # Generate main.tex for all problems
        vbagent compile
        
        # Generate for specific range
        vbagent compile --from 1 --to 13
        
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
        
        # Custom scans directory
        vbagent compile -d output/scans -o output/main.tex
    
    \b
    Subject-Specific Packages:
        Physics:      circuitikz, kinematikz, tzplot, pgfplots
        Chemistry:    chemfig, mhchem, pgfplots
        Mathematics:  pgfplots, tkz-euclide, venndiagram
    
    \b
    See Also:
        vbagent process --help    # For processing problems
        vbagent batch --help      # For batch processing
    """
    console = _get_console()
    
    try:
        # Parse problem list if provided
        problems = None
        if problem_list:
            problems = [f"problem_{n.strip()}" for n in problem_list.split(",")]
            if verbose:
                console.print(f"[dim]Using explicit problem list: {problems}[/dim]")
        
        # Determine range
        problem_range = None
        if from_index or to_index:
            start = from_index or 1
            end = to_index or 999
            problem_range = (start, end)
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
        )
        
        # Write to file
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        
        console.print(f"[green]✓[/green] Generated {output}")
        
        if verbose:
            console.print(f"\n[dim]Preview:[/dim]")
            # Show first 20 lines
            lines = content.split("\n")
            preview = "\n".join(lines[:20])
            console.print(f"[dim]{preview}[/dim]")
            if len(lines) > 20:
                console.print(f"[dim]... ({len(lines) - 20} more lines)[/dim]")
        
        # Show compilation command
        console.print(f"\n[cyan]To compile:[/cyan]")
        console.print(f"  pdflatex {output}")
        console.print(f"  # or")
        console.print(f"  latexmk -pdf {output}")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Failed to generate main.tex:[/red] {e}")
        raise SystemExit(1)
