"""Structured logging for agent I/O."""

from typing import Any
import json
import re
import threading

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.table import Table
from rich import box

# Shared console instance — import this from other modules to avoid overlap
console = Console()

# Lock to synchronize debug log output with spinners
_log_lock = threading.Lock()

# Thread-local task tag — set by parallel orchestrators so log output
# shows which pipeline task (Scan / TikZ / Options) an agent belongs to.
_task_tag = threading.local()


def set_task_tag(tag: str | None):
    """Set a task tag for the current thread's log output."""
    _task_tag.value = tag


def _get_tagged_name(agent_name: str) -> str:
    """Return 'Tag › AgentName' if a task tag is set, else just agent_name."""
    tag = getattr(_task_tag, "value", None)
    if tag:
        return f"{tag} › {agent_name}"
    return agent_name

_MAX_TEXT_LEN = 600
_MAX_JSON_LEN = 1200
_BASE64_PATTERN = re.compile(
    r'(data:[a-zA-Z]+/[a-zA-Z]+;base64,)[A-Za-z0-9+/=]{40,}',
)
_RAW_BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/=]{200,}')


def log_agent_input(agent_name, input_data, model=None):
    """Log agent input."""
    display_name = _get_tagged_name(agent_name)
    title = f"[INPUT] {display_name}"
    if model:
        title += f" : {model}"
    
    # Show which API key is being used (if key manager is active)
    try:
        from vbagent.api_keys.manager import KeyManager
        km = KeyManager.get_instance()
        if km.is_enabled() and km.current_key_name:
            title += f" : {km.current_key_name}"
    except Exception:
        pass
    
    body = _format_input(input_data)
    with _log_lock:
        console.print()
        console.print(Panel(
            body, title=title, title_align="left",
            border_style="#3b82f6", box=box.SIMPLE,
            padding=(1, 2),
        ))


def log_agent_output(agent_name, output_data, duration=None):
    """Log agent output."""
    display_name = _get_tagged_name(agent_name)
    title = f"[OUTPUT] {display_name}"
    if duration is not None:
        title += f" : {duration:.2f}s"
    
    # Don't truncate for scanner/solution agents - show full LaTeX
    skip_truncation = any(keyword in agent_name.lower() for keyword in ['scanner', 'solution', 'problem'])
    body = _format_output(output_data, skip_truncation=skip_truncation)
    
    with _log_lock:
        console.print()
        console.print(Panel(
            body, title=title, title_align="left",
            border_style="#22c55e", box=box.SIMPLE,
            padding=(1, 2),
        ))


def log_agent_error(agent_name, error):
    """Log agent error."""
    display_name = _get_tagged_name(agent_name)
    err_type = type(error).__name__
    err_msg = str(error)
    body = Text()
    body.append(err_type, style="#f87171")
    body.append(": ", style="#6b7280")
    body.append(_truncate(err_msg, 400), style="#e5e7eb")
    with _log_lock:
        console.print()
        console.print(Panel(
            body, title=f"[ERROR] {display_name}",
            title_align="left", border_style="#ef4444",
            box=box.SIMPLE, padding=(1, 2),
        ))


def log_agent_usage(agent_name, *, model="", duration=0.0, usage=None,
                    response_id=None, has_image=False, reasoning="none"):
    """Log agent completion as a compact JSON panel.

    Always shown (not gated by debug) — this is the primary completion indicator.
    """
    import json as _json
    from rich.syntax import Syntax

    short_model = model.replace("openai/", "") if model else "?"

    data: dict = {
        "duration": f"{duration:.1f}s",
        "model": short_model,
    }

    if reasoning and reasoning != "none":
        data["reasoning"] = reasoning

    if has_image:
        data["image"] = True

    if usage is not None:
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cached = 0
        reasoning_tok = 0
        inp_details = getattr(usage, "input_tokens_details", None)
        if inp_details:
            cached = getattr(inp_details, "cached_tokens", 0) or 0
        out_details = getattr(usage, "output_tokens_details", None)
        if out_details:
            reasoning_tok = getattr(out_details, "reasoning_tokens", 0) or 0

        tokens: dict = {"input": inp}
        if cached:
            tokens["cached"] = cached
        tokens["output"] = out
        if reasoning_tok:
            tokens["reasoning"] = reasoning_tok
        data["tokens"] = tokens

        reqs = getattr(usage, "requests", 0) or 0
        if reqs > 1:
            data["requests"] = reqs

    if response_id:
        short_id = response_id if len(response_id) <= 20 else f"…{response_id[-12:]}"
        data["id"] = short_id

    raw = _json.dumps(data, indent=2, ensure_ascii=False)
    body = Syntax(raw, "json", theme="monokai", word_wrap=True, padding=1)

    with _log_lock:
        display_name = _get_tagged_name(agent_name)
        console.print()
        console.print(f"[dim]✓ {display_name}[/dim]")
        console.print(body)


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
