"""Clean, transparent natural-language CLI for MCP-backed authoring."""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import InMemoryHistory
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from vbagent.mcp.chat_intent import (
    DEFAULT_CHAT_REASONING_EFFORT,
    AuthoringIntentPolicy,
    authoring_intent_policy,
    is_confirmation_message,
    is_decline_message,
)
from vbagent.ui.agent_io import (
    WorkerLogDecoder,
    print_structured_json,
    render_agent_io,
)

console = Console()


class ChatPrompt:
    """Interactive input with private, session-local message history."""

    def __init__(
        self,
        *,
        input=None,
        output=None,
        force_terminal: bool | None = None,
    ) -> None:
        is_terminal = (
            force_terminal
            if force_terminal is not None
            else sys.stdin.isatty() and sys.stdout.isatty()
        )
        self._session = (
            PromptSession(
                history=InMemoryHistory(),
                input=input,
                output=output,
            )
            if is_terminal
            else None
        )
        self._notification_futures: set[Any] = set()

    @property
    def is_terminal(self) -> bool:
        return self._session is not None

    def ask(self, status_provider: Callable[[], str | None] | None = None) -> str:
        """Read one message; Up selects older history and Down selects newer."""
        if self._session is not None:
            def toolbar():
                label = status_provider() if status_provider is not None else None
                if not label:
                    return FormattedText([])
                return FormattedText(
                    [
                        ("bold bg:#4c1d95 #ffffff", " Latest generation "),
                        ("", f" {label} "),
                    ]
                )

            return self._session.prompt(
                FormattedText(
                    [
                        ("bold ansicyan", "\nYou:"),
                        ("", " "),
                    ]
                ),
                bottom_toolbar=toolbar,
                refresh_interval=1.0,
            )
        return Prompt.ask("\n[bold cyan]You[/bold cyan]", console=console)

    def invalidate(self) -> None:
        """Redraw a live prompt after a background status change."""
        if self._session is not None:
            self._session.app.invalidate()

    def notify(self, callback: Callable[[], None]) -> None:
        """Print above a live prompt without corrupting the current draft."""
        if self._session is None:
            callback()
            return
        app = self._session.app
        if not app.is_running or app.loop is None:
            callback()
            return

        def schedule() -> None:
            from prompt_toolkit.application import run_in_terminal

            future = run_in_terminal(callback)
            self._notification_futures.add(future)
            future.add_done_callback(self._notification_futures.discard)

        app.loop.call_soon_threadsafe(schedule)


