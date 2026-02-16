"""Extract answers from LaTeX problem files."""

import click
import json
import yaml
from pathlib import Path
from typing import Optional

from ..common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", "main_file", type=click.Path(exists=True), default="main.tex",
              help="Path to main.tex file (default: main.tex)")
@click.option("-o", "--output", type=click.Path(), help="Output file path (optional)")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml", "latex"]),
              default="text", help="Output format (default: text)")
def extans(main_file: str, output: Optional[str], output_format: str):
    """Extract answers from LaTeX problem files.
    
    Parses main.tex to find all problem files (via \\foreach loops or direct \\input),
    then extracts answers from each problem file.
    
    Supports:
    - MCQ with \\ans marker in tasks environment
    - Integer type with \\ansint{value}
    - Multiple correct answers (comma-separated)
    
    \b
    Examples:
        vbagent extans
        vbagent extans -f main.tex --format json
        vbagent extans -o answers.yaml --format yaml
        vbagent extans --format latex -o answers.tex
    """
    from vbagent.parsers import parse_main_tex, extract_answer_from_problem
    
    console = _get_console()
    main_path = Path(main_file)
    
    # Parse main.tex to get problem files
    console.print(f"[cyan]Parsing {main_path}...[/cyan]")
    try:
        problem_files = parse_main_tex(main_path)
    except Exception as e:
        console.print(f"[red]Error parsing {main_path}: {e}[/red]")
        raise click.Abort()
    
    if not problem_files:
        console.print("[yellow]No problem files found in main.tex[/yellow]")
        return
    
    console.print(f"[green]Found {len(problem_files)} problem files[/green]")
    
    # Extract answers
    answers = {}
    missing = []
    
    with console.status("[cyan]Extracting answers...[/cyan]"):
        for i, problem_file in enumerate(problem_files, 1):
            if not problem_file.exists():
                missing.append(str(problem_file))
                answers[i] = None
                continue
            
            answer = extract_answer_from_problem(problem_file)
            answers[i] = answer
    
    # Report missing files
    if missing:
        console.print(f"\n[yellow]Warning: {len(missing)} files not found:[/yellow]")
        for f in missing[:5]:  # Show first 5
            console.print(f"  [dim]{f}[/dim]")
        if len(missing) > 5:
            console.print(f"  [dim]... and {len(missing) - 5} more[/dim]")
    
    # Format output
    if output_format == "json":
        output_content = json.dumps(answers, indent=2)
    elif output_format == "yaml":
        output_content = yaml.dump(answers, default_flow_style=False, sort_keys=False)
    elif output_format == "latex":
        output_content = _format_latex(answers)
    else:  # text
        output_content = _format_text(answers)
    
    # Write or print
    if output:
        output_path = Path(output)
        output_path.write_text(output_content, encoding="utf-8")
        console.print(f"\n[green]✓[/green] Answers written to {output_path}")
    else:
        console.print("\n" + output_content)


def _format_text(answers: dict[int, Optional[str]]) -> str:
    """Format answers as plain text."""
    lines = []
    for i, ans in answers.items():
        if ans is None:
            lines.append(f"Problem {i}: N/A")
        else:
            lines.append(f"Problem {i}: {ans}")
    return "\n".join(lines)


def _format_latex(answers: dict[int, Optional[str]]) -> str:
    """Format answers as LaTeX enumerate environment."""
    lines = [
        "\\begin{enumerate}",
    ]
    for i, ans in answers.items():
        if ans is None:
            lines.append(f"    \\item N/A")
        else:
            lines.append(f"    \\item ({ans})")
    lines.append("\\end{enumerate}")
    return "\n".join(lines)
