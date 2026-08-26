"""Durable, accepted-parent problem variants."""

import json
from pathlib import Path
from typing import Optional

import click

from vbagent.tex import extract_items
from ..common import _get_console


def extract_items_from_tex(content: str) -> list[str]:
    """Extract individual items from a TeX file."""
    return extract_items(content)


def filter_items_by_range(
    items: list[str],
    item_range: Optional[tuple[int, int]],
) -> list[str]:
    """Filter items by the specified range."""
    if not item_range:
        return items
    start, end = item_range
    start_idx = max(0, start - 1)
    end_idx = min(len(items), end)
    return items[start_idx:end_idx]


def load_ideas(ideas_path: str, idea_result_cls):
    """Load ideas from a JSON file."""
    try:
        content = Path(ideas_path).read_text()
        data = json.loads(content)
        return idea_result_cls(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--parent-spec-id",
    required=True,
    help="Accepted canonical authoring spec ID to use as the parent",
)
@click.option(
    "--type", "variant_types",
    multiple=True,
    required=True,
    type=click.Choice(["numerical", "context", "conceptual", "calculus"]),
    help="Variant family; repeat to balance a run across families",
)
@click.option(
    "-n", "--count", type=click.IntRange(1, 1000),
    default=1,
    show_default=True,
    help="Number of variant candidates to author",
)
@click.option(
    "-o", "--output", default="agentic/authoring", show_default=True,
    help="Canonical authoring output directory containing the parent ledger",
)
@click.option("--seed", type=int, default=0, show_default=True)
@click.option("--max-attempts", type=click.IntRange(1, 20), default=3, show_default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=2, show_default=True)
@click.option("--max-lineage-depth", type=click.IntRange(1, 5), default=2, show_default=True)
@click.option("--max-per-parent", type=click.IntRange(1, 1000), default=12, show_default=True)
@click.option("--human-review/--automatic-acceptance", default=False, show_default=True)
@click.option("--start/--no-start", default=True, show_default=True)
def variant(
    parent_spec_id: str,
    variant_types: tuple[str, ...],
    count: int,
    output: str,
    seed: int,
    max_attempts: int,
    concurrency: int,
    max_lineage_depth: int,
    max_per_parent: int,
    human_review: bool,
    start: bool,
):
    """Create controlled variants only from an accepted canonical parent.

    \b
    Every variant is independently solved, answer-adjudicated, syllabus checked,
    compiled, reviewed, and novelty checked. Raw TeX/image transformation is no
    longer a creation path; first author or ingest an accepted parent.

    Example:
        vbagent variant --parent-spec-id <id> --type numerical --type context --count 8
    """
    from vbagent.authoring.api import execute_variants
    from vbagent.authoring.models import AcceptancePolicy

    console = _get_console()
    try:
        weights = {family: 1.0 for family in variant_types}
        execution = execute_variants(
            parent_spec_id,
            Path(output),
            count=count,
            variant_families=weights,
            seed=seed,
            acceptance=AcceptancePolicy(human_review_required=human_review),
            max_attempts=max_attempts,
            concurrency=concurrency,
            max_lineage_depth=max_lineage_depth,
            max_variants_per_parent=max_per_parent,
            start=start,
        )
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc

    stats = execution.stats
    console.print(
        f"[bold green]Variant authoring {stats['status']}[/bold green] "
        f"accepted={stats['accepted']}, needs_review={stats['needs_review']}, "
        f"rejected={stats['rejected']}, failed={stats['failed']}"
    )
    console.print(f"Run: {execution.plan.plan_id}\nArtifacts: {execution.run_dir}")
    if stats["rejected"] or stats["failed"]:
        raise click.ClickException(
            "variant authoring completed without accepting every requested item; "
            "inspect the durable run evidence"
        )
