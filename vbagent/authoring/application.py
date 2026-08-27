"""Typed application boundary shared by CLI and MCP authoring clients."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vbagent.authoring.api import plan_authoring, plan_variants
from vbagent.authoring.catalog import SyllabusCatalogLoader
from vbagent.authoring.models import (
    AcceptancePolicy,
    AuthoringPlan,
    AuthoringRequest,
    CatalogTopic,
    CognitiveLevel,
    GenerationSpec,
    QuestionType,
    Representation,
    Subject,
)
from vbagent.authoring.paths import (
    generated_artifact_path,
    generated_build_path,
    generated_collection_manifest_path,
    generated_manifest_path,
    generated_output_root,
)
from vbagent.authoring.service import AuthoringRunService, RunLeaseError
from vbagent.authoring.store import AuthoringStore, ItemStatus, RunStatus


def _catalog_search_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _catalog_match_rank(needle: str, values: tuple[str, ...]) -> int | None:
    candidates = tuple(
        key for value in values if (key := _catalog_search_key(value))
    )
    if needle in candidates:
        return 0
    if any(
        candidate.startswith(needle)
        or (len(candidate) >= 4 and needle.startswith(candidate))
        for candidate in candidates
    ):
        return 1
    if any(needle in candidate for candidate in candidates):
        return 2
    tokens = needle.split()
    haystack_tokens = set(" ".join(candidates).split())
    if tokens and all(token in haystack_tokens for token in tokens):
        return 3
    return None


def _default_question_types() -> dict[str, float]:
    return {QuestionType.MCQ_SINGLE.value: 1.0}


def _default_difficulties() -> dict[int, float]:
    return {5: 1.0}


def _default_cognitive_levels() -> dict[str, float]:
    return {
        CognitiveLevel.APPLY.value: 2.0,
        CognitiveLevel.ANALYZE.value: 1.0,
    }


def _default_representations() -> dict[str, float]:
    return {
        Representation.SYMBOLIC.value: 1.0,
        Representation.NUMERICAL.value: 1.0,
        Representation.CONTEXTUAL.value: 1.0,
    }


class AuthoringIntent(BaseModel):
    """Safe public authoring intent accepted from interactive clients.

    Catalog paths, parent artifacts, coverage counters, and lineage metadata are
    deliberately absent. The application resolves those values from its own
    configured catalog and durable ledger.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exam: str = Field(description="Built-in exam catalog ID, such as jee_main or neet")
    subject: Subject
    chapter: str = Field(description="Exact or uniquely resolvable syllabus chapter")
    topics: list[str] = Field(
        default_factory=list,
        description="Optional exact or uniquely resolvable topics within the chapter",
    )
    count: int = Field(default=1, ge=1, le=100_000)
    question_types: dict[str, float] = Field(
        default_factory=_default_question_types,
        description=(
            "Weighted canonical type IDs only: mcq_sc for single-correct MCQ; "
            "integer for JEE numerical/integer response when the catalog allows it"
        ),
    )
    difficulties: dict[int, float] = Field(default_factory=_default_difficulties)
    cognitive_levels: dict[str, float] = Field(default_factory=_default_cognitive_levels)
    representations: dict[str, float] = Field(default_factory=_default_representations)
    reasoning_lenses: dict[str, float] = Field(default_factory=dict)
    construction_families: dict[str, float] = Field(default_factory=dict)
    diagram_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    passage_question_count: int = Field(default=3, ge=2, le=10)
    required_concepts: list[str] = Field(default_factory=list)
    forbidden_concepts: list[str] = Field(default_factory=list)
    seed_ideas: list[str] = Field(default_factory=list)
    tone: str = ""
    seed: int = 0
    human_review_required: bool = False
    include_solution: bool = True
    include_idea: bool = True

    def to_request(self) -> AuthoringRequest:
        return AuthoringRequest(
            exam=self.exam,
            subject=self.subject,
            chapter=self.chapter,
            topics=self.topics,
            count=self.count,
            question_types=self.question_types,
            difficulties=self.difficulties,
            cognitive_levels=self.cognitive_levels,
            representations=self.representations,
            reasoning_lenses=self.reasoning_lenses,
            construction_families=self.construction_families,
            diagram_ratio=self.diagram_ratio,
            passage_question_count=self.passage_question_count,
            required_concepts=self.required_concepts,
            forbidden_concepts=self.forbidden_concepts,
            seed_ideas=self.seed_ideas,
            tone=self.tone,
            seed=self.seed,
            include_solution=self.include_solution,
            include_idea=self.include_idea,
            acceptance=AcceptancePolicy(
                human_review_required=self.human_review_required,
            ),
        )


class CatalogReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam: str
    subject: str
    version: str
    chapters: int
    topics: int
    allowed_question_types: list[str]
    source_url: str
    official_source_sha256: str
    verified_at: str


class CatalogListResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalogs: list[CatalogReference]
    total: int


class CatalogSearchMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["chapter", "topic"]
    chapter_id: str
    chapter: str
    topic_id: str | None = None
    topic: str | None = None
    aliases: list[str] = Field(default_factory=list)
    description: str = ""


class CatalogSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam: str
    subject: str
    version: str
    allowed_question_types: list[str]
    query: str
    matches: list[CatalogSearchMatch]
    total: int
    truncated: bool


class CatalogChapterSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str = ""
    topic_count: int


class CatalogInspectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam: str
    subject: str
    version: str
    source_url: str
    verified_at: str
    source_sha256: str
    official_source_sha256: str
    allowed_question_types: list[str]
    exam_pattern_description: str
    exam_pattern_source_url: str
    exam_pattern_source_sha256: str
    exam_pattern_verified_at: str
    chapters: list[CatalogChapterSummary]


class CatalogTopicPageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exam: str
    subject: str
    version: str
    chapter_id: str
    chapter: str
    chapter_description: str
    topics: list[CatalogTopic]
    total: int
    offset: int
    limit: int
    next_offset: int | None


class PlanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    created: bool
    status: str
    exam: str
    subject: str
    chapter_ids: list[str]
    chapters: list[str]
    topic_ids: list[str]
    topics: list[str]
    catalog_version: str
    catalog_source_sha256: str
    catalog_official_source_sha256: str
    total_items: int
    distributions: dict[str, dict[str, int]]
    estimated_agent_calls: int
    warnings: list[str]
    max_attempts: int
    concurrency: int
    current_stage: str
    stage_updated_at: str | None
    generated_output_dir: str
    requires_confirmation: bool = True
    next_action: str


class WorkerLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pid: int
    log_path: str


class WorkerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    pid: int | None
    resume: bool
    log_path: str | None
    error_message: str | None
    created_at: str
    updated_at: str
    finished_at: str | None


class ActiveAuthoringStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: str
    ordinal: int
    attempt: int
    stage: str
    stage_updated_at: str | None
    worker_id: str | None
    chapter: str
    topic: str


class RunStatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    exam: str
    subject: str
    chapter_ids: list[str]
    chapters: list[str]
    topic_ids: list[str]
    topics: list[str]
    stats: dict[str, Any]
    usage: dict[str, Any]
    failure_reasons: dict[str, int]
    accepted_coverage: dict[str, dict[str, int]]
    all_items_accepted: bool
    all_requested_components_ready: bool = False
    needs_human_review: bool
    active_lease: bool
    current_stage: str | None
    stage_updated_at: str | None
    active_stages: list[ActiveAuthoringStage]
    stage_counts: dict[str, int]
    progress_counts: dict[str, int] = Field(default_factory=dict)
    latest_failure: dict[str, Any] | None = None
    worker: WorkerState | None
    artifact_resource_template: str
    evidence_resource_template: str
    worker_log_path: str
    generated_output_dir: str
    generated_manifest_path: str | None
    publication: dict[str, Any] | None


class RunCommandResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    action: Literal["start", "resume", "cancel", "rebuild"]
    dispatched: bool
    status: RunStatusResult
    worker: WorkerLaunch | None = None
    message: str


class ItemSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: str
    run_id: str
    ordinal: int
    status: str
    attempts: int
    max_attempts: int
    exam: str
    subject: str
    chapter_id: str
    chapter: str
    topic_id: str
    topic: str
    question_type: str
    difficulty: int
    cognitive_level: str
    representation: str
    diagram_policy: str
    source_kind: str
    parent_spec_id: str | None = None
    error_stage: str | None = None
    error_message: str | None = None
    artifact_sha256: str | None = None
    saved_path: str | None = None
    saved_number: int | None = None
    human_review_reason: str | None = None
    completed_at: str | None = None
    candidate: dict[str, Any] | None = None


class ItemPageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    items: list[ItemSummary]
    offset: int
    limit: int
    total: int
    next_offset: int | None


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    spec_id: str
    decision: Literal["approved", "rejected", "kept", "revision_requested"]
    item_status: str
    run_status: RunStatusResult


class ArtifactResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    spec_id: str
    path: str
    mime_type: str = "text/x-tex"
    content: str
    status: str = "accepted"
    validated: bool = True
    number: int | None = None


class EvidenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    spec_id: str
    evidence: dict[str, Any]


class WorkerLogPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_status: str
    offset: int
    next_offset: int
    eof: bool
    content: str


