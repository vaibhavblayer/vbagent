"""CLI for idea store management.

Commands:
    vbagent ideas collect --from-scans agentic/scans/
    vbagent ideas collect --from-ideas agentic/ideas/
    vbagent ideas add --topic magnetism --text "Biot-Savart law"
    vbagent ideas list [--topic magnetism]
    vbagent ideas stats
    vbagent ideas export --format latex --output revision.tex
"""

import click
from pathlib import Path


def _get_console():
    from rich.console import Console
    return Console()


def _get_store(store_path: str | None = None, subject: str | None = None):
    """Load or create the idea store."""
    from vbagent.ideas.store import IdeaStore
    from vbagent.config import get_config

    if subject is None:
        subject = get_config().subject

    if store_path is None:
        store_path = f"agentic/idea_store/{subject}.json"

    return IdeaStore(Path(store_path), subject=subject)


@click.group()
def ideas():
    """Manage the idea store — the seed database for problem generation."""
    pass


@ideas.command()
@click.option("--from-scans", "scans_dir", type=click.Path(exists=True), help="Scan .tex directory")
@click.option("--from-ideas", "ideas_dir", type=click.Path(exists=True), help="Idea JSON directory")
@click.option("--store", "store_path", default=None, help="Path to store JSON")
@click.option("--subject", default=None, help="Subject override")
def collect(scans_dir, ideas_dir, store_path, subject):
    """Collect ideas from scans or idea JSONs into the store."""
    from vbagent.pipeline.collect import collect_from_scans, collect_from_ideas_dir

    console = _get_console()
    store = _get_store(store_path, subject)

    if not scans_dir and not ideas_dir:
        console.print("[red]Provide --from-scans or --from-ideas[/red]")
        raise SystemExit(1)

    total_new, total_dup = 0, 0

    if scans_dir:
        new, dup = collect_from_scans(store, Path(scans_dir), store.subject)
        total_new += new
        total_dup += dup
        console.print(f"Scans: {new} new, {dup} duplicates")

    if ideas_dir:
        new, dup = collect_from_ideas_dir(store, Path(ideas_dir), store.subject)
        total_new += new
        total_dup += dup
        console.print(f"Ideas: {new} new, {dup} duplicates")

    store.save()
    console.print(f"\n[green]Store updated:[/green] {store.count()} total ideas ({total_new} new)")
    console.print(f"Saved to: {store.path}")


@ideas.command()
@click.option("--topic", required=True, help="Topic for the idea")
@click.option("--text", required=True, help="Idea description")
@click.option("--formula", multiple=True, help="LaTeX formulas (repeatable)")
@click.option("--store", "store_path", default=None)
@click.option("--subject", default=None)
def add(topic, text, formula, store_path, subject):
    """Add a single idea manually."""
    from vbagent.pipeline.collect import collect_manual

    console = _get_console()
    store = _get_store(store_path, subject)

    idea, is_new = collect_manual(store, text, topic, list(formula), store.subject)
    store.save()

    if is_new:
        console.print(f"[green]Added:[/green] {idea.id} — {idea.text}")
    else:
        console.print(f"[yellow]Duplicate:[/yellow] {idea.id} — merged sources")


@ideas.command("list")
@click.option("--topic", default=None, help="Filter by topic")
@click.option("--lens", default=None, help="Filter by lens compatibility")
@click.option("--store", "store_path", default=None)
@click.option("--subject", default=None)
def list_ideas(topic, lens, store_path, subject):
    """List ideas in the store."""
    console = _get_console()
    store = _get_store(store_path, subject)

    if topic and lens:
        pool = store.by_topic_and_lens(topic, lens)
    elif topic:
        pool = store.by_topic(topic)
    elif lens:
        pool = store.by_lens(lens)
    else:
        pool = store.ideas

    if not pool:
        console.print("[yellow]No ideas found[/yellow]")
        return

    for idea in pool:
        lenses_str = ", ".join(idea.natural_lenses[:3])
        console.print(f"  {idea.id:>15}  {idea.text[:60]:<60}  [{lenses_str}]")

    console.print(f"\n{len(pool)} idea(s)")


@ideas.command()
@click.option("--store", "store_path", default=None)
@click.option("--subject", default=None)
def stats(store_path, subject):
    """Show store statistics."""
    console = _get_console()
    store = _get_store(store_path, subject)

    console.print(f"Store: {store.path}")
    console.print(f"Total ideas: {store.count()}")
    console.print(f"Topics: {len(store.topics())}")
    console.print(f"Combinations: {len(store.combinations)}")

    if store.topics():
        console.print("\nIdeas per topic:")
        for t in store.topics():
            n = len(store.by_topic(t))
            console.print(f"  {t}: {n}")


@ideas.command()
@click.option("--format", "fmt", type=click.Choice(["latex", "json"]), default="latex")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--topic", default=None, help="Filter by topic")
@click.option("--store", "store_path", default=None)
@click.option("--subject", default=None)
def export(fmt, output, topic, store_path, subject):
    """Export ideas as a revision sheet."""
    console = _get_console()
    store = _get_store(store_path, subject)

    pool = store.by_topic(topic) if topic else store.ideas
    if not pool:
        console.print("[yellow]No ideas to export[/yellow]")
        return

    if fmt == "json":
        import json
        content = json.dumps(
            [i.model_dump() for i in pool], indent=2, ensure_ascii=False
        )
    else:
        content = _ideas_to_latex(pool, topic or store.subject)

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(content)
        console.print(f"[green]Exported {len(pool)} ideas to {output}[/green]")
    else:
        console.print(content)


def _ideas_to_latex(ideas: list, title: str) -> str:
    """Convert ideas to a LaTeX revision sheet."""
    from collections import defaultdict

    by_topic: dict[str, list] = defaultdict(list)
    for idea in ideas:
        by_topic[idea.topic or "General"].append(idea)

    lines = [f"\\section*{{Revision Sheet — {title.title()}}}"]

    for topic_name, topic_ideas in sorted(by_topic.items()):
        lines.append(f"\n\\subsection*{{{topic_name.replace('-', ' ').title()}}}")
        lines.append("\\begin{itemize}")
        for idea in topic_ideas:
            formulas_str = ""
            if idea.formulas:
                formulas_str = "\n    \\begin{align*}\n"
                formulas_str += " \\\\\n".join(f"    {f}" for f in idea.formulas[:3])
                formulas_str += "\n    \\end{align*}"

            lenses = ", ".join(idea.natural_lenses[:3])
            lines.append(f"    \\item {idea.text} \\hfill [{lenses}]")
            if formulas_str:
                lines.append(formulas_str)
        lines.append("\\end{itemize}")

    return "\n".join(lines)
