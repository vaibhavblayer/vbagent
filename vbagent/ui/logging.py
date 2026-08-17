"""Structured agent logging and compact terminal rendering."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import re
import threading
import traceback

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich import box

# Shared default console. CLI code should obtain it through get_agent_console().
console = Console()

# Lock to synchronize debug log output with spinners
_log_lock = threading.Lock()

# Thread-local task tag — set by parallel orchestrators so log output
# shows which pipeline task (Scan / TikZ / Options) an agent belongs to.
_task_tag = threading.local()
_logging_context = threading.local()
_event_lock = threading.Lock()

_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


@dataclass(frozen=True)
class AgentLoggingContext:
    """Console and visibility settings inherited by pipeline workers."""

    console: Console
    quiet: bool = False


def configure_agent_logging(*, output_console: Console | None = None, quiet: bool = False) -> None:
    """Configure agent rendering for the current thread."""
    _logging_context.value = AgentLoggingContext(
        console=output_console or console,
        quiet=quiet,
    )


@contextmanager
def agent_logging_context(*, output_console: Console | None = None, quiet: bool = False):
    """Temporarily configure logging without leaking state to later calls."""
    previous = capture_agent_logging_context()
    configure_agent_logging(output_console=output_console, quiet=quiet)
    try:
        yield capture_agent_logging_context()
    finally:
        apply_agent_logging_context(previous)


def capture_agent_logging_context() -> AgentLoggingContext:
    """Capture current settings so a child thread can inherit them."""
    return getattr(
        _logging_context,
        "value",
        AgentLoggingContext(console=console, quiet=False),
    )


def apply_agent_logging_context(context: AgentLoggingContext) -> None:
    """Apply a context captured by a parent thread."""
    _logging_context.value = context


def get_agent_console() -> Console:
    """Return the context console or the shared default console."""
    return capture_agent_logging_context().console


def _configured_level() -> str:
    try:
        from vbagent.config import get_config

        config = get_config()
        level = str(getattr(config, "log_level", "") or "").upper()
        if level in _LEVELS:
            return level
        return "DEBUG" if getattr(config, "debug", False) else "INFO"
    except Exception:
        return "INFO"


def _should_render(level: str) -> bool:
    context = capture_agent_logging_context()
    if context.quiet:
        return False
    return _LEVELS[level] >= _LEVELS[_configured_level()]


def set_task_tag(tag: str | None):
    """Set a task tag for the current thread's log output."""
    _task_tag.value = tag


def _get_tagged_name(agent_name: str) -> str:
    """Return 'Tag › AgentName' if a task tag is set, else just agent_name."""
    tag = getattr(_task_tag, "value", None)
    if tag:
        return f"{tag} › {agent_name}"
    return agent_name


def _event_log_path() -> Path | None:
    configured = os.environ.get("VBAGENT_LOG_FILE")
    if configured:
        if configured.strip().lower() in {"0", "off", "false", "none"}:
            return None
        return Path(configured).expanduser()
    if _configured_level() == "DEBUG":
        return Path(".vbagent/logs/agent-events.jsonl")
    return None


def record_agent_event(event: str, agent_name: str, **fields) -> None:
    """Append a metadata-only lifecycle event when event logging is enabled."""
    path = _event_log_path()
    if path is None:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "agent": agent_name,
    }
    tag = getattr(_task_tag, "value", None)
    if tag:
        payload["stage"] = tag
    payload.update(_sanitize_event_fields(fields))

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with _event_lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError:
        # Logging must never invalidate a completed model response.
        return


def _sanitize_event_fields(fields: dict) -> dict:
    sanitized = _sanitize_dict(fields)
    for key in ("error", "message"):
        if key in sanitized:
            sanitized[key] = _truncate(str(sanitized[key]), 1000)
    return sanitized

_MAX_TEXT_LEN = 600
_MAX_JSON_LEN = 1200
_BASE64_PATTERN = re.compile(
    r'(data:[a-zA-Z]+/[a-zA-Z]+;base64,)[A-Za-z0-9+/=]{40,}',
)
_RAW_BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/=]{200,}')


