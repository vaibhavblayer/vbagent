"""Transparent CLI conversation host built from the FastMCP authoring contract."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, TypeVar

from vbagent.mcp.chat_intent import (
    DEFAULT_CHAT_REASONING_EFFORT,
    ChatIntent,
    classify_authoring_intent,
)
from vbagent.mcp.server import SERVER_INSTRUCTIONS, MCPServer

TracePhase = Literal["input", "output", "error", "worker_output"]


@dataclass(frozen=True)
class ToolTraceEvent:
    """One user-visible MCP invocation or detached-agent output event."""

    phase: TracePhase
    tool_name: str
    payload: Any
    is_error: bool = False


TraceSink = Callable[[ToolTraceEvent], None]
ApprovalHandler = Callable[[str, dict[str, Any]], bool | None]
ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class PendingRunConfirmation:
    """Latest planned run that the terminal may start without another model turn."""

    run_id: str
    concurrency: int | None
    estimated_agent_calls: int | None = None


@dataclass(frozen=True)
class LatestRunState:
    """Compact, continuously refreshed state for the latest generation."""

    run_id: str
    status: str
    exam: str = ""
    subject: str = ""
    chapters: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    total_items: int = 0
    accepted: int = 0
    needs_review: int = 0
    draft: int = 0
    failed: int = 0
    generated_output_dir: str = ""
    generated_manifest_path: str | None = None
    worker_status: str | None = None
    current_stage: str | None = None
    stage_updated_at: str | None = None
    active_stages: tuple[dict[str, Any], ...] = ()
    stage_counts: dict[str, int] | None = None
    progress_counts: dict[str, int] | None = None
    latest_failure: dict[str, Any] | None = None
    publication: dict[str, Any] | None = None

    @property
    def completion_ready(self) -> bool:
        if self.status == "worker_failed":
            return True
        return self.status in {"completed", "cancelled"} and self.worker_status not in {
            "launching",
            "started",
        }

    def prompt_label(self) -> str:
        """Return a bounded one-line label for the terminal toolbar."""
        active = self.active_stages[0] if self.active_stages else {}
        scope = str(active.get("topic") or (self.topics[0] if self.topics else (
            self.chapters[0] if self.chapters else self.subject
        )))
        if len(scope) > 48:
            scope = scope[:45].rstrip() + "..."
        counts = self.progress_counts or {}
        progress = [
            f"drafted {counts.get('drafted', self.accepted)}/{self.total_items}",
            f"accepted {self.accepted}/{self.total_items}",
        ]
        if self.draft:
            progress.append(f"unverified drafts {self.draft}")
        for key in ("checking", "retrying", "needs_review", "unsuccessful"):
            if counts.get(key):
                progress.append(f"{key.replace('_', ' ')} {counts[key]}")
        stage = (self.current_stage or "").replace("_", " ")
        if len(stage) > 34:
            stage = stage[:31].rstrip() + "..."
        if active:
            stage = f"#{active['ordinal']} {stage}"
            if int(active.get("attempt", 1)) > 1:
                stage += f" (try {active['attempt']})"
        if (counts.get("retrying") or counts.get("unsuccessful")) and self.latest_failure:
            progress.append(f"last: {str(self.latest_failure.get('gate', '')).replace('_', ' ')}")
        parts = [self.status, *progress, stage, scope, self.run_id[:12]]
        return " · ".join(part for part in parts if part)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "exam": self.exam,
            "subject": self.subject,
            "chapters": list(self.chapters),
            "topics": list(self.topics),
            "progress": {
                **dict(self.progress_counts or {}),
                "accepted": self.accepted,
                "total": self.total_items,
                "needs_review": self.needs_review,
                "draft": self.draft,
                "failed": self.failed,
            },
            "worker_status": self.worker_status,
            "current_stage": self.current_stage,
            "stage_updated_at": self.stage_updated_at,
            "active_stages": [dict(item) for item in self.active_stages],
            "stage_counts": dict(self.stage_counts or {}),
            "latest_failure": self.latest_failure,
            "generated_output_dir": self.generated_output_dir,
            "generated_manifest_path": self.generated_manifest_path,
            "publication": self.publication,
        }


@dataclass(frozen=True)
class PendingToolApproval:
    """Consequential tool call staged until the terminal explicitly approves it."""

    name: str
    arguments: dict[str, Any]


CLI_CONTROLLER_INSTRUCTIONS = f"""{SERVER_INSTRUCTIONS}

You are the VBAgent terminal authoring controller. Be concise and operational.
The terminal renders every tool input and output, so do not repeat large JSON
payloads. Summarize only the fields the user needs to decide what to do next.
For ordinary conversation, answer in one to three brief sentences. Do not add
headings, decorative symbols, or LaTeX unless the user asks for them or the
mathematics cannot be stated clearly without it.
Use the canonical question-type IDs returned by catalog search: `mcq_sc` means
single-correct MCQ and `integer` means JEE numerical/integer response. Never
invent a friendlier alias. Omit optional intent fields the user did not request,
including `human_review_required`, so deterministic defaults remain effective.

