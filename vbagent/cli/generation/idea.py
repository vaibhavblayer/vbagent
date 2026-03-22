"""CLI command for extracting concepts and ideas from problems.

Analyzes problems and solutions to extract core concepts,
formulas, techniques, and difficulty factors. Subject-aware.
"""

from pathlib import Path

import click

from vbagent.tex import parse_tex_file_with_sections
from vbagent.ui.tables import create_table
from ..common import _get_console


def format_result_table(result) -> "Table":
    """Format idea extraction result as a rich table."""
    table = create_table(title="Extracted Ideas", show_header=True)
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Items", style="green")

    if result.topic:
        table.add_row("Topic", result.topic)
    if result.subtopic:
        table.add_row("Subtopic", result.subtopic)

    for label, items in [
        ("Concepts", result.concepts),
        ("Formulas", result.formulas),
        ("Techniques", result.techniques),
        ("Difficulty Factors", result.difficulty_factors),
    ]:
        if items:
            table.add_row(label, "\n".join(f"• {i}" for i in items))
        else:
            table.add_row(label, "[dim]None extracted[/dim]")

    return table


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-t", "--tex", required=True, type=click.Path(exists=True), help="Path to TeX file")
@click.option("-o", "--output", type=click.Path(), help="Output JSON file path")
@click.option("-s", "--subject", type=click.Choice(["physics", "chemistry", "mathematics"]), default=None, help="Subject (default: from config)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON to stdout")
@click.option("--append", "append_latex", is_flag=True, help="Append idea environment to the TeX file")
def idea(tex: str, output: str | None, subject: str | None, as_json: bool, append_latex: bool):
    r"""Extract concepts and problem-solving ideas.
    
    Analyzes a problem and its solution to identify concepts,
    formulas, techniques, and difficulty factors.
    
    \b
    Examples:
        vbagent idea -t problem.tex
        vbagent idea -t problem.tex --json
        vbagent idea -t problem.tex -o ideas.json
        vbagent idea -t problem.tex --append
        vbagent idea -t problem.tex -s chemistry
    """
    from vbagent.agents.content_generation.idea import (
        extract_ideas,
        generate_idea_latex,
        has_idea_environment,
    )

    console = _get_console()

    try:
        if append_latex:
            # LaTeX mode: generate \begin{idea}...\end{idea} and append
            content = Path(tex).read_text()
            if has_idea_environment(content):
                console.print("[yellow]Warning:[/yellow] File already has an idea environment. Skipping.")
                return
            with console.status("[bold green]Generating idea..."):
                idea_tex = generate_idea_latex(content, subject=subject)
            # Append to file
            with open(tex, "a") as f:
                f.write("\n\n" + idea_tex + "\n")
            console.print(f"[green]✓ Appended idea environment to {tex}[/green]")
        else:
            # JSON mode: extract structured ideas
            problem, solution = parse_tex_file_with_sections(tex)
            if not problem and not solution:
                console.print("[red]Error:[/red] Could not extract problem or solution from TeX file")
                raise SystemExit(1)

            with console.status("[bold green]Extracting ideas..."):
                result = extract_ideas(problem, solution, subject=subject)

            if as_json:
                click.echo(result.model_dump_json(indent=2))
            else:
                console.print(format_result_table(result))

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result.model_dump_json(indent=2))
                console.print(f"\n[green]Results saved to:[/green] {output}")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Idea extraction failed:[/red] {e}")
        raise SystemExit(1)