def log_agent_input(agent_name, input_data, model=None):
    """Render a structured JSON request preview."""
    record_agent_event("request_queued", agent_name, model=model)
    if not _should_render("INFO"):
        return

    display_name = _get_tagged_name(agent_name)
    title = f"[INPUT] {display_name}"
    if model:
        title += f" : {model}"
    
    body = _format_dict({
        "agent": display_name,
        "model": model,
        "input": _sanitize_dict(input_data),
    }, _MAX_JSON_LEN)
    with _log_lock:
        output = get_agent_console()
        output.print()
        output.print(Panel(
            body, title=title, title_align="left",
            border_style="#3b82f6", box=box.SIMPLE,
            padding=(1, 2),
        ))


def log_agent_output(agent_name, output_data, duration=None):
    """Render a structured JSON response preview."""
    if not _should_render("INFO"):
        return

    display_name = _get_tagged_name(agent_name)
    title = f"[OUTPUT] {display_name}"
    if duration is not None:
        title += f" : {duration:.2f}s"
    
    skip_truncation = any(
        keyword in agent_name.lower()
        for keyword in ("scanner", "solution", "problem")
    )
    if hasattr(output_data, "model_dump"):
        serialized_output = output_data.model_dump()
    else:
        serialized_output = output_data
    body = _format_dict({
        "agent": display_name,
        "duration": f"{duration:.2f}s" if duration is not None else None,
        "output": _sanitize_dict(serialized_output),
    }, 999999 if skip_truncation else _MAX_JSON_LEN)
    
    with _log_lock:
        output = get_agent_console()
        output.print()
        output.print(Panel(
            body, title=title, title_align="left",
            border_style="#22c55e", box=box.SIMPLE,
            padding=(1, 2),
        ))


def log_agent_started(agent_name, *, model="", queue_duration=0.0,
                      key_name=None, has_image=False, reasoning="none"):
    """Record the point at which a queued request receives an API slot."""
    record_agent_event(
        "request_started",
        agent_name,
        model=model,
        queue_duration=round(queue_duration, 4),
        key_name=key_name,
        has_image=has_image,
        reasoning=reasoning,
    )


def log_agent_error(agent_name, error, **metadata):
    """Record and render a failed or cancelled request."""
    attached = getattr(error, "_vbagent_metadata", {})
    details = {**attached, **metadata}
    display_name = _get_tagged_name(agent_name)
    err_type = type(error).__name__
    err_msg = str(error)
    event = "cancelled" if isinstance(error, TimeoutError) else "failed"
    record_agent_event(event, agent_name, error_type=err_type, error=err_msg, **details)

    if not _should_render("ERROR"):
        return

    if _configured_level() != "DEBUG":
        parts = [f"[red]ERROR {display_name}[/red]", f"{err_type}: {err_msg}"]
        duration = details.get("request_duration")
        if duration is not None:
            parts.append(f"{float(duration):.1f}s")
        model = details.get("model")
        if model:
            parts.append(str(model).replace("openai/", ""))
        with _log_lock:
            line = Text.from_markup(" [dim]·[/dim] ".join(parts))
            line.no_wrap = True
            line.overflow = "ellipsis"
            get_agent_console().print(line)
        return

    body = Text()
    body.append(err_type, style="#f87171")
    body.append(": ", style="#6b7280")
    body.append(_truncate(err_msg, 400), style="#e5e7eb")
    if error.__traceback__:
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        body.append("\n\n" + _truncate(trace, 2000), style="#6b7280")
    with _log_lock:
        output = get_agent_console()
        output.print()
        output.print(Panel(
            body, title=f"[ERROR] {display_name}",
            title_align="left", border_style="#ef4444",
            box=box.SIMPLE, padding=(1, 2),
        ))