After authoring_plan or authoring_plan_variants, always stop and present the
resolved scope, distribution, warnings, and estimated calls. Never call
authoring_start in the same model turn as planning. The terminal applies the
original user's intent deterministically after this turn: an explicit request
to create, generate, author, make, or produce problems authorizes an immediate
background start; a request for a plan, preflight, preview, or approval first
remains pending. Match your short closing sentence to that distinction, but do
not claim the run started until the terminal reports it. A later plain `yes`,
`confirm`, or `go ahead` approves the displayed action locally, without another
controller round trip. A plain `no` declines it. A direct start/resume or compile
instruction already authorizes that specific action on the identified run.
Never request a second approval for an explicitly authorized action. If a tool
reports `approval_required`, ask its specific approval question directly; do not
tell the user they must type a slash command. Never wait for terminal input inside
a tool call. Ask for missing scope instead of guessing what the user approved.

Use authoring_status for authoritative progress. When a run completes, report
its generated_output_dir and use authoring_read_final when full authored LaTeX
is requested, including its validation status. Raw worker logs may be large;
inspect them only when the user asks. Do not invent run IDs, spec IDs, syllabus
names, saved paths, tool results, or completion.

Respect requested components: set include_solution=false for idea-only or
question-only drafts, and include_idea=false for solution-only output. Deferred
solutions are not secretly generated. To add missing parts later, use
authoring_plan with complete_run_id and optional complete_spec_ids; preserve the
questions and existing components. Use authoring_start(rebuild_only=true) for
requests to export, assemble or compile existing results, not a new creation plan.
For "only include problems 6 and 7", pass problem_numbers=[6, 7] and rebuild_only=true.
These are human problem_N.tex numbers, not run-local ordinals. Never omit a
requested selection or rebuild the whole collection as a substitute.
"Compile after completion" is not permission to start a pending generation.
Check status: active workers automatically assemble and compile on completion;
acknowledge that without starting or rebuilding them. If still pending, explain
that it has not started and ask "Start this generation in the background?".
For completed runs, the explicit compile request authorizes a rebuild.
Human copies are agentic/generated/problem_N.tex with JSON metadata, and the
assembled main.tex, main.pdf and answer_key.tex are at the project root.
At the end, ask the author about needs_review items: keep, revise, approve when
checks permit it, or reject. Never choose rejection on the author's behalf.
Keeping preserves a draft and does not certify it. Revision queues one extra
attempt; starting that attempt requires the author's revision instruction.
"""


_APPROVAL_TOOLS = {
    "authoring_start",
    "authoring_resume",
    "authoring_cancel",
    "authoring_review",
}
_WORKER_ACTIVITY_TOOLS = {
    "authoring_start",
    "authoring_resume",
    "authoring_status",
}
_PLANNING_TOOLS = {
    "authoring_list_catalogs",
    "authoring_search_catalog",
    "authoring_inspect_catalog",
    "authoring_list_topics",
    "authoring_plan",
    "authoring_plan_variants",
}


def _run_async(factory: Callable[[], Awaitable[ResultT]]) -> ResultT:  # noqa: UP047
    """Run an async MCP operation from ordinary or already-async callers."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    holder: dict[str, Any] = {"result": None, "error": None}

    def worker() -> None:
        try:
            holder["result"] = asyncio.run(factory())
        except BaseException as exc:  # noqa: BLE001  # pragma: no cover
            holder["error"] = exc

    thread = threading.Thread(target=worker, daemon=False)
    thread.start()
    thread.join()
    if holder["error"] is not None:
        raise holder["error"]
    return holder["result"]