class RichChatRenderer:
    """Render complete controller-tool traces and compact model telemetry."""

    def __init__(
        self,
        output_console: Console,
        *,
        enabled: bool = True,
        detailed_usage: bool = False,
    ) -> None:
        self.console = output_console
        self.enabled = enabled
        self.detailed_usage = detailed_usage
        self._worker_decoders: dict[str, WorkerLogDecoder] = {}
        self._worker_render_lock = threading.RLock()

    def tool_event(self, event) -> None:
        if not self.enabled:
            return
        if event.phase == "worker_output":
            self.worker_output(event.payload)
            return
        if (
            event.phase == "output"
            and event.tool_name == "authoring_read_worker_log"
            and event.payload.get("ok")
        ):
            self.worker_output(event.payload.get("data") or {})
            return

        labels = {
            "input": ("TOOL INPUT", "#3b82f6"),
            "output": ("TOOL OUTPUT", "#22c55e"),
            "error": ("TOOL ERROR", "#ef4444"),
        }
        label, color = labels[event.phase]
        self.json_event(
            event.payload,
            title=f"[{label}] {event.tool_name}",
            border_style=color,
        )

    def json_event(
        self,
        payload: Any,
        *,
        title: str,
        border_style: str = "#22c55e",
    ) -> None:
        print_structured_json(
            self.console, payload, title=title, color=border_style
        )

    def worker_output(self, payload: dict[str, Any], *, final: bool = False) -> None:
        """Decode worker events before rendering; never JSON-encode a Rich panel."""
        run_id = str(payload.get("run_id") or "")
        with self._worker_render_lock:
            decoder = self._worker_decoders.setdefault(run_id, WorkerLogDecoder())
            for event in decoder.feed(str(payload.get("content") or ""), final=final):
                render_agent_io(
                    self.console,
                    {**event, "run_id": run_id},
                    detailed_usage=self.detailed_usage,
                )
            if payload.get("notice"):
                self.json_event(
                    {"event": "worker_notice", "run_id": run_id, "message": payload["notice"]},
                    title="VBAgent:",
                )

    def _finish_worker_output(self, run_id: str) -> None:
        with self._worker_render_lock:
            if run_id in self._worker_decoders:
                self.worker_output({"run_id": run_id}, final=True)
                self._worker_decoders.pop(run_id, None)

    def agent_event(self, event: dict[str, Any]) -> None:
        if not self.enabled or event.get("event") != "completed":
            return
        tokens = event.get("tokens") or {}
        if not self.detailed_usage:
            model = str(event.get("model", "?")).removeprefix("gpt-5.6-")
            self.console.print(
                "[dim]VBAgent usage: "
                f"{model} · {_compact_count(tokens.get('input', 0))} in · "
                f"{_compact_count(tokens.get('output', 0))} out · "
                f"{tokens.get('cache_hit_percent', 0.0):.1f}% cache[/dim]"
            )
            return
        request_hit = tokens.get("cache_request_hit_percent")
        request_hit_text = (
            f"{float(request_hit):.1f}%" if request_hit is not None else "n/a"
        )
        parts = [
            f"model={event.get('model', '?')}",
            f"input={tokens.get('input', 0)}",
            f"output={tokens.get('output', 0)}",
            f"cached={tokens.get('cached', 0)}",
            f"cache-hit={tokens.get('cache_hit_percent', 0.0):.1f}%",
            f"request-hit={request_hit_text}",
        ]
        if event.get("key_name"):
            parts.append(f"profile={event['key_name']}")
        if event.get("cache_domain"):
            parts.append(f"domain={event['cache_domain']}")
        self.console.print("[dim]VBAgent usage: " + " · ".join(parts) + "[/dim]")

    def controller_input(self, message: str) -> None:
        if self.enabled:
            self.json_event(
                {"role": "user", "content": message},
                title="You:",
                border_style="#3b82f6",
            )

    def controller_output(self, message: str) -> None:
        self.json_event(
            {"role": "assistant", "content": message or ""},
            title="VBAgent:",
        )

    def run_completion(self, payload: dict[str, Any]) -> None:
        """Render machine-readable completion metadata and complete LaTeX."""
        self._finish_worker_output(str((payload.get("run") or {}).get("run_id") or ""))
        artifacts = payload.get("artifacts") or []
        metadata = {
            **payload,
            "artifacts": [
                {key: value for key, value in artifact.items() if key != "content"}
                for artifact in artifacts
            ],
        }
        if payload.get("artifacts_truncated"):
            run_id = str((payload.get("run") or {}).get("run_id") or "")
            metadata["next_action"] = (
                f"Use /results {run_id} to display every accepted artifact in full."
            )
        self.json_event(metadata, title="VBAgent:")
        for artifact in artifacts:
            self.generated_artifact(artifact)

    def generated_artifact(self, artifact: dict[str, Any]) -> None:
        self.console.print(
            Panel(
                Syntax(
                    str(artifact.get("content") or ""),
                    "latex",
                    theme="monokai",
                    word_wrap=True,
                ),
                title=(
                    f"[GENERATED CODE] #{artifact.get('number') or artifact.get('ordinal', '?')} "
                    f"· {artifact.get('status', 'accepted')} · "
                    f"{artifact.get('path', '')}"
                ),
                title_align="left",
                border_style="#f59e0b",
                box=box.SIMPLE,
                padding=(1, 2),
            )
        )


def _make_session(**kwargs):
    from vbagent.mcp.chat import AuthoringChatSession

    return AuthoringChatSession(**kwargs)


def _compact_count(value: Any) -> str:
    count = int(value or 0)
    if count < 1_000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1_000:.1f}k"
    return f"{count / 1_000_000:.1f}m"