def log_agent_usage(agent_name, *, model="", duration=0.0, usage=None,
                    response_id=None, has_image=False, reasoning="none",
                    queue_duration=0.0, request_duration=None, key_name=None,
                    cache_group_id=None):
    """Record completion and render structured JSON usage metadata."""

    short_model = model.replace("openai/", "") if model else "?"

    data: dict = {
        "input": 0,
        "output": 0,
        "cached": 0,
        "cache_write": 0,
        "cache_hit_percent": 0.0,
        "cache_write_percent": 0.0,
        "reasoning": 0,
        "requests": 0,
    }

    if usage is not None:
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cached = 0
        cache_write = 0
        reasoning_tok = 0
        inp_details = getattr(usage, "input_tokens_details", None)
        if inp_details:
            cached = getattr(inp_details, "cached_tokens", 0) or 0
            cache_write = getattr(inp_details, "cache_write_tokens", 0) or 0
        out_details = getattr(usage, "output_tokens_details", None)
        if out_details:
            reasoning_tok = getattr(out_details, "reasoning_tokens", 0) or 0

        data.update({
            "input": inp,
            "output": out,
            "cached": cached,
            "cache_write": cache_write,
            "cache_hit_percent": round((cached / inp) * 100, 1) if inp else 0.0,
            "cache_write_percent": round((cache_write / inp) * 100, 1) if inp else 0.0,
            "reasoning": reasoning_tok,
            "requests": getattr(usage, "requests", 0) or 0,
        })

    actual_request_duration = duration if request_duration is None else request_duration
    record_agent_event(
        "completed",
        agent_name,
        model=short_model,
        duration=round(duration, 4),
        request_duration=round(actual_request_duration, 4),
        queue_duration=round(queue_duration, 4),
        key_name=key_name,
        cache_group_id=cache_group_id,
        response_id=response_id,
        has_image=has_image,
        reasoning_effort=reasoning,
        tokens=data,
    )

    if not _should_render("INFO"):
        return

    usage_payload = {
        "agent": _get_tagged_name(agent_name),
        "status": "completed",
        "duration": f"{duration:.1f}s",
        "request_duration": f"{actual_request_duration:.1f}s",
        "queue_duration": f"{queue_duration:.1f}s",
        "model": short_model,
        "reasoning": reasoning,
        "image": has_image,
        "tokens": data,
        "key_name": key_name,
        "cache_group": cache_group_id,
        "response_id": response_id,
    }
    with _log_lock:
        output = get_agent_console()
        output.print()
        output.print(Panel(
            _format_dict(usage_payload, _MAX_JSON_LEN),
            title=f"[USAGE] {_get_tagged_name(agent_name)}",
            title_align="left",
            border_style="#a78bfa",
            box=box.SIMPLE,
            padding=(1, 2),
        ))


def _compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _format_input(data):
    if isinstance(data, list):
        return _format_message_list(data)
    if isinstance(data, dict):
        return _format_dict(data, _MAX_JSON_LEN)
    if isinstance(data, str):
        return _truncate_rich(_sanitize_base64(data), _MAX_TEXT_LEN)
    return _truncate_rich(str(data), _MAX_TEXT_LEN)


def _format_output(data, skip_truncation=False):
    if hasattr(data, "model_fields"):
        return _format_pydantic(data)
    if isinstance(data, dict):
        return _format_dict(data, _MAX_JSON_LEN if not skip_truncation else 999999)
    if isinstance(data, str):
        sanitized = _sanitize_base64(data)
        if _looks_like_json(sanitized):
            return _format_json_str(sanitized, _MAX_JSON_LEN if not skip_truncation else 999999)
        if _looks_like_latex(sanitized):
            max_len = 999999 if skip_truncation else _MAX_TEXT_LEN
            return Syntax(_truncate(sanitized, max_len),
                          "latex", theme="monokai", word_wrap=True)
        return _truncate_rich(sanitized, 999999 if skip_truncation else _MAX_TEXT_LEN)
    return _truncate_rich(str(data), 999999 if skip_truncation else _MAX_TEXT_LEN)


def _format_message_list(messages):
    text = Text()
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        text.append(f"[{role}]", style="bold #a78bfa")
        content = msg.get("content", "")
        if isinstance(content, str):
            text.append(" " + _truncate(_sanitize_base64(content), 200))
        elif isinstance(content, list):
            for part in content:
                ptype = part.get("type", "")
                if ptype in ("input_image", "image_url", "image"):
                    url = part.get("image_url", part.get("url", ""))
                    meta = _extract_image_meta(url)
                    text.append("\n  \U0001f4f7 ", style="#60a5fa")
                    text.append(meta, style="#6b7280")
                elif ptype in ("input_text", "text"):
                    t = part.get("text", "")
                    text.append("\n  " + _truncate(t, 200))
        if i < len(messages) - 1:
            text.append("\n")
    return text