class AuthoringChatSession:
    """One cache-aware controller session over the exact in-process MCP tools."""

    def __init__(
        self,
        output_root: str | Path = "agentic/authoring",
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        trace_sink: TraceSink | None = None,
        approval_handler: ApprovalHandler | None = None,
        timeout: float | None = None,
        mirror_worker_io: bool = True,
        allow_intent_actions: bool = True,
    ) -> None:
        from vbagent.config import get_model

        self.output_root = Path(output_root).expanduser().resolve()
        self.model = model or get_model("default")
        # Chat routing needs enough reasoning for multi-turn scope and intent.
        # Generation/review agents retain their independently configured levels.
        self.reasoning_effort = reasoning_effort or DEFAULT_CHAT_REASONING_EFFORT
        self.trace_sink = trace_sink
        self.approval_handler = approval_handler
        self.timeout = timeout
        self.mirror_worker_io = mirror_worker_io
        self.allow_intent_actions = allow_intent_actions
        self.group_id = f"vbagent:authoring-chat:v1:{uuid.uuid4().hex}"
        self.previous_response_id: str | None = None
        self.credentials = None
        self._history: list[dict[str, str]] = []
        self._worker_offsets: dict[str, int] = {}
        self._worker_log_lock = threading.RLock()
        self._turn_tool_calls = 0
        self._turn_intent: ChatIntent | None = None
        self._turn_run_id: str | None = None
        self._turn_planned_run_ids: set[str] = set()
        self._authorized_pending_run_id: str | None = None
        self._pending_run_confirmation: PendingRunConfirmation | None = None
        self._pending_tool_approval: PendingToolApproval | None = None
        self._latest_run_state: LatestRunState | None = None
        self._reported_completions: set[str] = set()
        self._state_lock = threading.RLock()
        self._server: MCPServer | None = None
        self._tools: list[Any] | None = None
        self._tool_by_name: dict[str, Any] = {}
        self._agent = None

    @property
    def server(self) -> MCPServer:
        """Construct FastMCP only when a message or direct command needs it."""
        if self._server is None:
            self._server = MCPServer(output_root=self.output_root)
        return self._server

    @property
    def server_ready(self) -> bool:
        return self._server is not None

    @property
    def agent(self):
        """Build the controller and deferred tool namespaces on first use."""
        if self._agent is None:
            self._agent = self._create_controller_agent()
        return self._agent

    @property
    def controller_ready(self) -> bool:
        return self._agent is not None

    def prepare_controller(self) -> None:
        """Discover MCP metadata and build deferred namespaces on demand."""
        _ = self.agent

    def _ensure_tools(self) -> list[Any]:
        if self._tools is None:
            self._tools = _run_async(self.server.list_tools)
            self._tool_by_name = {tool.name: tool for tool in self._tools}
        return self._tools

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self._ensure_tools())

    def tool_descriptions(self) -> list[tuple[str, str]]:
        return [
            (tool.name, tool.description or "") for tool in self._ensure_tools()
        ]

    @property
    def pending_run_id(self) -> str | None:
        pending = self._pending_run_confirmation
        return pending.run_id if pending is not None else None

    @property
    def pending_tool_name(self) -> str | None:
        pending = self._pending_tool_approval
        return pending.name if pending is not None else None

    @property
    def authorized_pending_run_id(self) -> str | None:
        """Only the current request's matching plan may auto-start after a turn."""
        return self._authorized_pending_run_id

    @property
    def latest_run_state(self) -> LatestRunState | None:
        with self._state_lock:
            return self._latest_run_state

    @property
    def latest_run_label(self) -> str | None:
        state = self.latest_run_state
        return state.prompt_label() if state is not None else None

    def pending_approval(self) -> dict[str, Any] | None:
        """One explicit question for the next locally approvable action."""
        tool = self._pending_tool_approval
        if tool is not None:
            run_id = str(tool.arguments.get("run_id") or "")
            state = self.latest_run_state
            questions = {
                "authoring_start": "Start this generation in the background?",
                "authoring_resume": "Resume this generation in the background?",
                "authoring_cancel": "Cancel this generation?",
                "authoring_review": "Apply this author review decision?",
            }
            question = questions.get(tool.name, f"Run {tool.name}?")
            if tool.name == "authoring_review" and tool.arguments.get("decision"):
                question = f"Apply the '{tool.arguments['decision']}' review decision to this problem?"
            if tool.name == "authoring_start" and tool.arguments.get("rebuild_only"):
                numbers = tool.arguments.get("problem_numbers")
                question = (
                    f"Rebuild main.tex and main.pdf using only problems {', '.join(map(str, numbers))}?"
                    if numbers else "Rebuild main.tex, main.pdf and answer_key.tex from existing problems?"
                )
            return {
                "event": "approval_required", "action": tool.name,
                "run": state.as_dict() if state and state.run_id == run_id else {"run_id": run_id},
                "arguments": dict(tool.arguments),
                "question": question + " Reply yes or no.",
            }
        pending = self._pending_run_confirmation
        state = self.latest_run_state
        if pending is None:
            return None
        scope = (
            state.as_dict() if state is not None and state.run_id == pending.run_id
            else {"run_id": pending.run_id}
        )
        return {
            "event": "approval_required",
            "action": "start_background_generation",
            "run": scope,
            "estimated_agent_calls": pending.estimated_agent_calls,
            "question": (
                "Start this generation in the background? "
                "Reply yes or no."
            ),
        }

    def pending_background_approval(self) -> dict[str, Any] | None:
        """Compatibility for callers displaying the former plan-only prompt."""
        return self.pending_approval()

    def clear(self) -> None:
        """Start a fresh provider response chain without touching durable runs."""
        self.previous_response_id = None
        self.credentials = None
        self._history.clear()
        self._pending_run_confirmation = None
        self._pending_tool_approval = None
        self._authorized_pending_run_id = None
        self.group_id = f"vbagent:authoring-chat:v1:{uuid.uuid4().hex}"

    def send(self, message: str, *, show_spinner: bool = True) -> str:
        """Send one natural-language turn through the configured controller model."""
        request = message.strip()
        if not request:
            raise ValueError("chat message cannot be empty")

        intent = classify_authoring_intent(request)
        self._turn_intent = intent
        state = self.latest_run_state
        self._turn_run_id = self.pending_run_id or (state.run_id if state else None)
        self._turn_planned_run_ids = set()
        self._authorized_pending_run_id = None
        if intent.policy != "unspecified":
            # A new scoped request supersedes an unexecuted older tool proposal.
            self._pending_tool_approval = None
        if intent.policy == "create_now":
            # A request for new problems must not confirm an unrelated old plan
            # if the controller needs clarification before planning this one.
            self._pending_run_confirmation = None
        try:
            return self._send_controller(request, show_spinner=show_spinner)
        finally:
            pending = self._pending_run_confirmation
            if (
                pending is not None
                and self._pending_tool_approval is None
                and self._intent_authorizes("authoring_start", {"run_id": pending.run_id})
            ):
                self._authorized_pending_run_id = pending.run_id
            self._turn_intent = None
            self._turn_run_id = None
            self._turn_planned_run_ids = set()

    def _controller_input(self, request: str, *, replay: bool = False):
        """Include compact host state so local approvals are visible next turn."""
        messages = list(self._history) if replay else []
        state = self.latest_run_state
        if state is not None:
            messages.append({
                "role": "developer",
                "content": "Last observed terminal state (use authoring_status to refresh): "
                + json.dumps({
                    "run_id": state.run_id, "status": state.status,
                    "worker_status": state.worker_status,
                    "current_stage": state.current_stage,
                    "pending_run_id": self.pending_run_id,
                    "request_intent": self._turn_intent.policy if self._turn_intent else None,
                }, sort_keys=True),
            })
        return [*messages, {"role": "user", "content": request}] if messages else request

    def _send_controller(self, request: str, *, show_spinner: bool) -> str:

        from vbagent.agents.base import (
            _provider_status_code,
            run_agent_sync_continued,
        )

        self._turn_tool_calls = 0
        input_data = self._controller_input(
            request, replay=self.previous_response_id is None and bool(self._history),
        )

        try:
            result = run_agent_sync_continued(
                self.agent,
                input_data,
                self.group_id,
                previous_response_id=self.previous_response_id,
                credentials=self.credentials,
                show_spinner=show_spinner,
                timeout=self.timeout,
            )
        except BaseException as exc:
            status_code = _provider_status_code(exc)
            can_replay_safely = (
                self.previous_response_id is not None
                and self._turn_tool_calls == 0
                and status_code in {401, 403, 429}
            )
            if not can_replay_safely:
                raise
            self._retire_continuation_profile(status_code)
            replay = self._controller_input(request, replay=True)
            result = run_agent_sync_continued(
                self.agent,
                replay,
                self.group_id,
                show_spinner=show_spinner,
                timeout=self.timeout,
            )

        output = str(result.final_output or "").strip()
        self.previous_response_id = result.response_id
        self.credentials = result.credentials if result.response_id else None
        self._history.extend(
            [
                {"role": "user", "content": request},
                {"role": "assistant", "content": output},
            ]
        )
        self._trim_history()
        return output

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke one discovered MCP tool directly for terminal slash commands."""
        self._ensure_tools()
        if name not in self._tool_by_name:
            raise ValueError(f"unknown authoring tool: {name}")
        return _run_async(lambda: self._invoke_mcp_tool(name, arguments))

    def confirm_pending_run(self) -> dict[str, Any]:
        """Start the latest planned run from one explicit terminal confirmation."""
        pending = self._pending_run_confirmation
        if pending is None:
            raise ValueError("there is no authoring plan waiting for confirmation")
        return self.confirm_run(
            pending.run_id,
            concurrency=pending.concurrency,
        )

    def confirm_run(
        self,
        run_id: str,
        *,
        concurrency: int | None = None,
    ) -> dict[str, Any]:
        """Start one persisted run named explicitly by the terminal user."""
        arguments: dict[str, Any] = {
            "run_id": run_id,
            "confirmed": True,
        }
        if concurrency is not None:
            arguments["concurrency"] = concurrency
        return _run_async(
            lambda: self._invoke_mcp_tool(
                "authoring_start",
                arguments,
                approval_granted=True,
            )
        )

    def approve_pending_tool(self) -> dict[str, Any]:
        """Execute one consequential tool call previously staged by the controller."""
        pending = self._pending_tool_approval
        if pending is None:
            raise ValueError("there is no consequential tool waiting for approval")
        self._pending_tool_approval = None
        return _run_async(
            lambda: self._invoke_mcp_tool(
                pending.name,
                dict(pending.arguments),
                approval_granted=True,
            )
        )

    def approve_pending_action(self) -> dict[str, Any]:
        """A plain yes approves exactly the most recently displayed proposal."""
        if self._pending_tool_approval is not None:
            return self.approve_pending_tool()
        return self.confirm_pending_run()

    def decline_pending_action(self) -> dict[str, Any]:
        """Decline a proposal, without cancelling or changing the durable run."""
        payload = self.pending_approval()
        if payload is None:
            raise ValueError("there is no action waiting for approval")
        run_id = str(payload["run"].get("run_id") or "")
        self._pending_tool_approval = None
        if self.pending_run_id == run_id:
            self._pending_run_confirmation = None
        self._authorized_pending_run_id = None
        return {"action": payload["action"], "run_id": run_id}

    def decline_pending_tool(self) -> str:
        """Discard one staged consequential tool call without executing it."""
        pending = self._pending_tool_approval
        if pending is None:
            raise ValueError("there is no consequential tool waiting for approval")
        self._pending_tool_approval = None
        return pending.name

    def read_new_worker_io(self, run_id: str) -> dict[str, Any]:
        """Read the next visible worker-log page without replaying prior bytes."""
        with self._worker_log_lock:
            offset = self._worker_offsets.get(run_id, 0)
            payload = self.call_tool(
                "authoring_read_worker_log",
                {"run_id": run_id, "offset": offset, "limit_bytes": 262_144},
            )
            data = payload.get("data")
            if isinstance(data, dict) and data.get("next_offset") is not None:
                self._worker_offsets[run_id] = int(data["next_offset"])
        return payload

    def poll_new_worker_io(self, run_id: str) -> dict[str, Any] | None:
        """Read one new worker-log page for a live prompt without tool noise."""
        with self._worker_log_lock:
            offset = self._worker_offsets.get(run_id, 0)
            page = self.server.application.read_worker_log(
                run_id,
                offset=offset,
                limit_bytes=262_144,
            )
            self._worker_offsets[run_id] = page.next_offset
        if not page.content:
            return None
        return page.model_dump(mode="json")

    def refresh_run_state(self, run_id: str | None = None) -> LatestRunState:
        """Refresh the latest-run indicator from the durable ledger."""
        target = run_id or (self.latest_run_state.run_id if self.latest_run_state else None)
        if target is None:
            raise ValueError("there is no latest authoring run")
        result = self.server.application.status(target)
        state = self._latest_state_from_data(result.model_dump(mode="json"))
        if state is None:  # pragma: no cover - guarded by the typed result
            raise RuntimeError(f"could not derive state for authoring run {target}")
        if state.worker_status == "failed" and state.status not in {
            "completed",
            "cancelled",
        }:
            state = replace(state, status="worker_failed")
        with self._state_lock:
            self._latest_run_state = state
        return state

    def wait_for_run_completion(
        self,
        run_id: str,
        stop_event: threading.Event,
        *,
        poll_interval: float = 1.0,
        max_code_artifacts: int = 20,
        worker_io_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any] | None:
        """Poll one detached run and return one terminal notification."""
        while not stop_event.is_set():
            state = self.refresh_run_state(run_id)
            if self.mirror_worker_io and worker_io_callback is not None:
                worker_payload = self.poll_new_worker_io(run_id)
                if worker_payload is not None:
                    worker_io_callback(worker_payload)
                # A completed multi-item run can still have more than one log
                # page waiting. Drain all remaining pages before final code.
                while (
                    state.completion_ready
                    and worker_payload is not None
                    and not worker_payload.get("eof", True)
                    and not stop_event.is_set()
                ):
                    worker_payload = self.poll_new_worker_io(run_id)
                    if worker_payload is not None:
                        worker_io_callback(worker_payload)
            if state.completion_ready:
                return self.take_completion(
                    run_id,
                    max_code_artifacts=max_code_artifacts,
                )
            stop_event.wait(poll_interval)
        return None

    def take_completion(
        self,
        run_id: str,
        *,
        max_code_artifacts: int | None = 20,
        force: bool = False,
    ) -> dict[str, Any] | None:
        """Build one completion event, suppressing duplicate automatic notices."""
        state = self.refresh_run_state(run_id)
        if not state.completion_ready:
            return None
        with self._state_lock:
            if not force and run_id in self._reported_completions:
                return None
            if not force:
                self._reported_completions.add(run_id)
        try:
            artifacts = list(
                self.iter_authored_artifacts(
                    run_id,
                    limit=max_code_artifacts,
                )
            )
        except Exception:
            if not force:
                with self._state_lock:
                    self._reported_completions.discard(run_id)
            raise
        event = {
            "completed": "generation_completed",
            "cancelled": "generation_cancelled",
            "worker_failed": "generation_worker_failed",
        }[state.status]
        review_items = []
        if state.needs_review:
            review_page = self.server.application.list_items(run_id, status="needs_review", limit=20)
            review_items = [item.model_dump(mode="json", exclude={"candidate"}) for item in review_page.items]
        return {
            "event": event,
            "run": state.as_dict(),
            "saved_to": state.generated_output_dir,
            "manifest_path": state.generated_manifest_path,
            "deliverables": state.publication,
            "accepted_artifacts": state.accepted,
            "draft_artifacts": state.draft,
            "review_prompt": (
                "These drafts need your decision. Keep for later, revise with instructions, "
                "or reject? Nothing is rejected automatically. Approval requires all correctness and compile checks."
                if state.needs_review else None
            ),
            "review_items": review_items,
            "displayed_artifacts": len(artifacts),
            "artifacts_truncated": len(artifacts) < state.accepted + state.draft + state.needs_review,
            "artifacts": artifacts,
        }

    def iter_authored_artifacts(
        self,
        run_id: str,
        *,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream authored LaTeX, validation status, and saved paths in order."""
        if limit is not None and limit < 0:
            raise ValueError("artifact display limit cannot be negative")
        offset = 0
        yielded = 0
        while limit is None or yielded < limit:
            page_limit = min(200, limit - yielded) if limit is not None else 200
            if page_limit <= 0:
                return
            page = self.server.application.list_items(
                run_id,
                offset=offset,
                limit=page_limit,
                status=None,
            )
            for item in page.items:
                if item.status not in {"accepted", "draft", "needs_review"}:
                    continue
                artifact = self.server.application.get_final_artifact(
                    run_id,
                    item.spec_id,
                )
                yield {
                    "ordinal": item.ordinal,
                    "number": artifact.number,
                    "status": artifact.status,
                    "validated": artifact.validated,
                    "spec_id": item.spec_id,
                    "exam": item.exam,
                    "subject": item.subject,
                    "chapter": item.chapter,
                    "topic": item.topic,
                    "question_type": item.question_type,
                    "path": artifact.path,
                    "content": artifact.content,
                }
                yielded += 1
            if page.next_offset is None:
                return
            offset = page.next_offset

    def _create_controller_agent(self):
        from agents import FunctionTool, ToolSearchTool, tool_namespace

        from vbagent.agents.base import create_agent
        from vbagent.config import get_model_settings

        function_tools = []
        for discovered in self._ensure_tools():
            tool_name = discovered.name

            async def invoke(_context, arguments_json: str, *, name=tool_name):
                try:
                    arguments = json.loads(arguments_json or "{}")
                except json.JSONDecodeError as exc:
                    payload = self._local_error(
                        "validation_error",
                        f"invalid JSON arguments: {exc}",
                    )
                    self._emit(ToolTraceEvent("error", name, payload, True))
                    return json.dumps(payload, sort_keys=True)
                if not isinstance(arguments, dict):
                    payload = self._local_error(
                        "validation_error",
                        "tool arguments must be a JSON object",
                    )
                    self._emit(ToolTraceEvent("error", name, payload, True))
                    return json.dumps(payload, sort_keys=True)
                payload = await self._invoke_mcp_tool(name, arguments)
                return json.dumps(payload, ensure_ascii=False, sort_keys=True)

            function_tools.append(
                FunctionTool(
                    name=tool_name,
                    description=discovered.description or tool_name,
                    params_json_schema=discovered.inputSchema,
                    on_invoke_tool=invoke,
                    strict_json_schema=False,
                    defer_loading=True,
                )
            )

        planning_tools = [
            tool for tool in function_tools if tool.name in _PLANNING_TOOLS
        ]
        operation_tools = [
            tool for tool in function_tools if tool.name not in _PLANNING_TOOLS
        ]
        deferred_tools = [
            *tool_namespace(
                name="syllabus_authoring",
                description=(
                    "Search official local syllabi and create deterministic, "
                    "approval-gated authoring plans."
                ),
                tools=planning_tools,
            ),
            *tool_namespace(
                name="authoring_runs",
                description=(
                    "Start, monitor, review, cancel, resume, and inspect durable "
                    "problem-authoring runs and artifacts."
                ),
                tools=operation_tools,
            ),
        ]

        settings = get_model_settings("default")
        settings = replace(
            settings,
            reasoning={"effort": self.reasoning_effort},
        )
        return create_agent(
            name="Problem Authoring Chat Controller",
            instructions=CLI_CONTROLLER_INSTRUCTIONS,
            model=self.model,
            model_settings=settings,
            tools=[
                ToolSearchTool(),
                *deferred_tools,
            ],
        )

    def _intent_targets_run(self, run_id: str) -> bool:
        intent = self._turn_intent
        if not intent or not run_id:
            return False
        if intent.run_ids:
            return any(run_id.startswith(prefix) for prefix in intent.run_ids)
        return run_id == self._turn_run_id

    def _intent_authorizes(self, name: str, arguments: dict[str, Any]) -> bool:
        """Grant only a matching action/run, only while its user turn is active."""
        intent = self._turn_intent
        if intent is None or not self.allow_intent_actions:
            return False
        run_id = str(arguments.get("run_id") or "")
        if name == "authoring_start" and arguments.get("rebuild_only"):
            return intent.policy == "rebuild" and self._intent_targets_run(run_id)
        if name == "authoring_start":
            return (
                intent.policy == "create_now" and run_id in self._turn_planned_run_ids
            ) or (
                intent.policy == "start_existing" and self._intent_targets_run(run_id)
            )
        if name == "authoring_resume":
            return intent.policy == "resume" and self._intent_targets_run(run_id)
        # Review/rejection and cancellation retain their separate explicit gate.
        return False

    def _intent_mismatch(self, name: str, arguments: dict[str, Any]):
        """Do not turn a compile-only instruction into approval for generation."""
        intent = self._turn_intent
        if intent is None or intent.policy != "rebuild":
            return None
        if name in {"authoring_plan", "authoring_plan_variants", "authoring_resume"} or (
            name == "authoring_start" and not arguments.get("rebuild_only")
        ):
            return self._local_error(
                "generation_not_requested",
                "The user requested compilation, not generation. Check authoring_status. "
                "Active workers compile automatically on completion. For a pending run, "
                "ask whether to start it. For existing results use authoring_start with "
                "rebuild_only=true and preserve any requested problem_numbers.",
            )
        if name != "authoring_start":
            return None
        numbers = arguments.get("problem_numbers")
        if numbers is not None and not isinstance(numbers, list):
            return self._local_error("invalid_arguments", "problem_numbers must be an array of positive integers")
        if intent.selection_requested and not numbers:
            return self._local_error(
                "problem_selection_required",
                "The user requested a subset. Pass problem_numbers for the human "
                "problem_N.tex files; do not rebuild the whole collection. "
                f"Explicit requested numbers: {intent.problem_numbers}.",
            )
        if intent.problem_numbers is not None and tuple(numbers or ()) != intent.problem_numbers:
            return self._local_error(
                "problem_selection_mismatch",
                f"Use exactly problem_numbers={list(intent.problem_numbers)} as requested.",
            )
        if intent.after_completion and self._intent_targets_run(str(arguments.get("run_id") or "")):
            status = self.server.application.status(arguments["run_id"])
            payload = {"ok": True, "data": status.model_dump(mode="json")}
            self._update_pending_state("authoring_status", payload, arguments)
            state = self.latest_run_state
            if state is not None and not state.completion_ready:
                return self._local_error(
                    "automatic_compilation_pending",
                    "This run has not completed. Its worker assembles main.tex, main.pdf "
                    "and answer_key.tex automatically after generation. Do not rebuild or "
                    "start it for this request. If pending, ask whether to start generation.",
                )
        return None

    async def _invoke_mcp_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        approval_granted: bool = False,
    ) -> dict[str, Any]:
        self._turn_tool_calls += 1
        self._emit(ToolTraceEvent("input", name, arguments))

        try:
            mismatch = self._intent_mismatch(name, arguments)
        except Exception as exc:  # noqa: BLE001 - keep preflight failures in the tool contract
            mismatch = self._local_error("tool_execution_error", f"{type(exc).__name__}: {exc}")
        if mismatch is not None:
            self._emit(ToolTraceEvent("error", name, mismatch, True))
            return mismatch

        if (
            self._requires_approval(name, arguments)
            and not approval_granted
            and not self._intent_authorizes(name, arguments)
        ):
            decision = (
                self.approval_handler(name, dict(arguments))
                if self.approval_handler is not None
                else False
            )
            if self._turn_intent and self._turn_intent.policy == "confirmation_required":
                decision = None
            if decision is None:
                # Do not silently replace a proposal with another action in the
                # same model turn: yes must still mean the question displayed.
                if self._pending_tool_approval is None:
                    if not (
                        name == "authoring_start" and not arguments.get("rebuild_only")
                        and self.pending_run_id == arguments.get("run_id")
                    ):
                        # Only one question may become the meaning of "yes".
                        # An older plan must not resurface after this proposal.
                        self._pending_run_confirmation = None
                    self._pending_tool_approval = PendingToolApproval(
                        name=name,
                        arguments=dict(arguments),
                    )
                approval = self.pending_approval()
                payload = self._local_error(
                    "approval_required",
                    approval["question"],
                )
                payload["error"]["details"] = [approval]
                self._emit(ToolTraceEvent("error", name, payload, True))
                return payload
            if not decision:
                payload = self._local_error(
                    "user_declined",
                    f"local approval declined for {name}",
                )
                self._emit(ToolTraceEvent("error", name, payload, True))
                return payload

        try:
            result = await self.server.call_tool(name, arguments)
        except Exception as exc:  # noqa: BLE001 - normalize unexpected MCP failures
            payload = self._local_error(
                "tool_execution_error",
                f"{type(exc).__name__}: {exc}",
            )
            self._emit(ToolTraceEvent("error", name, payload, True))
            return payload

        payload = result.structuredContent
        if payload is None:
            text_parts = [
                block.text
                for block in result.content
                if getattr(block, "type", None) == "text"
            ]
            payload = {"ok": not result.isError, "content": "\n".join(text_parts)}
        phase: TracePhase = "error" if result.isError else "output"
        self._emit(ToolTraceEvent(phase, name, payload, bool(result.isError)))

        if not result.isError:
            self._update_pending_state(name, payload, arguments)

        if (
            self.mirror_worker_io
            and not result.isError
            and name in _WORKER_ACTIVITY_TOOLS
        ):
            run_id = self._extract_run_id(payload)
            if run_id:
                await self._drain_worker_io(run_id)
        return payload

    def _update_pending_state(
        self, name: str, payload: dict[str, Any], arguments: dict[str, Any],
    ) -> None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return
        latest = self._latest_state_from_data(data)
        if latest is not None:
            with self._state_lock:
                self._latest_run_state = latest
            if (
                self.pending_run_id == latest.run_id
                and (latest.status != "pending" or latest.worker_status in {"launching", "started"})
            ):
                self._pending_run_confirmation = None
        if name in {"authoring_plan", "authoring_plan_variants"}:
            self._pending_run_confirmation = None
            run_id = data.get("run_id")
            if (
                run_id and data.get("requires_confirmation")
                and data.get("status") == "pending"
            ):
                concurrency = data.get("concurrency")
                estimated = data.get("estimated_agent_calls")
                self._pending_run_confirmation = PendingRunConfirmation(
                    run_id=str(run_id),
                    concurrency=int(concurrency) if concurrency is not None else None,
                    estimated_agent_calls=(
                        int(estimated) if estimated is not None else None
                    ),
                )
                if self._turn_intent is not None:
                    self._turn_planned_run_ids.add(str(run_id))
            return
        if (
            name == "authoring_status" and latest is not None
            and latest.status == "pending" and latest.worker_status not in {"launching", "started"}
            and self._turn_intent is not None and self._turn_intent.after_completion
            and self._intent_targets_run(latest.run_id)
        ):
            self._pending_run_confirmation = PendingRunConfirmation(latest.run_id, None)
        if name in {"authoring_start", "authoring_resume"} and not arguments.get("rebuild_only"):
            run_id = data.get("run_id")
            pending = self._pending_run_confirmation
            if pending is not None and str(run_id or "") == pending.run_id:
                self._pending_run_confirmation = None
        pending_tool = self._pending_tool_approval
        if (
            pending_tool is not None and pending_tool.name == name
            and pending_tool.arguments.get("run_id") == arguments.get("run_id")
            and bool(pending_tool.arguments.get("rebuild_only")) == bool(arguments.get("rebuild_only"))
            and (
                name in {"authoring_start", "authoring_resume"}
                or pending_tool.arguments == arguments
            )
        ):
            self._pending_tool_approval = None

    def _latest_state_from_data(
        self,
        data: dict[str, Any],
    ) -> LatestRunState | None:
        nested_status = data.get("status")
        if not isinstance(nested_status, dict):
            nested_status = data.get("run_status")
        source = nested_status if isinstance(nested_status, dict) else data
        run_id = str(source.get("run_id") or data.get("run_id") or "")
        if not run_id:
            return None
        status_value = source.get("status")
        if not isinstance(status_value, str):
            return None

        with self._state_lock:
            current = self._latest_run_state
        fallback = current if current is not None and current.run_id == run_id else None
        stats = source.get("stats") if isinstance(source.get("stats"), dict) else {}
        worker = source.get("worker") if isinstance(source.get("worker"), dict) else {}

        def text_value(name: str) -> str:
            value = source.get(name, data.get(name))
            if value is not None:
                return str(value)
            return str(getattr(fallback, name, ""))

        def sequence_value(name: str) -> tuple[str, ...]:
            value = source.get(name, data.get(name))
            if isinstance(value, list | tuple):
                return tuple(str(item) for item in value)
            return tuple(getattr(fallback, name, ()))

        def count_value(name: str, plan_name: str | None = None) -> int:
            value = stats.get(name)
            if value is None and plan_name is not None:
                value = source.get(plan_name, data.get(plan_name))
            if value is not None:
                return int(value)
            fallback_name = plan_name if name == "total" and plan_name else name
            return int(getattr(fallback, fallback_name, 0))

        worker_status = worker.get("status")
        if worker_status is None and fallback is not None:
            worker_status = fallback.worker_status
        if worker_status == "failed":
            status_value = "worker_failed"
        elif status_value == "completed" and worker_status in {
            "launching",
            "started",
        }:
            status_value = "finalizing"

        manifest = source.get(
            "generated_manifest_path",
            data.get("generated_manifest_path"),
        )
        if manifest is None and fallback is not None:
            manifest = fallback.generated_manifest_path
        publication = source.get("publication", data.get("publication"))
        if not isinstance(publication, dict):
            publication = fallback.publication if fallback is not None else None
        current_stage = source.get("current_stage", data.get("current_stage"))
        if current_stage is None and fallback is not None:
            current_stage = fallback.current_stage
        stage_updated_at = source.get(
            "stage_updated_at",
            data.get("stage_updated_at"),
        )
        if stage_updated_at is None and fallback is not None:
            stage_updated_at = fallback.stage_updated_at
        active_stages_value = source.get(
            "active_stages",
            data.get("active_stages"),
        )
        if isinstance(active_stages_value, list | tuple):
            active_stages = tuple(
                dict(item) for item in active_stages_value if isinstance(item, dict)
            )
        else:
            active_stages = fallback.active_stages if fallback is not None else ()
        stage_counts_value = source.get("stage_counts", data.get("stage_counts"))
        if isinstance(stage_counts_value, dict):
            stage_counts = {
                str(stage): int(count)
                for stage, count in stage_counts_value.items()
            }
        else:
            stage_counts = (
                dict(fallback.stage_counts or {}) if fallback is not None else {}
            )
        progress_counts = source.get("progress_counts", data.get("progress_counts"))
        if not isinstance(progress_counts, dict):
            progress_counts = fallback.progress_counts if fallback is not None else {}
        latest_failure = source.get("latest_failure", data.get("latest_failure"))
        if "latest_failure" not in source and "latest_failure" not in data and fallback:
            latest_failure = fallback.latest_failure
        return LatestRunState(
            run_id=run_id,
            status=status_value,
            exam=text_value("exam"),
            subject=text_value("subject"),
            chapters=sequence_value("chapters"),
            topics=sequence_value("topics"),
            total_items=count_value("total", "total_items"),
            accepted=count_value("accepted"),
            needs_review=count_value("needs_review"),
            draft=count_value("draft"),
            failed=count_value("failed"),
            generated_output_dir=text_value("generated_output_dir"),
            generated_manifest_path=str(manifest) if manifest else None,
            worker_status=str(worker_status) if worker_status else None,
            current_stage=str(current_stage) if current_stage else None,
            stage_updated_at=str(stage_updated_at) if stage_updated_at else None,
            active_stages=active_stages,
            stage_counts=stage_counts,
            progress_counts=dict(progress_counts or {}),
            latest_failure=dict(latest_failure) if isinstance(latest_failure, dict) else None,
            publication=dict(publication) if publication is not None else None,
        )

    def _requires_approval(self, name: str, arguments: dict[str, Any]) -> bool:
        if name not in _APPROVAL_TOOLS:
            return False
        if name in {"authoring_start", "authoring_resume"}:
            return bool(arguments.get("confirmed"))
        return True

    async def _drain_worker_io(self, run_id: str) -> None:
        with self._worker_log_lock:
            offset = self._worker_offsets.get(run_id, 0)
            for _ in range(16):
                page = await asyncio.to_thread(
                    self.server.application.read_worker_log,
                    run_id,
                    offset=offset,
                    limit_bytes=262_144,
                )
                offset = page.next_offset
                self._worker_offsets[run_id] = offset
                if page.content:
                    self._emit(
                        ToolTraceEvent(
                            "worker_output",
                            "authoring_worker",
                            page.model_dump(mode="json"),
                        )
                    )
                if page.eof:
                    return
        self._emit(
            ToolTraceEvent(
                "worker_output",
                "authoring_worker",
                {
                    "run_id": run_id,
                    "next_offset": offset,
                    "notice": "more worker output remains; poll status or /logs again",
                },
            )
        )

    def _retire_continuation_profile(self, status_code: int | None) -> None:
        key_name = getattr(self.credentials, "key_name", None)
        if key_name:
            try:
                from vbagent.api_keys import KeyManager

                cooldown = 60.0 if status_code == 429 else 300.0
                KeyManager.get_instance().mark_profile_unavailable(key_name, cooldown)
            except Exception:  # noqa: BLE001 - failover accounting is best effort
                self._emit(
                    ToolTraceEvent(
                        "error",
                        "controller_profile_failover",
                        {"message": "could not persist provider cooldown"},
                        True,
                    )
                )
        self.previous_response_id = None
        self.credentials = None

    def _trim_history(self, max_characters: int = 200_000) -> None:
        total = sum(len(item["content"]) for item in self._history)
        while len(self._history) > 2 and total > max_characters:
            removed = self._history.pop(0)
            total -= len(removed["content"])

    def _emit(self, event: ToolTraceEvent) -> None:
        if self.trace_sink is None:
            return
        try:
            self.trace_sink(event)
        except Exception:  # noqa: BLE001 - rendering must not break tool execution
            return

    @staticmethod
    def _extract_run_id(payload: dict[str, Any]) -> str | None:
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        run_id = data.get("run_id")
        return str(run_id) if run_id else None

    @staticmethod
    def _local_error(code: str, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "error": {"code": code, "message": message, "details": []},
        }
