"""CLI for canonical syllabus-driven problem authoring."""

from __future__ import annotations

import json
from functools import wraps
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
    needs_review = int(stats.get("needs_review", 0) or 0)
    rejected = int(stats.get("rejected", 0) or 0)
    failed = int(stats.get("failed", 0) or 0)
    if needs_review or rejected or failed:
        raise click.ClickException(
            f"{label} completed without accepting every requested item "
            f"(needs_review={needs_review}, rejected={rejected}, failed={failed}); "
            "inspect the durable run evidence"
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
        click.option("--solution/--no-solution", "include_solution", default=True, show_default=True),
        click.option("--idea-component/--no-idea-component", "include_idea", default=True, show_default=True),
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
    from vbagent.authoring.application import AuthoringApplication

    request = _build_request(kwargs)
    plan = AuthoringApplication().preview(request)
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
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.store import AuthoringStore

    console = _get_console()
    request = _build_request(kwargs)
    output_path = Path(output).expanduser().resolve()
    application = AuthoringApplication(output_path)
    prepared = application.plan(
        request,
        max_attempts=max_attempts,
        concurrency=concurrency,
        include_existing_coverage=existing_coverage,
    )
    with AuthoringStore(output_path) as store:
        plan = store.load_plan(prepared.run_id)
    _show_plan(plan)
    console.print(f"[green]Durable run:[/green] {plan.plan_id}")
    if not start:
        console.print(
            f"Start later with: vbagent author continue --run-id {plan.plan_id} --output {output_path}"
        )
        return
    try:
        result = application.execute_foreground(
            plan.plan_id,
            concurrency=concurrency,
        )
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]Interrupted safely.[/yellow] Resume with: "
            f"vbagent author continue --run-id {plan.plan_id} --output {output_path}"
        )
        raise click.Abort()
    with AuthoringStore(output_path) as store:
        _show_status(store, plan.plan_id, result.stats)
    _raise_if_incomplete(result.stats)


@author.command()
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@_authoring_errors
def status(run_id, output):
    """Show durable status, attempts, failures, usage, and accepted coverage."""
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.store import AuthoringStore

    output_path = Path(output).expanduser().resolve()
    result = AuthoringApplication(output_path).status(run_id)
    with AuthoringStore(output_path) as store:
        _show_status(store, run_id, result.stats)


@author.command(name="continue")
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=None)
@click.option("--rebuild-only", is_flag=True, help="Export and assemble existing items without generation calls")
@click.option(
    "--problem-number", "problem_numbers", multiple=True, type=click.IntRange(min=1),
    help="With --rebuild-only, include only these problem_N.tex files; repeat for each number.",
)
@_authoring_errors
def continue_authoring(run_id, output, concurrency, rebuild_only, problem_numbers):
    """Resume an interrupted or deliberately paused authoring run."""
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.store import AuthoringStore, RunStatus

    output_path = Path(output).expanduser().resolve()
    application = AuthoringApplication(output_path)
    if problem_numbers and not rebuild_only:
        raise click.UsageError("--problem-number requires --rebuild-only")
    if rebuild_only:
        result = application.start(
            run_id, confirmed=True, rebuild_only=True,
            problem_numbers=list(problem_numbers) if problem_numbers else None,
        )
        with AuthoringStore(output_path) as store:
            _show_status(store, run_id, result.status.stats)
        publication = result.status.publication or {}
        if publication.get("status") in {"failed", "compile_failed"}:
            raise click.ClickException(publication.get("error") or "assembly failed")
        return
    with AuthoringStore(output_path) as store:
        run = store.get_run(run_id)
    result = application.execute_foreground(
        run_id,
        concurrency=concurrency,
        resume_cancelled=run["status"] == RunStatus.CANCELLED.value,
    )
    with AuthoringStore(output_path) as store:
        _show_status(store, run_id, result.stats)
    _raise_if_incomplete(result.stats)


