"""Extract answers from LaTeX problem files."""

import json
import os
import re
from pathlib import Path
from typing import Optional

import click
import yaml

from ..common import _get_console, natural_sort_key

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "source",
    required=False,
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
@click.option(
    "-f",
    "--file",
    "main_file_option",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to main.tex file (default: main.tex)",
)
@click.option(
    "-d",
    "--dir",
    "problems_dir_option",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Directory containing problem .tex files",
)
@click.option("-o", "--output", type=click.Path(), help="Output file path (optional)")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml", "latex"]),
              default="text", help="Output format (default: text)")
@click.option(
    "--add",
    is_flag=True,
    help="Write a LaTeX answer key and add it to the main TeX file without prompting",
)
def extans(
    source: Optional[str],
    main_file_option: Optional[str],
    problems_dir_option: Optional[str],
    output: Optional[str],
    output_format: str,
    add: bool,
):
    """Extract answers from LaTeX problem files.
    
    SOURCE may be a main TeX file or a directory of problem files. A main file is
    parsed for \\foreach loops and direct \\input commands. A directory is scanned
    for top-level .tex files in natural filename order.
    
    Supports:
    - MCQ with \\ans marker in tasks environment
    - Integer type with \\ansint{value}
    - Multiple correct answers (comma-separated)
    - Subjective answers in a finalanswer environment
    
    \b
    Examples:
        vbagent extans
        vbagent extans path/to/main.tex
        vbagent extans agentic/scans
        vbagent extans -f main.tex --format json
        vbagent extans -d agentic/scans --format json
        vbagent extans -o answers.yaml --format yaml
        vbagent extans --format latex -o answer_key.tex
        vbagent extans main.tex --add
    """
    from vbagent.tex import extract_answer_details_from_problem, parse_main_tex
    
    console = _get_console()
    explicit_sources = [
        source is not None,
        main_file_option is not None,
        problems_dir_option is not None,
    ]
    if sum(explicit_sources) > 1:
        raise click.UsageError(
            "Pass one source: a positional file/directory, --file, or --dir"
        )

    main_path: Optional[Path] = None
    problems_dir: Optional[Path] = None
    if problems_dir_option is not None:
        problems_dir = Path(problems_dir_option)
    elif source is not None and Path(source).is_dir():
        problems_dir = Path(source)
    else:
        main_path = Path(source or main_file_option or "main.tex")
        if not main_path.exists():
            raise click.UsageError(f"Main TeX file does not exist: {main_path}")

    if add and main_path is None:
        raise click.UsageError(
            "--add requires a main TeX file; use --format latex --output PATH "
            "when extracting from a directory"
        )

    if add:
        output_format = "latex"
        if output is None:
            assert main_path is not None
            output = str(main_path.parent / "answer_key.tex")

    if problems_dir is not None:
        console.print(f"[cyan]Scanning {problems_dir}...[/cyan]")
        problem_files = sorted(problems_dir.glob("*.tex"), key=natural_sort_key)
        if output is not None:
            output_path = Path(output).resolve()
            problem_files = [
                problem_file
                for problem_file in problem_files
                if problem_file.resolve() != output_path
            ]
    else:
        assert main_path is not None
        console.print(f"[cyan]Parsing {main_path}...[/cyan]")
        try:
            problem_files = parse_main_tex(main_path)
        except Exception as e:
            console.print(f"[red]Error parsing {main_path}: {e}[/red]")
            raise click.Abort()
    
    if not problem_files:
        source_label = problems_dir if problems_dir is not None else main_path
        console.print(f"[yellow]No problem files found in {source_label}[/yellow]")
        return
    
    console.print(f"[green]Found {len(problem_files)} problem files[/green]")
    
    # Extract answers
    answers = {}
    answer_kinds = {}
    missing = []
    
    with console.status("[cyan]Extracting answers...[/cyan]"):
        for i, problem_file in enumerate(problem_files, 1):
            if not problem_file.exists():
                missing.append(str(problem_file))
                answers[i] = None
                continue
            
            answer = extract_answer_details_from_problem(problem_file)
            answers[i] = answer.value if answer else None
            answer_kinds[i] = answer.kind if answer else None
    
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
        output_content = _format_latex(answers, answer_kinds)
    else:  # text
        output_content = _format_text(answers)
    
    # Write or print
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_content, encoding="utf-8")
        console.print(f"\n[green]OK[/green] Answers written to {output_path}")
    else:
        console.print("\n" + output_content)

    if output_format == "latex" and output and main_path is not None:
        output_path = Path(output)
        should_add = add or click.confirm(
            f"Add the answer key to {main_path}?",
            default=True,
        )
        if should_add:
            status = _add_answer_key_to_main(main_path, output_path)
            if status == "added":
                console.print(f"[green]OK[/green] Added answer key to {main_path}")
            elif status == "already_present":
                console.print(f"[dim]Answer key is already included in {main_path}[/dim]")
            elif status == "missing_enumerate":
                console.print(
                    f"[yellow]Warning:[/yellow] Could not find "
                    f"\\end{{enumerate}} in {main_path}; main file was not changed."
                )


