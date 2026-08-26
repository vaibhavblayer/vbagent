"""Programmatic facade shared by CLI, paper, chat, and MCP callers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vbagent.authoring.models import AcceptancePolicy, AuthoringPlan, AuthoringRequest
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.service import AuthoringRunService
from vbagent.authoring.store import AuthoringStore


@dataclass(frozen=True)
class AuthoringExecution:
    plan: AuthoringPlan
    stats: dict[str, Any]
    items: tuple[dict[str, Any], ...]
    output_dir: Path
    run_dir: Path
    database_path: Path

    @property
    def accepted_candidates(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for item in self.items:
            if item["status"] != "accepted" or not item.get("last_candidate_json"):
                continue
            candidates.append(json.loads(item["last_candidate_json"]))
        return candidates


def execute_authoring(
    request: AuthoringRequest,
    output_dir: str | Path,
    *,
    max_attempts: int = 3,
    concurrency: int = 2,
    start: bool = True,
    include_existing_coverage: bool = True,
) -> AuthoringExecution:
    """Plan and durably execute one canonical authoring request."""
    output = Path(output_dir).expanduser().resolve()
    plan = plan_authoring(
        request,
        output_dir=output,
        include_existing_coverage=include_existing_coverage,
    )
    with AuthoringStore(output) as store:
        store.create_run(
            plan,
            output,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )
        stats = AuthoringRunService(store).execute(plan.plan_id) if start else store.stats(plan.plan_id)
        items = tuple(store.list_item_results(plan.plan_id))
        database_path = store.db_path
    return AuthoringExecution(
        plan=plan,
        stats=stats,
        items=items,
        output_dir=output,
        run_dir=output / "runs" / plan.plan_id,
        database_path=database_path,
    )


def plan_authoring(
    request: AuthoringRequest,
    *,
    output_dir: str | Path | None = None,
    include_existing_coverage: bool = True,
) -> AuthoringPlan:
    """Create a deterministic plan, optionally incorporating durable coverage."""
    planner = AuthoringPlanner()
    catalog = planner.load_catalog(request)
    effective_request = request
    if include_existing_coverage and output_dir is not None:
        output = Path(output_dir).expanduser().resolve()
        with AuthoringStore(output) as store:
            stored = store.accepted_coverage_for_catalog(
                exam=request.exam,
                subject=request.subject,
                catalog_source_sha256=catalog.source_sha256,
            )["topic"]
        if stored:
            combined = dict(request.existing_accepted_counts)
            for topic_id, count in stored.items():
                combined[topic_id] = combined.get(topic_id, 0) + count
            effective_request = request.model_copy(
                update={"existing_accepted_counts": combined},
            )
    return planner.plan(effective_request, catalog=catalog)


def execute_variants(
    parent_spec_id: str,
    output_dir: str | Path,
    *,
    count: int = 1,
    variant_families: dict[str, float] | None = None,
    seed: int = 0,
    acceptance: AcceptancePolicy | dict[str, Any] | None = None,
    max_attempts: int = 3,
    concurrency: int = 2,
    max_lineage_depth: int = 2,
    max_variants_per_parent: int = 12,
    start: bool = True,
) -> AuthoringExecution:
    """Create controlled variants of one accepted canonical parent.

    Parent lookup, artifact binding, depth, and per-parent fan-out are enforced
    again transactionally when the run is created, preventing parallel callers
    from exceeding lineage limits.
    """
    output = Path(output_dir).expanduser().resolve()
    with AuthoringStore(output) as store:
        item = store.get_item(parent_spec_id)
        if item["status"] != "accepted" or not item.get("last_candidate_json"):
            raise ValueError(f"variant parent {parent_spec_id} is not accepted")
        parent_candidate = json.loads(item["last_candidate_json"])
        parent_spec = item["spec_json"]
        from vbagent.authoring.models import GenerationSpec

        spec = GenerationSpec.model_validate_json(parent_spec)
        parent_latex = parent_candidate.get("final_latex", "")
        if not parent_latex:
            raise ValueError(f"accepted variant parent {parent_spec_id} has no final LaTeX")
        parent_plan = store.plan_metadata(item["run_id"])

    has_visual = bool(
        re.search(
            r"\\(?:begin\{(?:tikzpicture|circuitikz|axis)\}|includegraphics)",
            parent_latex,
            flags=re.IGNORECASE,
        )
    )
    policy = acceptance or spec.acceptance
    root_id = spec.lineage_root_spec_id or spec.spec_id
    request = AuthoringRequest(
        exam=spec.exam,
        subject=spec.subject,
        chapter=spec.chapter,
        topics=[spec.topic],
        syllabus_path=parent_plan["catalog_source"],
        expected_syllabus_version=spec.syllabus_version,
        count=count,
        question_types={spec.question_type.value: 1.0},
        difficulties={spec.difficulty: 1.0},
        cognitive_levels={spec.cognitive_level.value: 1.0},
        representations={spec.representation.value: 1.0},
        reasoning_lenses={spec.reasoning_lens: 1.0},
        construction_families={spec.construction_family: 1.0},
        diagram_ratio=1.0 if has_visual else 0.0,
        passage_question_count=spec.passage_question_count,
        required_concepts=list(spec.required_concepts),
        forbidden_concepts=list(spec.forbidden_concepts),
        tone=spec.tone,
        seed=seed,
        acceptance=policy,
        variant_parent_spec_id=spec.spec_id,
        variant_parent_latex=parent_latex,
        variant_parent_artifact_sha256=hashlib.sha256(parent_latex.encode()).hexdigest(),
        variant_lineage_root_spec_id=root_id,
        variant_parent_depth=spec.lineage_depth,
        variant_families=variant_families
        or {"numerical": 1.0, "context": 1.0, "conceptual": 1.0, "calculus": 1.0},
        max_lineage_depth=max_lineage_depth,
        max_variants_per_parent=max_variants_per_parent,
    )
    return execute_authoring(
        request,
        output,
        max_attempts=max_attempts,
        concurrency=concurrency,
        start=start,
        include_existing_coverage=False,
    )