Launcher = Callable[[Path, str, int | None, bool, str], WorkerLaunch]


class SubprocessWorkerLauncher:
    """Launch a detached authoring worker whose output never touches MCP stdout."""

    def __call__(
        self,
        output_root: Path,
        run_id: str,
        concurrency: int | None,
        resume: bool,
        dispatch_token: str,
    ) -> WorkerLaunch:
        run_dir = output_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / "worker.log"
        command = [
            sys.executable,
            "-m",
            "vbagent.authoring.worker",
            "--output",
            str(output_root),
            "--run-id",
            run_id,
            "--dispatch-token",
            dispatch_token,
        ]
        if concurrency is not None:
            command.extend(["--concurrency", str(concurrency)])
        if resume:
            command.append("--resume")

        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONUNBUFFERED": "1",
                "NO_COLOR": "1",
                "VBAGENT_AUTHORING_WORKER": "1",
                "VBAGENT_FULL_AGENT_IO": "1",
                "VBAGENT_AGENT_IO_FORMAT": "jsonl",
            }
        )
        detach_options: dict[str, Any]
        if os.name == "nt":
            detach_options = {
                "creationflags": (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            }
        else:
            detach_options = {"start_new_session": True}
        with log_path.open("ab", buffering=0) as log_handle:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=environment,
                close_fds=True,
                **detach_options,
            )
        return WorkerLaunch(
            pid=process.pid,
            log_path=str(log_path),
        )


