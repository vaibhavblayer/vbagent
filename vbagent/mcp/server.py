"""Typed MCP server for durable syllabus-driven problem authoring."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, TypeVar

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ResourceError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vbagent.authoring.application import (
    ArtifactResult,
    AuthoringApplication,
    AuthoringIntent,
    CatalogInspectionResult,
    CatalogListResult,
    CatalogSearchResult,
    CatalogTopicPageResult,
    EvidenceResult,
    ItemPageResult,
    PlanResult,
    ReviewResult,
    RunCommandResult,
    RunStatusResult,
    WorkerLogPage,
)
from vbagent.authoring.models import Subject
from vbagent.authoring.service import RunLeaseError
from vbagent.authoring.store import ItemStatus

logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT", bound=BaseModel)


SERVER_INSTRUCTIONS = """VBAgent authoring creates durable, syllabus-bound problems.

For a natural-language creation request:
1. If the user already supplied a supported exam and subject, call
   authoring_search_catalog directly with the user's exact topic words. Use
   authoring_list_catalogs only when the exam or subject is missing or
   ambiguous; do not add that extra model/tool round trip unnecessarily.
   Search runs inside VBAgent and returns only compact matches.
   Use the returned allowed_question_types IDs exactly (`mcq_sc` for a
   single-correct MCQ and `integer` for an allowed JEE numerical response).
   If browsing is needed, authoring_inspect_catalog returns chapter summaries
   only; after a chapter is selected, authoring_list_topics returns only that
   chapter's bounded topic page. Never request a whole subject topic tree.
2. Use authoring_plan first. Planning is deterministic and makes no model calls.
3. Inspect and report the resolved distribution, item count, warnings, and
   estimated model calls. Decide authorization from the user's original intent:
   an explicit instruction to create, generate, author, make, or produce the
   problems already authorizes a background start. A request to plan, preflight,
   preview, show-before-starting, or an ambiguous exploratory question does not;
   ask "Start this generation in the background?" and wait.
4. Call authoring_start with confirmed=true only when either the original direct
   creation instruction or a later confirmation supplies that authorization.
5. Poll authoring_status and use paginated authoring_list_items. Do not request
   every candidate body for a large run.
6. On completion, report generated_output_dir. Use authoring_read_final for
   authored items; inspect its status and validated flag before calling a draft
   accepted. It returns complete LaTeX and the exact saved path. Use
   authoring_read_evidence for the audit trail of one selected item.
7. authoring_read_worker_log exposes bounded raw agent I/O for operator
   transparency; do not treat terminal text as authoritative run state.

Use authoring_plan_variants only with an accepted parent spec_id. Cancellation
is cooperative and durable. A cancelled run can be resumed only after explicit
user authorization. The MCP host model handles conversation; VBAgent's configured
agent roles choose Luna, Terra, or Sol for the actual authoring stages.

Select include_solution/include_idea from the user's requested components.
Use authoring_plan(complete_run_id=...) to add missing parts without regenerating
questions. Use authoring_start(rebuild_only=true) to export and compile existing
results without generation calls. A direct instruction to compile or include
selected problems authorizes that rebuild; do not require a second approval.
Pass problem_numbers=[6, 7] when asked to include only problem_6.tex and problem_7.tex;
these are workspace-wide human file numbers, not run-local item ordinals.
Never silently drop a requested selection. If the scope is unclear, ask a direct
question and wait for the answer. Active generation workers automatically compile
on completion; a request to compile afterward does not authorize starting a pending run.
Numbered human copies live in agentic/generated;
main.tex, main.pdf and answer_key.tex live at the project root.
Machine check failures await author review after retries. Ask whether to keep,
revise or reject; never reject on the author's behalf. Approval cannot bypass
missing correctness or compilation checks.
"""


class MCPErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ToolResponse(BaseModel, Generic[ResultT]):  # noqa: UP046
    """Output envelope used for both successful and protocol-error results."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    data: ResultT | None = None
    error: MCPErrorDetail | None = None