def _add_answer_key_to_main(main_path: Path, answer_key_path: Path) -> str:
    """Insert the answer-key input after the final enumerate, idempotently."""
    content = main_path.read_text(encoding="utf-8")
    relative_answer = Path(
        os.path.relpath(answer_key_path.resolve(), main_path.parent.resolve())
    ).as_posix()
    input_line = rf"\input{{{relative_answer}}}"

    targets = [relative_answer]
    if relative_answer.endswith(".tex"):
        targets.append(relative_answer[:-4])
    target_pattern = "|".join(re.escape(target) for target in targets)
    existing_pattern = rf"\\input\s*\{{(?:{target_pattern})\}}"
    if re.search(existing_pattern, content):
        return "already_present"

    enumerate_end = r"\end{enumerate}"
    insertion_at = content.rfind(enumerate_end)
    if insertion_at < 0:
        return "missing_enumerate"
    insertion_at += len(enumerate_end)

    block = f"\n\n\\vspace*{{\\fill}}\n{input_line}"
    updated = content[:insertion_at] + block + content[insertion_at:]
    main_path.write_text(updated, encoding="utf-8")
    return "added"


def _format_text(answers: dict[int, Optional[str]]) -> str:
    """Format answers as plain text."""
    lines = []
    for i, ans in answers.items():
        if ans is None:
            lines.append(f"Problem {i}: N/A")
        else:
            lines.append(f"Problem {i}: {ans}")
    return "\n".join(lines)


def _infer_answer_kind(answer: str) -> str:
    """Infer legacy untyped answers for direct formatter callers."""
    if re.fullmatch(r"[A-D](?:\s*,\s*[A-D])*", answer, re.IGNORECASE):
        return "mcq"
    if re.fullmatch(r"[+-]?\d+", answer.strip()):
        return "integer"
    return "subjective"


def _format_latex(
    answers: dict[int, Optional[str]],
    answer_kinds: Optional[dict[int, Optional[str]]] = None,
    *,
    max_columns: int | None = None,
) -> str:
    """Format answers as a type-aware LaTeX answer key."""
    kinds = {
        index: (
            (answer_kinds or {}).get(index)
            or (_infer_answer_kind(answer) if answer is not None else None)
        )
        for index, answer in answers.items()
    }
    columns = 2 if "subjective" in kinds.values() else 7
    if max_columns is not None:
        if max_columns < 1:
            raise ValueError("max_columns must be at least 1")
        columns = min(columns, max_columns)
    heading = [
        "\\begin{center}",
        "    \\textsc{Answer Key}",
        "\\end{center}",
    ]
    if columns > 1:
        # The optional heading moves with the first answer row when space is
        # tight; a separate center environment could be orphaned on the prior page.
        lines = [f"\\begin{{multicols}}{{{columns}}}[", *heading, "]"]
    else:
        lines = [*heading, "\\nopagebreak[4]"]
    lines.append("\\begin{enumerate}")
    for i, ans in answers.items():
        if ans is None:
            lines.append("    \\item N/A")
        elif kinds[i] == "mcq":
            lines.append(f"    \\item ({ans.lower()})")
        elif kinds[i] == "integer":
            lines.append(f"    \\item ({ans})")
        else:
            lines.append(f"    \\item {ans}")
    lines.append("\\end{enumerate}")
    if columns > 1:
        lines.append("\\end{multicols}")
    return "\n".join(lines)