def _render_tools(session) -> None:
    table = Table(title="Discovered authoring tools", box=box.SIMPLE)
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Purpose")
    for name, description in session.tool_descriptions():
        table.add_row(name, description)
    console.print(table)


def _render_help() -> None:
    console.print(
        "Commands: [cyan]/tools[/cyan], [cyan]/status [RUN_ID][/cyan], "
        "[cyan]/logs RUN_ID[/cyan], [cyan]/confirm[/cyan], "
        "[cyan]/results [RUN_ID][/cyan], "
        "[cyan]/approve[/cyan], [cyan]/decline[/cyan], [cyan]/clear[/cyan], "
        "[cyan]/help[/cyan], [cyan]/exit[/cyan].\n"
        "An explicit create/generate request starts after its plan is shown. "
        "Direct start or compile requests also act without a second approval. "
        "When asked a question, reply [cyan]yes[/cyan] or [cyan]no[/cyan].\n"
        "Everything else is sent to the VBAgent chat model.\n"
        "Use [cyan]↑[/cyan] for older submitted messages and [cyan]↓[/cyan] "
        "for newer messages or a blank draft. History stays in this process only."
    )


def _authoring_intent_policy(message: str) -> AuthoringIntentPolicy:
    """Compatibility wrapper; the session owns the actual authorization."""
    return authoring_intent_policy(message)


def _render_command_result(
    payload: dict[str, Any],
    renderer: RichChatRenderer,
) -> dict[str, Any] | None:
    if not payload.get("ok"):
        renderer.json_event(payload, title="VBAgent:", border_style="#ef4444")
        return None
    data = payload.get("data") or {}
    run_id = str(data.get("run_id") or "")
    worker = data.get("worker") or {}
    dispatched = bool(data.get("dispatched"))
    if data.get("action") == "rebuild":
        publication = (data.get("status") or {}).get("publication") or {}
        renderer.json_event(
            {
                "event": "document_rebuilt" if publication.get("compile_success") else "document_build_failed",
                "run_id": run_id, "action": "rebuild", "generation_started": False,
                "publication": publication,
            },
            title="VBAgent:",
            border_style="#a78bfa" if publication.get("compile_success") else "#ef4444",
        )
        return data
    if data.get("action") in {"start", "resume"}:
        renderer.json_event(
            {
                "event": "background_generation_started",
                "run_id": run_id,
                "state": "dispatched" if dispatched else "already_active",
                "pid": worker.get("pid"),
                "message": (
                    "Generation continues in the background; the latest-run "
                    "toolbar will update automatically."
                ),
                "commands": {
                    "status": f"/status {run_id}",
                    "logs": f"/logs {run_id}",
                },
            },
            title="VBAgent:",
        )
        return data
    message = data.get("message")
    renderer.json_event(
        {
            "event": "command_completed",
            "run_id": run_id or None,
            "action": data.get("action"),
            "message": message,
        },
        title="VBAgent:",
    )
    return data