CatalogListResponse = ToolResponse[CatalogListResult]
CatalogSearchResponse = ToolResponse[CatalogSearchResult]
CatalogInspectionResponse = ToolResponse[CatalogInspectionResult]
CatalogTopicPageResponse = ToolResponse[CatalogTopicPageResult]
PlanResponse = ToolResponse[PlanResult]
RunStatusResponse = ToolResponse[RunStatusResult]
RunCommandResponse = ToolResponse[RunCommandResult]
ItemPageResponse = ToolResponse[ItemPageResult]
ReviewResponse = ToolResponse[ReviewResult]
ArtifactResponse = ToolResponse[ArtifactResult]
EvidenceResponse = ToolResponse[EvidenceResult]
WorkerLogResponse = ToolResponse[WorkerLogPage]


def _call_result(payload: BaseModel, *, is_error: bool = False) -> CallToolResult:
    structured = payload.model_dump(mode="json")
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(structured, indent=2, sort_keys=True),
            )
        ],
        structuredContent=structured,
        isError=is_error,
    )


def _error_detail(exc: Exception) -> MCPErrorDetail:
    details: list[dict[str, Any]] = []
    if isinstance(exc, ValidationError):
        code = "validation_error"
        details = exc.errors(include_url=False, include_context=False)
    elif isinstance(exc, KeyError | FileNotFoundError):
        code = "not_found"
    elif isinstance(exc, RunLeaseError):
        code = "run_conflict"
    elif isinstance(exc, ValueError):
        code = "invalid_request"
    elif isinstance(exc, RuntimeError):
        code = "execution_error"
    else:
        code = "internal_error"
        logger.exception("Unhandled MCP authoring failure", exc_info=exc)
    message = str(exc)
    if isinstance(exc, KeyError) and exc.args:
        message = str(exc.args[0])
    return MCPErrorDetail(code=code, message=message, details=details)


async def _invoke(  # noqa: UP047
    response_type: type[ToolResponse[ResultT]],
    operation: Callable[[], ResultT],
) -> CallToolResult:
    try:
        data = await asyncio.to_thread(operation)
    except Exception as exc:  # noqa: BLE001 - domain failures become MCP errors
        return _call_result(
            response_type(ok=False, error=_error_detail(exc)),
            is_error=True,
        )
    return _call_result(response_type(ok=True, data=data))


def _annotations(
    title: str,
    *,
    read_only: bool,
    idempotent: bool,
    open_world: bool,
    destructive: bool = False,
) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=open_world,
    )


