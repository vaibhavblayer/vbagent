"""CLI for canonical syllabus-driven problem authoring."""

from __future__ import annotations

from functools import wraps
import json
from pathlib import Path

import click
from rich.table import Table

from vbagent.cli.common import _get_console


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _authoring_errors(function):
    """Render expected authoring-domain failures as concise CLI errors."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except click.ClickException:
            raise
        except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapped


def _raise_if_incomplete(stats: dict, *, label: str = "authoring run") -> None:
    rejected = int(stats.get("rejected", 0) or 0)
    failed = int(stats.get("failed", 0) or 0)
    if rejected or failed:
        raise click.ClickException(
            f"{label} completed without accepting every requested item "
            f"(rejected={rejected}, failed={failed}); inspect the durable run evidence"
        )


def _request_options(function):
    options = [
        click.option("--exam", required=True, help="Exam catalog ID, e.g. jee_main or neet"),
        click.option(
            "--subject",
            required=True,
            type=click.Choice(["physics", "chemistry", "mathematics", "biology"]),
        ),
        click.option("--chapter", required=True, help="Exact or uniquely resolvable syllabus chapter"),
        click.option("--topic", "topics", multiple=True, help="Exact or uniquely resolvable topic; repeat for several"),
        click.option("--syllabus", "syllabus_path", type=click.Path(exists=True, dir_okay=False)),
        click.option("--syllabus-version", "expected_syllabus_version"),
        click.option("-c", "--count", type=click.IntRange(1, 100_000), default=1, show_default=True),
        click.option(
            "--type",
            "question_types",
            multiple=True,
            default=("mcq_sc:1",),
            help="Question type or type:weight; repeat to define a distribution",
        ),
        click.option(
            "--difficulty",
            "difficulties",
            multiple=True,
            default=("5:1",),
            help="Difficulty 1-10 or level:weight; repeat to define a distribution",
        ),
        click.option(
            "--cognitive",
            "cognitive_levels",
            multiple=True,
            default=("apply:2", "analyze:1"),
            help="Cognitive level or level:weight",
        ),
        click.option(
            "--representation",
            "representations",
            multiple=True,
            default=("symbolic:1", "numerical:1", "contextual:1"),
            help="Representation or representation:weight",
        ),
        click.option("--lens", "reasoning_lenses", multiple=True, help="Reasoning lens or lens:weight"),
        click.option(
            "--construction",
            "construction_families",
            multiple=True,
            help="Construction family or family:weight",
        ),
        click.option("--diagram-ratio", type=click.FloatRange(0.0, 1.0), default=0.0, show_default=True),
        click.option("--passage-questions", type=click.IntRange(2, 10), default=3, show_default=True),
        click.option("--require-concept", "required_concepts", multiple=True),
        click.option("--forbid-concept", "forbidden_concepts", multiple=True),
        click.option("--idea", "seed_ideas", multiple=True, help="Seed idea; repeat for multiple constraints"),
        click.option("--tone", default=""),
        click.option("--seed", type=int, default=0, show_default=True),
        click.option("--human-review/--automatic-acceptance", default=False, show_default=True),
    ]
    for option in reversed(options):
        function = option(function)
    return function


@click.group(context_settings=CONTEXT_SETTINGS)
def author():
    """Plan, run, resume, and audit syllabus-driven problem authoring."""


@author.command()
@_request_options
@click.option("--save", "save_path", type=click.Path(dir_okay=False), help="Save the immutable plan JSON")
@_authoring_errors
def preflight(save_path=None, **kwargs):
    """Resolve syllabus scope and show the full variety plan without API calls."""
    from vbagent.authoring.planner import AuthoringPlanner

    request = _build_request(kwargs)
    plan = AuthoringPlanner().plan(request)
    _show_plan(plan)
    if save_path:
        path = Path(save_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
        _get_console().print(f"[green]Saved immutable plan:[/green] {path}")


@author.command(name="run")
@_request_options
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--max-attempts", type=click.IntRange(1, 20), default=3, show_default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=2, show_default=True)
@click.option("--start/--no-start", default=True, help="Execute immediately or only create the durable run")
@click.option(
    "--existing-coverage/--ignore-existing-coverage",
    default=True,
    show_default=True,
    help="Balance against accepted items already stored for this exact syllabus snapshot",
)
@_authoring_errors
def run_authoring(output, max_attempts, concurrency, start, existing_coverage, **kwargs):
    """Create a durable authoring run and execute its acceptance pipeline."""
    from vbagent.authoring.api import execute_authoring, plan_authoring
    from vbagent.authoring.store import AuthoringStore

    console = _get_console()
    request = _build_request(kwargs)
    output_path = Path(output).expanduser().resolve()
    plan = plan_authoring(
        request,
        output_dir=output_path,
        include_existing_coverage=existing_coverage,
    )
    _show_plan(plan)
    console.print(f"[green]Durable run:[/green] {plan.plan_id}")
    try:
        execution = execute_authoring(
            plan.request,
            output_path,
            max_attempts=max_attempts,
            concurrency=concurrency,
            start=start,
            include_existing_coverage=False,
        )
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]Interrupted safely.[/yellow] Resume with: "
            f"vbagent author continue --run-id {plan.plan_id} --output {output_path}"
        )
        raise click.Abort()
    if not start:
        console.print(
            f"Start later with: vbagent author continue --run-id {plan.plan_id} --output {output_path}"
        )
        return
    with AuthoringStore(execution.database_path) as store:
        _show_status(store, plan.plan_id, execution.stats)
    _raise_if_incomplete(execution.stats)


@author.command()
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@_authoring_errors
def status(run_id, output):
    """Show durable status, attempts, failures, usage, and accepted coverage."""
    from vbagent.authoring.store import AuthoringStore

    with AuthoringStore(Path(output).expanduser().resolve()) as store:
        _show_status(store, run_id, store.stats(run_id))


@author.command(name="continue")
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=None)
@_authoring_errors
def continue_authoring(run_id, output, concurrency):
    """Resume an interrupted or deliberately paused authoring run."""
    from vbagent.authoring.service import AuthoringRunService
    from vbagent.authoring.store import AuthoringStore, RunStatus

    with AuthoringStore(Path(output).expanduser().resolve()) as store:
        run = store.get_run(run_id)
        service = AuthoringRunService(store)
        if run["status"] == RunStatus.CANCELLED.value:
            stats = service.resume(run_id, concurrency=concurrency)
        else:
            stats = service.execute(run_id, concurrency=concurrency)
        _show_status(store, run_id, stats)
    _raise_if_incomplete(stats)


@author.command()
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--reason", default="user requested cancellation", show_default=True)
@_authoring_errors
def cancel(run_id, output, reason):
    """Request cooperative cancellation without losing completed artifacts."""
    from vbagent.authoring.service import AuthoringRunService
    from vbagent.authoring.store import AuthoringStore

    with AuthoringStore(Path(output).expanduser().resolve()) as store:
        AuthoringRunService(store).cancel(run_id, reason)
        _show_status(store, run_id, store.stats(run_id))


@author.command()
@click.option("--run-id", required=True)
@click.option("--spec-id", required=True)
@click.option("--approve/--reject", default=None, required=True)
@click.option("--reason", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@_authoring_errors
def review(run_id, spec_id, approve, reason, output):
    """Record the required human decision for one needs-review candidate."""
    from vbagent.authoring.store import AuthoringStore

    with AuthoringStore(Path(output).expanduser().resolve()) as store:
        store.review_item(run_id, spec_id, approve=approve, reason=reason)
        _show_status(store, run_id, store.stats(run_id))


@author.command()
def catalogs():
    """List built-in exam/subject syllabus catalogs actually available."""
    from vbagent.authoring.catalog import SyllabusCatalogLoader

    console = _get_console()
    pairs = SyllabusCatalogLoader.available()
    if not pairs:
        console.print("[yellow]No built-in syllabus catalogs found.[/yellow]")
        return
    table = Table(title="Built-in syllabus catalogs")
    table.add_column("Exam")
    table.add_column("Subject")
    for exam, subject in pairs:
        table.add_row(exam, subject)
    console.print(table)


def _build_request(values):
    from vbagent.authoring.models import AuthoringRequest

    return AuthoringRequest(
        exam=values["exam"],
        subject=values["subject"],
        chapter=values["chapter"],
        topics=list(values.get("topics") or ()),
        syllabus_path=values.get("syllabus_path"),
        expected_syllabus_version=values.get("expected_syllabus_version"),
        count=values["count"],
        question_types=_parse_weights(values["question_types"]),
        difficulties=_parse_weights(values["difficulties"], difficulty=True),
        cognitive_levels=_parse_weights(values["cognitive_levels"]),
        representations=_parse_weights(values["representations"]),
        reasoning_lenses=_parse_weights(values.get("reasoning_lenses") or ()),
        construction_families=_parse_weights(values.get("construction_families") or ()),
        diagram_ratio=values["diagram_ratio"],
        passage_question_count=values["passage_questions"],
        required_concepts=list(values.get("required_concepts") or ()),
        forbidden_concepts=list(values.get("forbidden_concepts") or ()),
        seed_ideas=list(values.get("seed_ideas") or ()),
        tone=values.get("tone") or "",
        seed=values["seed"],
        acceptance={"human_review_required": values["human_review"]},
    )


def _parse_weights(values, *, difficulty=False):
    if not values:
        return {}
    result = {}
    difficulty_names = {"easy": 3, "medium": 5, "hard": 8, "very-hard": 9, "olympiad": 10}
    for raw in values:
        value, separator, raw_weight = raw.rpartition(":")
        if not separator:
            value, raw_weight = raw, "1"
        try:
            weight = float(raw_weight)
        except ValueError as exc:
            raise click.BadParameter(f"invalid weight in {raw!r}") from exc
        key = value.strip()
        if difficulty:
            key = difficulty_names.get(key.lower(), key)
            try:
                key = int(key)
            except ValueError as exc:
                raise click.BadParameter(f"difficulty must be 1-10 or a named level: {value!r}") from exc
        result[key] = result.get(key, 0.0) + weight
    return result


def _show_plan(plan):
    console = _get_console()
    console.print(f"\n[bold]Authoring plan {plan.plan_id}[/bold]")
    console.print(
        f"Catalog: {plan.request.exam}/{plan.request.subject} {plan.catalog_version} | "
        f"Items: {len(plan.items)} | Estimated agent calls: {plan.estimated_agent_calls}"
    )
    if plan.catalog_source_url:
        console.print(f"Official source: {plan.catalog_source_url} (verified {plan.catalog_verified_at})")
    if plan.exam_pattern_description:
        console.print(f"Exam pattern: {plan.exam_pattern_description}")
    if plan.exam_pattern_source_url:
        console.print(
            f"Exam-pattern source: {plan.exam_pattern_source_url} "
            f"(verified {plan.exam_pattern_verified_at})"
        )
    table = Table(show_header=True)
    table.add_column("Axis")
    table.add_column("Planned distribution")
    for axis, distribution in plan.distributions.items():
        rendered = ", ".join(f"{key}={value}" for key, value in distribution.items())
        table.add_row(axis, rendered)
    console.print(table)
    for warning in plan.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


def _show_status(store, run_id, stats=None):
    console = _get_console()
    stats = stats or store.stats(run_id)
    console.print(f"\n[bold]Authoring run {run_id}[/bold]")
    console.print(
        f"Status: {stats['status']} | total={stats['total']} | accepted={stats['accepted']} | "
        f"needs_review={stats['needs_review']} | rejected={stats['rejected']} | "
        f"failed={stats['failed']} | pending={stats['pending']} | attempts={stats['attempts']}"
    )
    usage = store.usage_summary(run_id)
    console.print(
        f"Usage: requests={usage['requests']}, input={usage['input_tokens']}, "
        f"output={usage['output_tokens']}, cached={usage['cached_tokens']}, "
        f"duration={usage['duration_seconds']:.1f}s"
    )
    failures = store.failure_reasons(run_id)
    if failures:
        console.print("Failures: " + ", ".join(f"{name}={count}" for name, count in failures.items()))
