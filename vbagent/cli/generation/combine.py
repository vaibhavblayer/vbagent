"""CLI for the combine pipeline.

Commands:
    vbagent combine --count 5 --pick 3 --difficulty 7
    vbagent combine --count 3 --pick 4 --lens calculus --lens probability
    vbagent combine --topic magnetism --count 5 --lens matrix --difficulty hard
    vbagent combine --count 5 --pick 3 --lens all --difficulty 8
    vbagent combine --count 10 --pick 3 --difficulty 4-7
"""

import time

import click
from pathlib import Path


def _get_console():
    from rich.console import Console
    return Console()


@click.command()
@click.option("--count", "-c", default=1, help="Number of combined problems to generate")
@click.option("--pick", "-p", default=5, help="Number of candidate ideas to pick (agent selects best 2-4)")
@click.option("--difficulty", "-d", default="5", help="Difficulty 1-10, or name (easy/medium/hard), or range (4-7)")
@click.option("--lens", multiple=True, help="Math lens(es): algebra, calculus, vectors, matrix, probability, combinatorics, trigonometry, coordinate. Repeatable.")
@click.option("--all-lenses", is_flag=True, help="Generate one problem per compatible lens")
@click.option("--topic", "-t", default=None, help="Filter ideas by topic")
@click.option("--type", "question_type", default="mcq_sc", help="Question type: mcq_sc, mcq_mc, integer, passage, match, assertion_reason")
@click.option("--concepts", default=None, type=click.Path(exists=True), help="Path to concepts.tex for extra context")
@click.option("--no-diagram", is_flag=True, help="Skip TikZ diagram generation")
@click.option("--output", "-o", default="agentic/generated", help="Output base directory")
@click.option("--store", "store_path", default=None, help="Path to idea store JSON")
@click.option("--subject", default=None, help="Subject override")
@click.option("--verbose", "-v", is_flag=True)
def combine(
    count, pick, difficulty, lens, all_lenses,
    topic, question_type, concepts, no_diagram,
    output, store_path, subject, verbose,
):
    """Generate combined problems from the idea store.

    \b
    Picks N ideas from the store, runs the IdeaCombiner agent to select
    the best subset and design a problem framed through math lenses.

    \b
    Examples:
        vbagent combine --count 5 --pick 3 --difficulty 7
        vbagent combine --count 3 --lens calculus --lens probability
        vbagent combine --topic magnetism --difficulty hard --count 5
        vbagent combine --count 10 --difficulty 4-7
        vbagent combine --count 5 --lens all --difficulty 8

    \b
    Output Structure:
        agentic/generated/originals/{subject}/{topic}/{VBP-ID}[-{lens}]/
        ├── problem.tex
        ├── solution.tex
        ├── tikz/diagram.tex
        └── meta.json
    """
    from vbagent.ideas.models import parse_difficulty, MATH_LENSES
    from vbagent.pipeline.combine import generate_batch
    from vbagent.config import get_config

    console = _get_console()

    if subject is None:
        subject = get_config().subject

    # Load store
    if store_path is None:
        store_path = f"agentic/idea_store/{subject}.json"

    from vbagent.ideas.store import IdeaStore
    store = IdeaStore(Path(store_path), subject=subject)

    if store.count() == 0:
        console.print("[red]Idea store is empty.[/red] Run `vbagent ideas collect` first.")
        raise SystemExit(1)

    console.print(f"Store: {store.count()} ideas across {len(store.topics())} topics")

    # Parse difficulty
    diff = parse_difficulty(difficulty)

    # Parse lenses
    lenses_list: list[str] | None = None
    if lens:
        lenses_list = [l for l in lens if l in MATH_LENSES]
        if not lenses_list:
            console.print(f"[red]Invalid lens(es). Valid: {', '.join(MATH_LENSES)}[/red]")
            raise SystemExit(1)

    # Load concepts context
    concepts_context = ""
    if concepts:
        concepts_context = Path(concepts).read_text()

    t0 = time.time()

    try:
        results = generate_batch(
            store=store,
            count=count,
            pick=pick,
            lenses=lenses_list,
            all_lenses=all_lenses,
            difficulty=diff,
            question_type=question_type,
            topic=topic,
            concepts_context=concepts_context,
            with_diagram=not no_diagram,
            output_base=Path(output),
            subject=subject,
            console=console,
        )

        elapsed = time.time() - t0
        console.print(f"\n[bold green]Generated {len(results)} combined problem(s)[/bold green] in {elapsed:.1f}s")
        console.print(f"Output: {output}/originals/")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Combine failed:[/red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise SystemExit(1)