class MCPServer:
    """Authoring-focused FastMCP server backed by one controlled workspace."""

    def __init__(
        self,
        output_root: str | Path = "agentic/authoring",
        *,
        application: AuthoringApplication | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_level: str = "INFO",
    ) -> None:
        self.application = application or AuthoringApplication(output_root)
        self.server = FastMCP(
            "vbagent-authoring",
            instructions=SERVER_INSTRUCTIONS,
            host=host,
            port=port,
            log_level=log_level.upper(),
        )
        self._register_tools()
        self._register_resources()

    def _register_tools(self) -> None:
        app = self.application

        @self.server.tool(
            name="authoring_list_catalogs",
            title="List authoring catalogs",
            description=(
                "List built-in exam and subject catalogs, their versions, sizes, "
                "and allowed question types. Use before planning."
            ),
            annotations=_annotations(
                "List authoring catalogs",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_list_catalogs() -> Annotated[
            CallToolResult,
            CatalogListResponse,
        ]:
            return await _invoke(CatalogListResponse, app.list_catalogs)

        @self.server.tool(
            name="authoring_search_catalog",
            title="Search one syllabus catalog",
            description=(
                "Search chapter titles, topic titles, and familiar aliases in one "
                "built-in catalog. Returns compact matches instead of the complete "
                "subject tree; prefer this for natural-language creation requests."
            ),
            annotations=_annotations(
                "Search one syllabus catalog",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_search_catalog(
            exam: str,
            subject: Subject,
            query: str = Field(
                min_length=1,
                description="User's exact chapter or topic wording",
            ),
            limit: int = Field(default=20, ge=1, le=50),
        ) -> Annotated[CallToolResult, CatalogSearchResponse]:
            return await _invoke(
                CatalogSearchResponse,
                lambda: app.search_catalog(
                    exam,
                    subject,
                    query,
                    limit=limit,
                ),
            )

        @self.server.tool(
            name="authoring_inspect_catalog",
            title="Inspect one syllabus catalog",
            description=(
                "Inspect official provenance, exam pattern, allowed question types, "
                "and chapter summaries for one built-in catalog. Deliberately omits "
                "the subject-wide topic tree."
            ),
            annotations=_annotations(
                "Inspect one syllabus catalog",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_inspect_catalog(
            exam: str,
            subject: Subject,
        ) -> Annotated[CallToolResult, CatalogInspectionResponse]:
            return await _invoke(
                CatalogInspectionResponse,
                lambda: app.inspect_catalog(exam, subject),
            )

        @self.server.tool(
            name="authoring_list_topics",
            title="List topics in one syllabus chapter",
            description=(
                "Return a bounded topic page for one uniquely resolved chapter. "
                "Call only after selecting a chapter; never loads other chapters' topics."
            ),
            annotations=_annotations(
                "List topics in one syllabus chapter",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_list_topics(
            exam: str,
            subject: Subject,
            chapter: str = Field(
                min_length=1,
                description="Exact or uniquely resolvable chapter title or ID",
            ),
            offset: int = Field(default=0, ge=0),
            limit: int = Field(default=50, ge=1, le=100),
        ) -> Annotated[CallToolResult, CatalogTopicPageResponse]:
            return await _invoke(
                CatalogTopicPageResponse,
                lambda: app.list_catalog_topics(
                    exam,
                    subject,
                    chapter,
                    offset=offset,
                    limit=limit,
                ),
            )

        @self.server.tool(
            name="authoring_plan",
            title="Plan a durable authoring run",
            description=(
                "Resolve a typed natural-language intent against the syllabus and "
                "persist an immutable run plan without making model calls. Select "
                "include_solution/include_idea explicitly when requested. To add "
                "missing parts to existing questions, pass complete_run_id and "
                "optional complete_spec_ids; this preserves the numbered files."
            ),
            annotations=_annotations(
                "Plan a durable authoring run",
                read_only=False,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_plan(
            intent: AuthoringIntent,
            max_attempts: int = Field(default=3, ge=1, le=20),
            concurrency: int = Field(default=2, ge=1, le=32),
            include_existing_coverage: bool = True,
            complete_run_id: str | None = None,
            complete_spec_ids: list[str] | None = None,
        ) -> Annotated[CallToolResult, PlanResponse]:
            return await _invoke(
                PlanResponse,
                lambda: app.plan(
                    intent,
                    max_attempts=max_attempts,
                    concurrency=concurrency,
                    include_existing_coverage=include_existing_coverage,
                    complete_run_id=complete_run_id,
                    complete_spec_ids=complete_spec_ids,
                ),
            )

        @self.server.tool(
            name="authoring_start",
            title="Start a confirmed authoring run",
            description=(
                "Dispatch a detached worker for a persisted plan. Set confirmed=true "
                "only when the original message directly requested creation or the "
                "user later approved the inspected plan and cost. For export, "
                "assembly or compilation of existing files, use rebuild_only=true; "
                "this works for completed runs without regenerating problems. "
                "Use problem_numbers for an explicit subset of human problem_N.tex files."
            ),
            annotations=_annotations(
                "Start a confirmed authoring run",
                read_only=False,
                idempotent=True,
                open_world=True,
            ),
            structured_output=True,
        )
        async def authoring_start(
            run_id: str,
            confirmed: bool = Field(
                default=False,
                description=(
                    "True only after a direct user creation/rebuild instruction or a later "
                    "explicit confirmation"
                ),
            ),
            concurrency: int | None = Field(default=None, ge=1, le=32),
            rebuild_only: bool = Field(default=False, description="Export and compile existing items only, including completed runs; no generation calls"),
            problem_numbers: list[Annotated[int, Field(strict=True, gt=0)]] | None = Field(
                default=None, min_length=1, max_length=1000,
                description="Only with rebuild_only=true: exact human problem_N.tex numbers to include, e.g. [6, 7]. Omit for all eligible problems. Missing or unverified selections fail without replacing the root document.",
            ),
        ) -> Annotated[CallToolResult, RunCommandResponse]:
            return await _invoke(
                RunCommandResponse,
                lambda: app.start(
                    run_id,
                    confirmed=confirmed,
                    concurrency=concurrency,
                    rebuild_only=rebuild_only,
                    problem_numbers=problem_numbers,
                ),
            )

        @self.server.tool(
            name="authoring_status",
            title="Read durable run status",
            description=(
                "Read authoritative counts, usage and prompt-cache telemetry, "
                "failure reasons, coverage, lease state, generated output path, "
                "and resource templates."
            ),
            annotations=_annotations(
                "Read durable run status",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_status(
            run_id: str,
        ) -> Annotated[CallToolResult, RunStatusResponse]:
            return await _invoke(RunStatusResponse, lambda: app.status(run_id))

        @self.server.tool(
            name="authoring_list_items",
            title="List authoring items",
            description=(
                "List a bounded page of item metadata. Candidate bodies are excluded "
                "by default; use item resources for accepted artifacts or evidence."
            ),
            annotations=_annotations(
                "List authoring items",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_list_items(
            run_id: str,
            offset: int = Field(default=0, ge=0),
            limit: int = Field(default=50, ge=1, le=200),
            status: ItemStatus | None = None,
        ) -> Annotated[CallToolResult, ItemPageResponse]:
            return await _invoke(
                ItemPageResponse,
                lambda: app.list_items(
                    run_id,
                    offset=offset,
                    limit=limit,
                    status=status.value if status is not None else None,
                    include_candidate=False,
                ),
            )

        @self.server.tool(
            name="authoring_cancel",
            title="Cancel an authoring run",
            description=(
                "Request cooperative cancellation while preserving all completed "
                "items, attempts, evidence, and accepted artifacts."
            ),
            annotations=_annotations(
                "Cancel an authoring run",
                read_only=False,
                idempotent=True,
                open_world=False,
                destructive=True,
            ),
            structured_output=True,
        )
        async def authoring_cancel(
            run_id: str,
            reason: str = "user requested cancellation",
        ) -> Annotated[CallToolResult, RunCommandResponse]:
            return await _invoke(
                RunCommandResponse,
                lambda: app.cancel(run_id, reason),
            )

        @self.server.tool(
            name="authoring_resume",
            title="Resume a cancelled authoring run",
            description=(
                "Resume retryable work in a cancelled run using a detached worker. "
                "Set confirmed=true only after a direct user resume instruction or "
                "a later explicit confirmation."
            ),
            annotations=_annotations(
                "Resume a cancelled authoring run",
                read_only=False,
                idempotent=True,
                open_world=True,
            ),
            structured_output=True,
        )
        async def authoring_resume(
            run_id: str,
            confirmed: bool = Field(
                default=False,
                description=(
                    "True only after a direct user resume instruction or a later "
                    "explicit confirmation"
                ),
            ),
            concurrency: int | None = Field(default=None, ge=1, le=32),
        ) -> Annotated[CallToolResult, RunCommandResponse]:
            return await _invoke(
                RunCommandResponse,
                lambda: app.resume(
                    run_id,
                    confirmed=confirmed,
                    concurrency=concurrency,
                ),
            )

        @self.server.tool(
            name="authoring_review",
            title="Review one authoring item",
            description=(
                "Record the AUTHOR's choice for a needs_review item: keep, revise, "
                "approve, or reject, with a reason. Never reject automatically. "
                "Revise queues one more attempt; start it after user authorization. "
                "Approval requires completed correctness/compile checks and repeats novelty."
            ),
            annotations=_annotations(
                "Review one authoring item",
                read_only=False,
                idempotent=False,
                open_world=False,
                destructive=True,
            ),
            structured_output=True,
        )
        async def authoring_review(
            run_id: str,
            spec_id: str,
            reason: str,
            approve: bool | None = None,
            decision: Literal["approve", "reject", "keep", "revise"] | None = None,
        ) -> Annotated[CallToolResult, ReviewResponse]:
            return await _invoke(
                ReviewResponse,
                lambda: app.review(
                    run_id,
                    spec_id,
                    approve=approve,
                    reason=reason,
                    decision=decision,
                ),
            )

        @self.server.tool(
            name="authoring_plan_variants",
            title="Plan controlled problem variants",
            description=(
                "Create a no-model-call durable plan for variants of one accepted "
                "canonical parent, retaining syllabus identity and lineage controls."
            ),
            annotations=_annotations(
                "Plan controlled problem variants",
                read_only=False,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_plan_variants(
            parent_spec_id: str,
            count: int = Field(default=1, ge=1, le=1000),
            variant_families: dict[str, float] | None = None,
            seed: int = 0,
            human_review_required: bool | None = None,
            max_attempts: int = Field(default=3, ge=1, le=20),
            concurrency: int = Field(default=2, ge=1, le=32),
            max_lineage_depth: int = Field(default=2, ge=1, le=5),
            max_variants_per_parent: int = Field(default=12, ge=1, le=1000),
        ) -> Annotated[CallToolResult, PlanResponse]:
            return await _invoke(
                PlanResponse,
                lambda: app.plan_controlled_variants(
                    parent_spec_id,
                    count=count,
                    variant_families=variant_families,
                    seed=seed,
                    human_review_required=human_review_required,
                    max_attempts=max_attempts,
                    concurrency=concurrency,
                    max_lineage_depth=max_lineage_depth,
                    max_variants_per_parent=max_variants_per_parent,
                ),
            )

        @self.server.tool(
            name="authoring_read_final",
            title="Read one authored artifact",
            description=(
                "Read complete LaTeX and its numbered path for an accepted item, "
                "explicitly requested draft, or review-pending draft. Check status "
                "and validated: drafts are not certified answers."
            ),
            annotations=_annotations(
                "Read one authored artifact",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_read_final(
            run_id: str,
            spec_id: str,
        ) -> Annotated[CallToolResult, ArtifactResponse]:
            return await _invoke(
                ArtifactResponse,
                lambda: app.get_final_artifact(run_id, spec_id),
            )

        @self.server.tool(
            name="authoring_read_evidence",
            title="Read one item audit trail",
            description=(
                "Read the immutable specification, attempts, candidates, ordered "
                "quality gates, and human review state for one item."
            ),
            annotations=_annotations(
                "Read one item audit trail",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_read_evidence(
            run_id: str,
            spec_id: str,
        ) -> Annotated[CallToolResult, EvidenceResponse]:
            return await _invoke(
                EvidenceResponse,
                lambda: app.get_item_evidence(run_id, spec_id),
            )

        @self.server.tool(
            name="authoring_read_worker_log",
            title="Read detached agent I/O",
            description=(
                "Read one bounded byte page from the detached worker log. This is "
                "transparent raw agent I/O; authoring_status remains authoritative."
            ),
            annotations=_annotations(
                "Read detached agent I/O",
                read_only=True,
                idempotent=True,
                open_world=False,
            ),
            structured_output=True,
        )
        async def authoring_read_worker_log(
            run_id: str,
            offset: int = Field(default=0, ge=0),
            limit_bytes: int = Field(default=65_536, ge=1, le=262_144),
        ) -> Annotated[CallToolResult, WorkerLogResponse]:
            return await _invoke(
                WorkerLogResponse,
                lambda: app.read_worker_log(
                    run_id,
                    offset=offset,
                    limit_bytes=limit_bytes,
                ),
            )

    def _register_resources(self) -> None:
        app = self.application

        @self.server.resource(
            "vbagent://authoring/runs/{run_id}/items/{spec_id}/final",
            name="authoring-artifact",
            title="Authored artifact with validation status",
            description="Authored LaTeX with status and validated fields in a leading TeX comment.",
            mime_type="text/x-tex",
        )
        def authored_artifact(run_id: str, spec_id: str) -> str:
            try:
                artifact = app.get_final_artifact(run_id, spec_id)
                return (
                    f"% VBAgent artifact status: {artifact.status}; "
                    f"validated={str(artifact.validated).lower()}\n"
                    + artifact.content
                )
            except Exception as exc:
                raise ResourceError(_error_detail(exc).message) from exc

        @self.server.resource(
            "vbagent://authoring/runs/{run_id}/items/{spec_id}/evidence",
            name="authoring-item-evidence",
            title="Authoring item evidence",
            description="Immutable specification, attempts, candidates, and ordered gates.",
            mime_type="application/json",
        )
        def item_evidence(run_id: str, spec_id: str) -> str:
            try:
                return app.read_item_evidence(run_id, spec_id)
            except Exception as exc:
                raise ResourceError(_error_detail(exc).message) from exc

    async def list_tools(self):
        """Expose FastMCP discovery for local tests and embedded clients."""
        return await self.server.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        """Execute one tool through FastMCP's validation/conversion layer."""
        return await self.server.call_tool(name, arguments)

    def run(self, transport: str = "stdio") -> None:
        """Run the configured FastMCP transport."""
        self.server.run(transport=transport)