def _format_pydantic(model):
    """Format Pydantic model for display.
    
    For models with LaTeX content, show structure with LaTeX truncated.
    """
    model_name = type(model).__name__
    
    # For PrimaryClassification and ClassificationResult, only show core 3 fields
    if model_name in ("PrimaryClassification", "ClassificationResult"):
        data = {
            "subject": model.subject,
            "question_type": model.question_type,
            "has_diagram": model.has_diagram,
        }
        return _format_dict(data, _MAX_JSON_LEN)
    
    # For SolutionOutput, show structure with LaTeX truncated
    if model_name == "SolutionOutput":
        data = model.model_dump()
        # Truncate solution_latex in the JSON view
        if "solution_latex" in data and isinstance(data["solution_latex"], str):
            latex = data["solution_latex"]
            if len(latex) > 100:
                data["solution_latex"] = latex[:100] + f"... ({len(latex)} chars)"
        return _format_dict(data, _MAX_JSON_LEN)
    
    # For other models, show all fields
    data = model.model_dump()
    return _format_dict(data, _MAX_JSON_LEN)


def _format_dict(data, max_len):
    sanitized = _sanitize_dict(data)
    try:
        raw = json.dumps(sanitized, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        raw = str(sanitized)
    return Syntax(_truncate(raw, max_len), "json", theme="monokai", word_wrap=True)


def _format_json_str(s, max_len):
    try:
        parsed = json.loads(s)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        return Syntax(_truncate(pretty, max_len), "json",
                      theme="monokai", word_wrap=True)
    except (json.JSONDecodeError, TypeError):
        return _truncate_rich(s, max_len)


def _format_cell_value(value):
    if value is None:
        return "[#6b7280]\u2013[/]"
    if isinstance(value, bool):
        return "[#4ade80]true[/]" if value else "[#f87171]false[/]"
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, str):
        return _truncate(_sanitize_base64(value), 120)
    if isinstance(value, (list, tuple)):
        if not value:
            return "[#6b7280]\u2013[/]"
        items = [str(v) for v in value[:6]]
        suffix = "\u2026" if len(value) > 6 else ""
        return ", ".join(items) + suffix
    if isinstance(value, dict):
        return _truncate(json.dumps(value, default=str), 120)
    return str(value)


def _sanitize_base64(text):
    if not isinstance(text, str):
        return str(text)

    def _replace_data_uri(m):
        prefix = m.group(1)
        full = m.group(0)
        raw_b64 = full[len(prefix):]
        mime = prefix.replace("data:", "").replace(";base64,", "")
        size_bytes = len(raw_b64) * 3 / 4
        kb = size_bytes / 1024
        return f"[{mime} base64 ~{kb:.1f} KB]"

    result = _BASE64_PATTERN.sub(_replace_data_uri, text)

    def _replace_raw(m):
        raw = m.group(0)
        size_bytes = len(raw) * 3 / 4
        kb = size_bytes / 1024
        return f"[base64 data ~{kb:.1f} KB]"

    result = _RAW_BASE64_PATTERN.sub(_replace_raw, result)
    return result


def _sanitize_dict(data):
    if isinstance(data, dict):
        return {k: _sanitize_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_dict(v) for v in data]
    if isinstance(data, str):
        return _sanitize_base64(data)
    return data


def _extract_image_meta(url):
    if not isinstance(url, str):
        return "image"
    m = re.match(r'data:([a-zA-Z]+/[a-zA-Z]+);base64,(.+)', url, re.DOTALL)
    if m:
        mime = m.group(1)
        raw = m.group(2)
        size_bytes = len(raw) * 3 / 4
        kb = size_bytes / 1024
        return f"{mime} base64 ~{kb:.1f} KB"
    if len(url) > 200:
        return f"image URL ({len(url)} chars)"
    return url


def _truncate(text, max_len):
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\u2026 ({len(text)} chars total)"


def _truncate_rich(text, max_len):
    if not isinstance(text, str):
        text = str(text)
    t = Text()
    if len(text) <= max_len:
        t.append(text, style="#e5e7eb")
    else:
        t.append(text[:max_len], style="#e5e7eb")
        t.append(f"\u2026 ({len(text)} chars total)", style="#6b7280")
    return t


def _looks_like_json(text):
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    return ((stripped.startswith("{") and stripped.endswith("}"))
            or (stripped.startswith("[") and stripped.endswith("]")))


def _looks_like_latex(text):
    if not isinstance(text, str):
        return False
    indicators = ["\\begin{", "\\end{", "\\frac", "\\item",
                   "\\textbf", "\\section"]
    return any(ind in text for ind in indicators)