@click.command()
@click.option(
    "--output",
    default="agentic/authoring",
    show_default=True,
    type=click.Path(file_okay=False),
    help="Controlled workspace shared with vbagent author and vbagent mcp.",
)
@click.option(
    "--model",
    default=None,
    help="VBAgent chat model override (the default is normally GPT-5.6 Luna).",
)
@click.option(
    "--reasoning-effort",
    type=click.Choice(["none", "low", "medium", "high", "xhigh", "max"]),
    default=DEFAULT_CHAT_REASONING_EFFORT,
    show_default=True,
    help="Reasoning effort for the chat controller only; authoring agents are unchanged.",
)
@click.option("--message", "message", "-m", help="Run one non-interactive turn.")
@click.option(
    "--yes",
    "auto_approve",
    is_flag=True,
    help="Approve consequential start, rebuild, resume, cancel, and review tool calls.",
)
@click.option("--trace/--no-trace", default=True, show_default=True)
@click.option(
    "--worker-io/--no-worker-io",
    default=True,
    show_default=True,
    help="Mirror new detached-agent input/output whenever run status is checked.",
)
@click.option("--timeout", type=click.FloatRange(min=1.0), default=None)
@click.option("--verbose", "-v", is_flag=True, help="Show provider and protocol logs.")
def chat(
    output: str,
    model: str | None,
    reasoning_effort: str | None,
    message: str | None,
    auto_approve: bool,
    trace: bool,
    worker_io: bool,
    timeout: float | None,
    verbose: bool,
) -> None:
    """Talk naturally to the durable authoring workflow with complete tool traces."""
    dependency_level = logging.INFO if verbose else logging.WARNING
    for logger_name in ("agents", "httpx", "mcp", "openai"):
        logging.getLogger(logger_name).setLevel(dependency_level)
    renderer = RichChatRenderer(
        console,
        enabled=trace,
        detailed_usage=verbose,
    )
    workspace = Path(output).expanduser().resolve()
    display_model = model or "configured default (loaded on first message)"
    display_reasoning = reasoning_effort or DEFAULT_CHAT_REASONING_EFFORT

    console.print(
        Panel(
            "Natural language → deferred MCP tools → durable authoring ledger\n"
            f"VBAgent: [cyan]{display_model}[/cyan] · "
            f"[cyan]{display_reasoning}[/cyan] reasoning\n"
            f"Workspace: [cyan]{workspace}[/cyan]\n"
            "The chat agent and tool schemas load only when first needed; "
            "generation is detached after explicit creation intent or confirmation.",
            title="VBAgent Authoring Chat",
            border_style="#a78bfa",
            box=box.SIMPLE,
        )
    )

    def approve(_tool_name: str, _arguments: dict[str, Any]) -> bool | None:
        if auto_approve:
            return True
        if message is not None:
            return False
        # Never block for terminal input from inside an asynchronous model tool
        # callback. The call is staged and the outer shell accepts /approve.
        return None

    session = None
    chat_prompt: ChatPrompt | None = None
    monitor_stop = threading.Event()
    monitor_threads: dict[str, threading.Thread] = {}
    monitor_lock = threading.RLock()

    def get_session():
        nonlocal session
        if session is not None:
            return session
        try:
            with console.status(
                "[cyan]Loading the VBAgent chat agent…[/cyan]",
                spinner="dots",
            ):
                session = _make_session(
                    output_root=output,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    trace_sink=renderer.tool_event if trace else None,
                    approval_handler=approve,
                    timeout=timeout,
                    mirror_worker_io=worker_io,
                    allow_intent_actions=message is None or auto_approve,
                )
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc
        return session

    def render_exception(exc: BaseException, *, event: str = "error") -> None:
        renderer.json_event(
            {
                "event": event,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            },
            title="VBAgent:",
            border_style="#ef4444",
        )

    def announce_background_approval(active_session) -> None:
        payload = active_session.pending_approval()
        if payload is None:
            return
        renderer.json_event(payload, title="VBAgent:", border_style="#f59e0b")

    def render_terminal_completion(active_session, run_id: str) -> None:
        payload = active_session.take_completion(run_id)
        if payload is not None:
            renderer.run_completion(payload)

    def start_monitor(active_session, run_id: str) -> None:
        if chat_prompt is None or not hasattr(active_session, "wait_for_run_completion"):
            return
        with monitor_lock:
            existing = monitor_threads.get(run_id)
            if existing is not None and existing.is_alive():
                return

            def monitor() -> None:
                try:
                    def show_worker_io(payload: dict[str, Any]) -> None:
                        chat_prompt.notify(
                            lambda data=payload: renderer.worker_output(data)
                        )

                    payload = active_session.wait_for_run_completion(
                        run_id,
                        monitor_stop,
                        worker_io_callback=(
                            show_worker_io if trace and worker_io else None
                        ),
                    )
                    if payload is not None and not monitor_stop.is_set():
                        chat_prompt.notify(lambda: renderer.run_completion(payload))
                except Exception as exc:  # noqa: BLE001 - surface monitor failure
                    if not monitor_stop.is_set():
                        chat_prompt.notify(
                            lambda error=exc: render_exception(
                                error,
                                event="background_monitor_failed",
                            )
                        )
                finally:
                    with monitor_lock:
                        monitor_threads.pop(run_id, None)
                    chat_prompt.invalidate()

            thread = threading.Thread(
                target=monitor,
                name=f"vbagent-chat-monitor-{run_id[:8]}",
                daemon=True,
            )
            monitor_threads[run_id] = thread
            thread.start()

    def handle_command_result(active_session, payload: dict[str, Any]) -> None:
        data = _render_command_result(payload, renderer)
        if data is None:
            return
        run_id = str(data.get("run_id") or "")
        if not run_id:
            return
        action = data.get("action")
        nested_status = data.get("status") if isinstance(data.get("status"), dict) else {}
        status = str(nested_status.get("status") or "")
        if status in {"completed", "cancelled"}:
            render_terminal_completion(active_session, run_id)
        elif action in {"start", "resume"}:
            start_monitor(active_session, run_id)

    def send_one(user_message: str) -> None:
        active_session = get_session()
        if not active_session.controller_ready:
            with console.status(
                "[cyan]Discovering deferred MCP tool namespaces…[/cyan]",
                spinner="dots",
            ):
                active_session.prepare_controller()
        renderer.controller_input(user_message)
        try:
            from vbagent.ui.logging import agent_logging_context

            with agent_logging_context(
                output_console=console,
                quiet=True,
                event_sink=renderer.agent_event if trace else None,
            ):
                response = active_session.send(user_message, show_spinner=True)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc
        renderer.controller_output(response)
        pending_run_id = getattr(active_session, "pending_run_id", None)
        if pending_run_id and pending_run_id == active_session.authorized_pending_run_id:
            renderer.json_event(
                {
                    "event": "background_start_authorized",
                    "run_id": pending_run_id,
                    "authorization_source": "explicit_creation_intent",
                    "confirmation_required": False,
                    "message": (
                        "Your explicit generation request authorizes this run; "
                        "starting it in the background."
                    ),
                },
                title="VBAgent:",
            )
            try:
                handle_command_result(
                    active_session,
                    active_session.confirm_pending_run(),
                )
            except Exception as exc:  # noqa: BLE001 - preserve the chat session
                render_exception(exc, event="background_start_failed")
        else:
            announce_background_approval(active_session)
        state = getattr(active_session, "latest_run_state", None)
        if state is not None and getattr(state, "completion_ready", False):
            render_terminal_completion(active_session, state.run_id)
        elif state is not None and state.worker_status in {"launching", "started"}:
            start_monitor(active_session, state.run_id)

    if message is not None:
        send_one(message)
        return

    _render_help()
    chat_prompt = ChatPrompt()
    try:
        while True:
            try:
                user_message = chat_prompt.ask(
                    lambda: (
                        getattr(session, "latest_run_label", None)
                        if session is not None
                        else None
                    )
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Chat closed.[/dim]")
                return
            if not user_message:
                continue

            command, _, remainder = user_message.partition(" ")
            command = command.lower()
            if command in {"/exit", "/quit", "exit", "quit"}:
                console.print("[dim]Chat closed.[/dim]")
                return
            if command == "/help":
                _render_help()
                continue
            if command == "/tools":
                _render_tools(get_session())
                continue
            if command == "/clear":
                if session is not None:
                    session.clear()
                renderer.json_event(
                    {
                        "event": "conversation_cleared",
                        "message": "Durable runs and the latest-run indicator are unchanged.",
                    },
                    title="VBAgent:",
                )
                continue
            if command == "/confirm" and remainder.strip():
                try:
                    active_session = get_session()
                    handle_command_result(
                        active_session,
                        active_session.confirm_run(remainder.strip()),
                    )
                except Exception as exc:  # noqa: BLE001 - keep the shell available
                    render_exception(exc)
                continue
            if command in {"/confirm", "/approve"} or (
                session is not None
                and session.pending_approval() is not None
                and is_confirmation_message(user_message)
            ):
                if session is None or session.pending_approval() is None:
                    renderer.json_event(
                        {
                            "event": "nothing_to_confirm",
                            "message": "There is no action waiting for confirmation.",
                        },
                        title="VBAgent:",
                        border_style="#f59e0b",
                    )
                    continue
                try:
                    handle_command_result(session, session.approve_pending_action())
                except Exception as exc:  # noqa: BLE001 - keep the shell available
                    render_exception(exc)
                continue
            if command == "/decline" or (
                session is not None and session.pending_approval() is not None
                and is_decline_message(user_message)
            ):
                if session is None or session.pending_approval() is None:
                    renderer.json_event(
                        {
                            "event": "nothing_to_decline",
                            "message": "There is no action waiting for approval.",
                        },
                        title="VBAgent:",
                        border_style="#f59e0b",
                    )
                    continue
                declined = session.decline_pending_action()
                renderer.json_event(
                    {
                        "event": "approval_declined",
                        **declined,
                        "message": "No action was taken.",
                    },
                    title="VBAgent:",
                    border_style="#f59e0b",
                )
                continue
            if command in {"/status", "/logs"}:
                active_session = get_session()
                run_id = remainder.strip() or active_session.pending_run_id
                if not run_id and getattr(active_session, "latest_run_state", None):
                    run_id = active_session.latest_run_state.run_id
                if not run_id:
                    renderer.json_event(
                        {
                            "event": "missing_run_id",
                            "message": f"Usage: {command} RUN_ID",
                        },
                        title="VBAgent:",
                        border_style="#f59e0b",
                    )
                    continue
                try:
                    if command == "/status":
                        payload = active_session.call_tool(
                            "authoring_status",
                            {"run_id": run_id},
                        )
                        if not trace:
                            renderer.json_event(payload, title="VBAgent:")
                        state = active_session.latest_run_state
                        if state is not None and getattr(
                            state,
                            "completion_ready",
                            False,
                        ):
                            render_terminal_completion(active_session, run_id)
                        elif state is not None and state.worker_status in {
                            "launching",
                            "started",
                        }:
                            start_monitor(active_session, run_id)
                    else:
                        payload = active_session.read_new_worker_io(run_id)
                        if not trace:
                            if payload.get("ok"):
                                renderer.worker_output(payload.get("data") or {})
                            else:
                                renderer.json_event(payload, title="VBAgent:")
                except Exception as exc:  # noqa: BLE001 - keep the shell alive
                    render_exception(exc)
                continue
            if command == "/results":
                active_session = get_session()
                run_id = remainder.strip()
                if not run_id and getattr(active_session, "latest_run_state", None):
                    run_id = active_session.latest_run_state.run_id
                if not run_id:
                    renderer.json_event(
                        {
                            "event": "missing_run_id",
                            "message": "Usage: /results RUN_ID",
                        },
                        title="VBAgent:",
                        border_style="#f59e0b",
                    )
                    continue
                try:
                    state = active_session.refresh_run_state(run_id)
                    renderer.json_event(
                        {
                            "event": "generated_results",
                            "run": state.as_dict(),
                            "saved_to": state.generated_output_dir,
                            "message": "Displaying every accepted artifact in full.",
                        },
                        title="VBAgent:",
                    )
                    shown = 0
                    for artifact in active_session.iter_authored_artifacts(run_id):
                        renderer.generated_artifact(artifact)
                        shown += 1
                    if shown == 0:
                        renderer.json_event(
                            {
                                "event": "no_accepted_artifacts",
                                "run_id": run_id,
                                "status": state.status,
                            },
                            title="VBAgent:",
                            border_style="#f59e0b",
                        )
                except Exception as exc:  # noqa: BLE001 - keep the shell alive
                    render_exception(exc)
                continue
            if command.startswith("/"):
                renderer.json_event(
                    {
                        "event": "unknown_command",
                        "message": "Unknown command. Use /help.",
                    },
                    title="VBAgent:",
                    border_style="#f59e0b",
                )
                continue
            try:
                send_one(user_message)
            except KeyboardInterrupt:
                console.print("\n[yellow]Current request cancelled. Chat closed.[/yellow]")
                return
    finally:
        monitor_stop.set()
        with monitor_lock:
            threads = list(monitor_threads.values())
        for thread in threads:
            thread.join(timeout=1.0)


if __name__ == "__main__":
    chat()