@author.command()
@click.option("--run-id", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--reason", default="user requested cancellation", show_default=True)
@_authoring_errors
def cancel(run_id, output, reason):
    """Request cooperative cancellation without losing completed artifacts."""
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.store import AuthoringStore

    output_path = Path(output).expanduser().resolve()
    result = AuthoringApplication(output_path).cancel(run_id, reason)
    with AuthoringStore(output_path) as store:
        _show_status(store, run_id, result.status.stats)


@author.command()
@click.option("--run-id", required=True)
@click.option("--spec-id", required=True)
@click.option("--approve/--reject", default=None)
@click.option("--decision", type=click.Choice(["approve", "reject", "keep", "revise"]))
@click.option("--reason", required=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@_authoring_errors
def review(run_id, spec_id, approve, decision, reason, output):
    """Record the required human decision for one needs-review candidate."""
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.store import AuthoringStore

    output_path = Path(output).expanduser().resolve()
    result = AuthoringApplication(output_path).review(
        run_id,
        spec_id,
        approve=approve,
        reason=reason,
        decision=decision,
    )
    with AuthoringStore(output_path) as store:
        _show_status(store, run_id, result.run_status.stats)


@author.command(name="complete")
@click.option("--run-id", required=True)
@click.option("--spec-id", "spec_ids", multiple=True)
@click.option("-o", "--output", default="agentic/authoring", show_default=True)
@click.option("--solution/--no-solution", "include_solution", default=True)
@click.option("--idea-component/--no-idea-component", "include_idea", default=True)
@click.option("--concurrency", type=click.IntRange(1, 32), default=2)
@_authoring_errors
def complete_components(run_id, spec_ids, output, include_solution, include_idea, concurrency):
    """Add missing parts to existing questions, preserving their numbered files."""
    from vbagent.authoring.application import AuthoringApplication
    from vbagent.authoring.completion import plan_completion
    from vbagent.authoring.store import AuthoringStore

    output_path = Path(output).expanduser().resolve()
    plan = plan_completion(output_path, run_id, spec_ids=list(spec_ids), include_solution=include_solution, include_idea=include_idea)
    with AuthoringStore(output_path) as store:
        store.create_run(plan, output_path, max_attempts=3, concurrency=concurrency)
    _show_plan(plan)
    result = AuthoringApplication(output_path).execute_foreground(plan.plan_id, concurrency=concurrency)
    with AuthoringStore(output_path) as store:
        _show_status(store, plan.plan_id, result.stats)
    _raise_if_incomplete(result.stats)


@author.command()
def catalogs():
    """List built-in exam/subject syllabus catalogs actually available."""
    from vbagent.authoring.application import AuthoringApplication

    console = _get_console()
    result = AuthoringApplication().list_catalogs()
    if not result.catalogs:
        console.print("[yellow]No built-in syllabus catalogs found.[/yellow]")
        return
    table = Table(title="Built-in syllabus catalogs")
    table.add_column("Exam")
    table.add_column("Subject")
    table.add_column("Version")
    table.add_column("Question types")
    for catalog in result.catalogs:
        table.add_row(
            catalog.exam,
            catalog.subject,
            catalog.version,
            ", ".join(catalog.allowed_question_types),
        )
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
        include_solution=values["include_solution"],
        include_idea=values["include_idea"],
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
    from vbagent.authoring.paths import (
        generated_collection_manifest_path,
        generated_output_root,
    )

    console = _get_console()
    stats = stats or store.stats(run_id)
    console.print(f"\n[bold]Authoring run {run_id}[/bold]")
    console.print(
        f"Status: {stats['status']} | total={stats['total']} | accepted={stats['accepted']} | "
        f"unverified_drafts={stats.get('draft', 0)} | "
        f"needs_review={stats['needs_review']} | rejected={stats['rejected']} | "
        f"failed={stats['failed']} | pending={stats['pending']} | attempts={stats['attempts']}"
    )
    progress = store.run_progress(run_id)
    console.print(f"Stage: {progress['current_stage'] or 'idle'}")
    counts = progress["progress_counts"]
    console.print(
        f"Progress: drafted={counts['drafted']}/{counts['total']} | "
        f"checking={counts['checking']} | retrying={counts['retrying']} | "
        f"not_started={counts['not_started']}"
    )
    if progress["latest_failure"]:
        failure = progress["latest_failure"]
        console.print(
            f"Latest failed check: #{failure['ordinal']} attempt {failure['attempt']} "
            f"| {failure['gate']} | {failure['summary']}",
            markup=False,
        )
    for active in progress["active_stages"]:
        console.print(
            f"  #{active['ordinal']} {active['stage']} | {active['topic']} | "
            f"attempt={active['attempt']}"
        )
    usage = store.usage_summary(run_id)
    console.print(
        f"Usage: requests={usage['requests']}, input={usage['input_tokens']}, "
        f"output={usage['output_tokens']}, cached={usage['cached_tokens']}, "
        f"cache_write={usage['cache_write_tokens']}, "
        f"duration={usage['duration_seconds']:.1f}s"
    )
    request_hit = usage.get("cache_request_hit_percent")
    multiplier = usage.get("effective_input_multiplier")
    console.print(
        "Cache: "
        f"token_hit={usage.get('cache_hit_percent', 0.0):.2f}%, "
        f"write={usage.get('cache_write_percent', 0.0):.2f}%, "
        f"request_hit={f'{request_hit:.2f}%' if request_hit is not None else 'n/a'}, "
        f"effective_input={f'{multiplier:.4f}x' if multiplier is not None else 'n/a'}, "
        f"failovers={usage.get('profile_failovers', 0)}"
    )
    profile_usage = usage.get("profile_usage") or {}
    domain_usage = usage.get("cache_domain_usage") or {}
    if profile_usage:
        console.print("Profiles:")
        for name, bucket in sorted(profile_usage.items()):
            console.print(f"  {_format_cache_usage_bucket(name, bucket)}")
    elif usage.get("profiles"):
        console.print(
            "Profiles: "
            + ", ".join(
                f"{name}={count}"
                for name, count in sorted(usage["profiles"].items())
            )
        )
    if domain_usage:
        console.print("Cache domains:")
        for name, bucket in sorted(domain_usage.items()):
            console.print(f"  {_format_cache_usage_bucket(name, bucket)}")
    elif usage.get("cache_domains"):
        console.print(
            "Cache domains: "
            + ", ".join(
                f"{name}={count}"
                for name, count in sorted(usage["cache_domains"].items())
            )
        )
    failures = store.failure_reasons(run_id)
    if failures:
        console.print("Failures: " + ", ".join(f"{name}={count}" for name, count in failures.items()))
    run = store.get_run(run_id)
    generated_dir = generated_output_root(Path(run["output_dir"]))
    manifest = generated_collection_manifest_path(Path(run["output_dir"]))
    console.print(f"Generated output: {generated_dir}")
    if manifest.is_file():
        console.print(f"Generated manifest: {manifest}")
        publication = json.loads(manifest.read_text(encoding="utf-8")).get("publication") or {}
        for label, key in (("Main TeX", "main_tex_path"), ("PDF", "pdf_path"), ("Answer key", "answer_key_path")):
            if publication.get(key):
                console.print(f"{label}: {publication[key]}")
        if publication.get("error"):
            console.print(f"Assembly: {publication['error']}", markup=False)
    if stats.get("needs_review"):
        console.print("Author decision needed: keep, revise, approve when checks pass, or reject. No draft was rejected automatically.")


def _format_cache_usage_bucket(name: str, bucket: dict) -> str:
    request_hit = bucket.get("cache_request_hit_percent")
    request_hit_text = f"{request_hit:.2f}%" if request_hit is not None else "n/a"
    return (
        f"{name}: requests={bucket.get('requests', 0)}, "
        f"token_hit={bucket.get('cache_hit_percent', 0.0):.2f}%, "
        f"write={bucket.get('cache_write_percent', 0.0):.2f}%, "
        f"request_hit={request_hit_text}, failovers={bucket.get('failovers', 0)}"
    )