class AuthoringApplication:
    """Coherent authoring use cases with a server-controlled output boundary."""

    def __init__(
        self,
        output_root: str | Path = "agentic/authoring",
        *,
        launcher: Launcher | None = None,
    ) -> None:
        self.output_root = Path(output_root).expanduser().resolve()
        self.launcher = launcher or SubprocessWorkerLauncher()

    def list_catalogs(self) -> CatalogListResult:
        catalogs: list[CatalogReference] = []
        for exam, subject in SyllabusCatalogLoader.available():
            catalog = SyllabusCatalogLoader.load_builtin(exam, subject)
            catalogs.append(
                CatalogReference(
                    exam=catalog.exam,
                    subject=catalog.subject,
                    version=catalog.version,
                    chapters=len(catalog.chapters),
                    topics=sum(len(chapter.topics) for chapter in catalog.chapters),
                    allowed_question_types=[item.value for item in catalog.allowed_question_types],
                    source_url=catalog.source_url,
                    official_source_sha256=catalog.official_source_sha256,
                    verified_at=catalog.verified_at,
                )
            )
        return CatalogListResult(catalogs=catalogs, total=len(catalogs))

    def search_catalog(
        self,
        exam: str,
        subject: Subject,
        query: str,
        *,
        limit: int = 20,
    ) -> CatalogSearchResult:
        """Search one catalog without returning its complete topic tree."""
        clean_query = query.strip()
        needle = _catalog_search_key(clean_query)
        if not needle:
            raise ValueError("catalog search query cannot be empty")
        if limit < 1 or limit > 50:
            raise ValueError("catalog search limit must be between 1 and 50")

        catalog = SyllabusCatalogLoader.load_builtin(exam, subject)
        ranked: list[tuple[int, int, int, CatalogSearchMatch]] = []
        for chapter_index, chapter in enumerate(catalog.chapters):
            chapter_rank = _catalog_match_rank(
                needle,
                (chapter.id, chapter.title),
            )
            if chapter_rank is not None:
                ranked.append(
                    (
                        chapter_rank,
                        chapter_index,
                        -1,
                        CatalogSearchMatch(
                            kind="chapter",
                            chapter_id=chapter.id,
                            chapter=chapter.title,
                            description=chapter.description,
                        ),
                    )
                )
            for topic_index, topic in enumerate(chapter.topics):
                topic_rank = _catalog_match_rank(
                    needle,
                    (topic.id, topic.title, *topic.aliases),
                )
                if topic_rank is None:
                    continue
                ranked.append(
                    (
                        topic_rank,
                        chapter_index,
                        topic_index,
                        CatalogSearchMatch(
                            kind="topic",
                            chapter_id=chapter.id,
                            chapter=chapter.title,
                            topic_id=topic.id,
                            topic=topic.title,
                            aliases=list(topic.aliases),
                            description=topic.description,
                        ),
                    )
                )
        ranked.sort(key=lambda item: item[:3])
        matches = [item[3] for item in ranked]
        return CatalogSearchResult(
            exam=catalog.exam,
            subject=catalog.subject,
            version=catalog.version,
            allowed_question_types=[
                item.value for item in catalog.allowed_question_types
            ],
            query=clean_query,
            matches=matches[:limit],
            total=len(matches),
            truncated=len(matches) > limit,
        )

    def inspect_catalog(self, exam: str, subject: Subject) -> CatalogInspectionResult:
        catalog = SyllabusCatalogLoader.load_builtin(exam, subject)
        return CatalogInspectionResult(
            exam=catalog.exam,
            subject=catalog.subject,
            version=catalog.version,
            source_url=catalog.source_url,
            verified_at=catalog.verified_at,
            source_sha256=catalog.source_sha256,
            official_source_sha256=catalog.official_source_sha256,
            allowed_question_types=[item.value for item in catalog.allowed_question_types],
            exam_pattern_description=catalog.exam_pattern_description,
            exam_pattern_source_url=catalog.exam_pattern_source_url,
            exam_pattern_source_sha256=catalog.exam_pattern_source_sha256,
            exam_pattern_verified_at=catalog.exam_pattern_verified_at,
            chapters=[
                CatalogChapterSummary(
                    id=chapter.id,
                    title=chapter.title,
                    description=chapter.description,
                    topic_count=len(chapter.topics),
                )
                for chapter in catalog.chapters
            ],
        )

    def list_catalog_topics(
        self,
        exam: str,
        subject: Subject,
        chapter: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> CatalogTopicPageResult:
        """Return one selected chapter's bounded topic tree."""
        if offset < 0:
            raise ValueError("catalog topic offset cannot be negative")
        if limit < 1 or limit > 100:
            raise ValueError("catalog topic limit must be between 1 and 100")
        catalog = SyllabusCatalogLoader.load_builtin(exam, subject)
        resolved = SyllabusCatalogLoader.resolve_chapter(catalog, chapter)
        topics = list(resolved.topics)
        page = topics[offset : offset + limit]
        next_offset = offset + len(page)
        return CatalogTopicPageResult(
            exam=catalog.exam,
            subject=catalog.subject,
            version=catalog.version,
            chapter_id=resolved.id,
            chapter=resolved.title,
            chapter_description=resolved.description,
            topics=page,
            total=len(topics),
            offset=offset,
            limit=limit,
            next_offset=next_offset if next_offset < len(topics) else None,
        )

    def plan(
        self,
        intent: AuthoringIntent | AuthoringRequest,
        *,
        max_attempts: int = 3,
        concurrency: int = 2,
        include_existing_coverage: bool = True,
        complete_run_id: str | None = None,
        complete_spec_ids: list[str] | None = None,
    ) -> PlanResult:
        if complete_run_id:
            from vbagent.authoring.completion import plan_completion

            plan = plan_completion(self.output_root, complete_run_id, spec_ids=complete_spec_ids, include_solution=intent.include_solution, include_idea=intent.include_idea)
        else:
            if complete_spec_ids:
                raise ValueError("complete_spec_ids requires complete_run_id")
            plan = self.preview(intent, include_existing_coverage=include_existing_coverage)
        return self._persist_plan(
            plan,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )

    def preview(
        self,
        intent: AuthoringIntent | AuthoringRequest,
        *,
        include_existing_coverage: bool = False,
    ) -> AuthoringPlan:
        """Resolve a deterministic plan without persisting it or calling models."""
        request = intent.to_request() if isinstance(intent, AuthoringIntent) else intent
        return plan_authoring(
            request,
            output_dir=self.output_root if include_existing_coverage else None,
            include_existing_coverage=include_existing_coverage,
        )

    def plan_controlled_variants(
        self,
        parent_spec_id: str,
        *,
        count: int = 1,
        variant_families: dict[str, float] | None = None,
        seed: int = 0,
        human_review_required: bool | None = None,
        max_attempts: int = 3,
        concurrency: int = 2,
        max_lineage_depth: int = 2,
        max_variants_per_parent: int = 12,
    ) -> PlanResult:
        acceptance: AcceptancePolicy | None = None
        if human_review_required is not None:
            acceptance = AcceptancePolicy(
                human_review_required=human_review_required,
            )
        plan = plan_variants(
            parent_spec_id,
            self.output_root,
            count=count,
            variant_families=variant_families,
            seed=seed,
            acceptance=acceptance,
            max_lineage_depth=max_lineage_depth,
            max_variants_per_parent=max_variants_per_parent,
        )
        return self._persist_plan(
            plan,
            max_attempts=max_attempts,
            concurrency=concurrency,
        )

    def _persist_plan(
        self,
        plan: AuthoringPlan,
        *,
        max_attempts: int,
        concurrency: int,
    ) -> PlanResult:
        with AuthoringStore(self.output_root) as store:
            try:
                store.get_run(plan.plan_id)
                created = False
            except KeyError:
                created = True
            store.create_run(
                plan,
                self.output_root,
                max_attempts=max_attempts,
                concurrency=concurrency,
            )
            run = store.get_run(plan.plan_id)
        return PlanResult(
            run_id=plan.plan_id,
            created=created,
            status=run["status"],
            exam=plan.request.exam,
            subject=plan.request.subject,
            chapter_ids=list(
                dict.fromkeys(spec.chapter_id for spec in plan.items)
            ),
            chapters=list(dict.fromkeys(spec.chapter for spec in plan.items)),
            topic_ids=list(dict.fromkeys(spec.topic_id for spec in plan.items)),
            topics=list(dict.fromkeys(spec.topic for spec in plan.items)),
            catalog_version=plan.catalog_version,
            catalog_source_sha256=plan.catalog_source_sha256,
            catalog_official_source_sha256=plan.catalog_official_source_sha256,
            total_items=len(plan.items),
            distributions=plan.distributions,
            estimated_agent_calls=plan.estimated_agent_calls,
            warnings=list(plan.warnings),
            max_attempts=int(run["max_attempts"]),
            concurrency=int(run["concurrency"]),
            current_stage=str(run["current_stage"] or "awaiting_start"),
            stage_updated_at=run["stage_updated_at"],
            generated_output_dir=str(generated_output_root(self.output_root)),
            next_action=(
                "Present the resolved plan and estimated calls, then stop this "
                "controller turn. The terminal will start it when the original "
                "message explicitly requested creation; plan-only or ambiguous "
                "intent remains pending for confirmation."
            ),
        )

    def start(
        self,
        run_id: str,
        *,
        confirmed: bool,
        concurrency: int | None = None,
        rebuild_only: bool = False,
        problem_numbers: list[int] | None = None,
    ) -> RunCommandResult:
        if not confirmed:
            raise ValueError(
                "explicit user authorization is required before generation or rebuilding"
            )
        if problem_numbers is not None and not rebuild_only:
            raise ValueError("problem_numbers is only valid with rebuild_only=true")
        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)
            if rebuild_only:
                from vbagent.authoring.publication import (
                    assemble_generated_run,
                    publication_stage,
                    validate_problem_numbers,
                )

                selection = validate_problem_numbers(problem_numbers)
                if self._has_active_lease(run):
                    raise ValueError("wait for the active worker before rebuilding")
                store.restore_unreviewed_rejections(run_id)
                publication = assemble_generated_run(
                    store, run_id,
                    progress_callback=lambda stage: store.set_run_stage(run_id, None, stage),
                    problem_numbers=selection,
                )
                stage = (
                    publication_stage(store.stats(run_id), publication)
                    if run["status"] == RunStatus.COMPLETED.value
                    else "cancelled" if run["status"] == RunStatus.CANCELLED.value
                    else "awaiting_start"
                )
                store.set_run_stage(run_id, None, stage)
                store.write_run_manifest(run_id)
                return RunCommandResult(
                    run_id=run_id, action="rebuild", dispatched=False,
                    status=self._status_from_store(store, run_id),
                    message="Existing files exported and assembly attempted; no problem-generation calls were made.",
                )
            if run["status"] == RunStatus.COMPLETED.value:
                raise ValueError(f"authoring run {run_id} is already completed")
            if run["status"] == RunStatus.CANCELLED.value:
                raise ValueError(
                    f"authoring run {run_id} is cancelled; use authoring_resume"
                )
            if run["status"] == RunStatus.CANCEL_REQUESTED.value:
                raise ValueError(
                    f"authoring run {run_id} is cancelling; wait for cancelled status"
                )
            if self._has_active_lease(run):
                status = self._status_from_store(store, run_id)
                return RunCommandResult(
                    run_id=run_id,
                    action="start",
                    dispatched=False,
                    status=status,
                    worker=self._worker_from_dispatch(store.get_dispatch(run_id)),
                    message="The durable run is already active.",
                )
            dispatch_token = uuid.uuid4().hex
            reserved = store.reserve_dispatch(
                run_id,
                dispatch_token,
                resume=False,
            )
            if not reserved:
                status = self._status_from_store(store, run_id)
                return RunCommandResult(
                    run_id=run_id,
                    action="start",
                    dispatched=False,
                    status=status,
                    worker=self._worker_from_dispatch(store.get_dispatch(run_id)),
                    message="A worker launch is already reserved or active.",
                )
        try:
            worker = self.launcher(
                self.output_root,
                run_id,
                concurrency,
                False,
                dispatch_token,
            )
        except Exception as exc:
            with AuthoringStore(self.output_root) as store:
                store.finish_dispatch(
                    run_id,
                    dispatch_token,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
            raise
        with AuthoringStore(self.output_root) as store:
            store.mark_dispatch_started(
                run_id,
                dispatch_token,
                pid=worker.pid,
                log_path=worker.log_path,
            )
        return RunCommandResult(
            run_id=run_id,
            action="start",
            dispatched=True,
            status=self.status(run_id),
            worker=worker,
            message="Worker dispatched; poll authoring_status for durable progress.",
        )

    def resume(
        self,
        run_id: str,
        *,
        confirmed: bool,
        concurrency: int | None = None,
    ) -> RunCommandResult:
        if not confirmed:
            raise ValueError(
                "explicit user authorization is required before model calls resume"
            )
        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)
            if run["status"] != RunStatus.CANCELLED.value:
                raise ValueError(
                    f"authoring run {run_id} is {run['status']}; only cancelled runs can resume"
                )
            dispatch_token = uuid.uuid4().hex
            reserved = store.reserve_dispatch(
                run_id,
                dispatch_token,
                resume=True,
            )
            if not reserved:
                status = self._status_from_store(store, run_id)
                return RunCommandResult(
                    run_id=run_id,
                    action="resume",
                    dispatched=False,
                    status=status,
                    worker=self._worker_from_dispatch(store.get_dispatch(run_id)),
                    message="A resume worker launch is already reserved or active.",
                )
        try:
            worker = self.launcher(
                self.output_root,
                run_id,
                concurrency,
                True,
                dispatch_token,
            )
        except Exception as exc:
            with AuthoringStore(self.output_root) as store:
                store.finish_dispatch(
                    run_id,
                    dispatch_token,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
            raise
        with AuthoringStore(self.output_root) as store:
            store.mark_dispatch_started(
                run_id,
                dispatch_token,
                pid=worker.pid,
                log_path=worker.log_path,
            )
        return RunCommandResult(
            run_id=run_id,
            action="resume",
            dispatched=True,
            status=self.status(run_id),
            worker=worker,
            message="Resume worker dispatched; poll authoring_status for durable progress.",
        )

    def execute_foreground(
        self,
        run_id: str,
        *,
        concurrency: int | None = None,
        resume_cancelled: bool = False,
    ) -> RunStatusResult:
        """Run synchronously for the manual CLI while sharing all contracts."""
        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)
            if store.has_active_dispatch(run_id):
                raise RunLeaseError(
                    f"authoring run {run_id} already has an active detached worker"
                )
            service = AuthoringRunService(store)
            if run["status"] == RunStatus.CANCELLED.value:
                if not resume_cancelled:
                    raise ValueError(f"authoring run {run_id} is cancelled")
                service.resume(run_id, concurrency=concurrency)
            else:
                service.execute(run_id, concurrency=concurrency)
            return self._status_from_store(store, run_id)

    def cancel(
        self,
        run_id: str,
        reason: str = "user requested cancellation",
    ) -> RunCommandResult:
        if not reason.strip():
            raise ValueError("a cancellation reason is required")
        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)
            terminal = run["status"] in {
                RunStatus.COMPLETED.value,
                RunStatus.CANCELLED.value,
            }
            if not terminal:
                AuthoringRunService(store).cancel(run_id, reason.strip())
            status = self._status_from_store(store, run_id)
        return RunCommandResult(
            run_id=run_id,
            action="cancel",
            dispatched=False,
            status=status,
            message=(
                f"Run is already {status.status}; no cancellation change was needed."
                if terminal
                else "Cancellation recorded; an in-flight item may finish cooperatively."
            ),
        )

    def status(self, run_id: str) -> RunStatusResult:
        with AuthoringStore(self.output_root) as store:
            return self._status_from_store(store, run_id)

    def _status_from_store(
        self,
        store: AuthoringStore,
        run_id: str,
    ) -> RunStatusResult:
        run = store.get_run(run_id)
        dispatch = store.get_dispatch(run_id)
        stats = store.stats(run_id)
        scope = store.run_scope(run_id)
        progress = store.run_progress(run_id)
        total = int(stats["total"])
        accepted = int(stats[ItemStatus.ACCEPTED.value])
        manifest_path = generated_collection_manifest_path(self.output_root)
        if not manifest_path.is_file():
            manifest_path = generated_manifest_path(self.output_root, run_id)
        build_path = generated_build_path(self.output_root, run_id)
        publication = (
            json.loads(build_path.read_text(encoding="utf-8"))
            if build_path.is_file()
            else None
        )
        return RunStatusResult(
            run_id=run_id,
            status=run["status"],
            **scope,
            stats=stats,
            usage=store.usage_summary(run_id),
            failure_reasons=store.failure_reasons(run_id),
            accepted_coverage=store.accepted_coverage(run_id),
            all_items_accepted=total > 0 and accepted == total,
            all_requested_components_ready=total > 0 and accepted + int(stats.get("draft", 0)) == total,
            needs_human_review=bool(stats[ItemStatus.NEEDS_REVIEW.value]),
            active_lease=self._has_active_lease(run),
            **progress,
            worker=self._worker_state(dispatch),
            artifact_resource_template=(
                f"vbagent://authoring/runs/{run_id}/items/{{spec_id}}/final"
            ),
            evidence_resource_template=(
                f"vbagent://authoring/runs/{run_id}/items/{{spec_id}}/evidence"
            ),
            worker_log_path=str(self.output_root / "runs" / run_id / "worker.log"),
            generated_output_dir=str(generated_output_root(self.output_root)),
            generated_manifest_path=(
                str(manifest_path) if manifest_path.is_file() else None
            ),
            publication=publication,
        )

    def list_items(
        self,
        run_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        include_candidate: bool = False,
    ) -> ItemPageResult:
        from vbagent.authoring.exports import get_export

        with AuthoringStore(self.output_root) as store:
            records, total = store.list_item_results_page(
                run_id,
                offset=offset,
                limit=limit,
                status=status,
                include_candidate=include_candidate,
            )
            exports = {str(record["spec_id"]): get_export(store, str(record["spec_id"])) for record in records}
        for record in records:
            if record["status"] in {ItemStatus.ACCEPTED.value, ItemStatus.DRAFT.value, ItemStatus.NEEDS_REVIEW.value}:
                exported = exports[str(record["spec_id"])]
                if exported:
                    record["saved_number"] = int(exported["number"])
                    record["saved_path"] = str(
                        generated_output_root(self.output_root)
                        / f"problem_{exported['number']}.tex"
                    )
        next_offset = offset + len(records)
        if next_offset >= total:
            next_offset = None
        return ItemPageResult(
            run_id=run_id,
            items=[ItemSummary.model_validate(record) for record in records],
            offset=offset,
            limit=limit,
            total=total,
            next_offset=next_offset,
        )

    def review(
        self,
        run_id: str,
        spec_id: str,
        *,
        approve: bool | None = None,
        reason: str,
        decision: Literal["approve", "reject", "keep", "revise"] | None = None,
    ) -> ReviewResult:
        if decision is None and approve is None:
            raise ValueError("choose approve, reject, keep, or revise")
        if decision is not None and approve is not None:
            raise ValueError("provide decision or approve, not both")
        action = decision or ("approve" if approve else "reject")
        with AuthoringStore(self.output_root) as store:
            if action in {"keep", "revise"}:
                store.defer_or_revise_item(run_id, spec_id, reason=reason, revise=action == "revise")
            else:
                store.review_item(run_id, spec_id, approve=action == "approve", reason=reason)
            if action != "revise":
                from vbagent.authoring.publication import (
                    assemble_generated_run,
                    publication_stage,
                )

                publication = assemble_generated_run(store, run_id)
                if store.get_run(run_id)["status"] == RunStatus.COMPLETED.value:
                    store.set_run_stage(run_id, None, publication_stage(store.stats(run_id), publication))
                store.write_run_manifest(run_id)
            item = store.get_run_item(run_id, spec_id)
            status = self._status_from_store(store, run_id)
        return ReviewResult(
            run_id=run_id,
            spec_id=spec_id,
            decision={"approve": "approved", "reject": "rejected", "keep": "kept", "revise": "revision_requested"}[action],
            item_status=item["status"],
            run_status=status,
        )

    def get_final_artifact(self, run_id: str, spec_id: str) -> ArtifactResult:
        from vbagent.authoring.exports import get_export
        from vbagent.authoring.results import AuthoredCandidate

        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)
            item = store.get_run_item(run_id, spec_id)
            if item["status"] not in {ItemStatus.ACCEPTED.value, ItemStatus.DRAFT.value, ItemStatus.NEEDS_REVIEW.value}:
                raise ValueError(
                    f"item {spec_id} is {item['status']}; readable artifacts require accepted, draft, or needs_review status"
                )
            spec = GenerationSpec.model_validate_json(item["spec_json"])
            canonical = generated_artifact_path(Path(run["output_dir"]), run_id, spec)
            if item["status"] == ItemStatus.ACCEPTED.value:
                self._assert_published_path(canonical, run_id)
                if not canonical.is_file():
                    raise FileNotFoundError(f"published artifact is missing for accepted item {spec_id}")
                content = canonical.read_text(encoding="utf-8")
            else:
                candidate = AuthoredCandidate.model_validate_json(item["last_candidate_json"])
                content = candidate.deliverable_latex
            exported = get_export(store, spec_id)
            path = generated_output_root(self.output_root) / f"problem_{exported['number']}.tex" if exported else canonical
            if not exported and item["status"] == ItemStatus.NEEDS_REVIEW.value:
                review_path = store.item_output_dir(self.output_root, run_id, spec) / "review.tex"
                if review_path.is_file():
                    path = review_path
        return ArtifactResult(
            run_id=run_id,
            spec_id=spec_id,
            path=str(path),
            content=content,
            status=item["status"],
            validated=item["status"] == ItemStatus.ACCEPTED.value,
            number=int(exported["number"]) if exported else None,
        )

    def read_final_artifact(self, run_id: str, spec_id: str) -> str:
        return self.get_final_artifact(run_id, spec_id).content

    def get_item_evidence(self, run_id: str, spec_id: str) -> EvidenceResult:
        with AuthoringStore(self.output_root) as store:
            evidence = store.item_evidence(run_id, spec_id)
        return EvidenceResult(
            run_id=run_id,
            spec_id=spec_id,
            evidence=evidence,
        )

    def read_item_evidence(self, run_id: str, spec_id: str) -> str:
        result = self.get_item_evidence(run_id, spec_id)
        return json.dumps(result.evidence, indent=2, sort_keys=True)

    def read_worker_log(
        self,
        run_id: str,
        *,
        offset: int = 0,
        limit_bytes: int = 65_536,
    ) -> WorkerLogPage:
        """Read a bounded byte page of transparent detached-agent output."""
        if offset < 0:
            raise ValueError("worker log offset cannot be negative")
        if limit_bytes < 1 or limit_bytes > 262_144:
            raise ValueError("worker log limit_bytes must be between 1 and 262144")
        with AuthoringStore(self.output_root) as store:
            run = store.get_run(run_id)

        path = self.output_root / "runs" / run_id / "worker.log"
        self._assert_controlled_path(path)
        if not path.exists():
            return WorkerLogPage(
                run_id=run_id,
                run_status=run["status"],
                offset=offset,
                next_offset=offset,
                eof=True,
                content="",
            )

        size = path.stat().st_size
        effective_offset = min(offset, size)
        with path.open("rb") as handle:
            handle.seek(effective_offset)
            payload = handle.read(limit_bytes)
            # Do not turn a Unicode character split at the page boundary into
            # replacement glyphs. UTF-8 needs at most three extra bytes.
            for _ in range(3):
                try:
                    payload.decode("utf-8")
                    break
                except UnicodeDecodeError as exc:
                    if exc.reason != "unexpected end of data":
                        break
                    extra = handle.read(1)
                    if not extra:
                        break
                    payload += extra
        next_offset = effective_offset + len(payload)
        return WorkerLogPage(
            run_id=run_id,
            run_status=run["status"],
            offset=effective_offset,
            next_offset=next_offset,
            eof=next_offset >= size,
            content=payload.decode("utf-8", errors="replace"),
        )

    def _assert_controlled_path(self, path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.output_root)
        except ValueError as exc:
            raise ValueError("artifact path escapes the configured authoring root") from exc

    def _assert_published_path(self, path: Path, run_id: str) -> None:
        resolved = path.resolve()
        root = self.output_root / "runs" / run_id / "accepted"
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("artifact path escapes the generated output root") from exc

    @staticmethod
    def _has_active_lease(run: dict[str, Any]) -> bool:
        if not run.get("lease_owner") or not run.get("lease_expires_at"):
            return False
        try:
            expires = datetime.fromisoformat(run["lease_expires_at"])
        except (TypeError, ValueError):
            return False
        return expires > datetime.now(UTC)

    @staticmethod
    def _worker_from_dispatch(dispatch: dict[str, Any] | None) -> WorkerLaunch | None:
        if not dispatch or not dispatch.get("pid") or not dispatch.get("log_path"):
            return None
        return WorkerLaunch(
            pid=int(dispatch["pid"]),
            log_path=str(dispatch["log_path"]),
        )

    @staticmethod
    def _worker_state(dispatch: dict[str, Any] | None) -> WorkerState | None:
        if not dispatch:
            return None
        return WorkerState(
            status=str(dispatch["status"]),
            pid=int(dispatch["pid"]) if dispatch.get("pid") is not None else None,
            resume=bool(dispatch["resume"]),
            log_path=str(dispatch["log_path"]) if dispatch.get("log_path") else None,
            error_message=(
                str(dispatch["error_message"])
                if dispatch.get("error_message")
                else None
            ),
            created_at=str(dispatch["created_at"]),
            updated_at=str(dispatch["updated_at"]),
            finished_at=(
                str(dispatch["finished_at"])
                if dispatch.get("finished_at")
                else None
            ),
        )
