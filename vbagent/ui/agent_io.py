"""Structured agent traces, independent of terminal width and log transport."""

from __future__ import annotations

import json
import re
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.text import Text

IO_VERSION = 1
_PHASES = {"input", "output", "usage", "error"}
_COLORS = {
    "input": "#60a5fa",
    "output": "#4ade80",
    "usage": "#a78bfa",
    "error": "#f87171",
}
_LEGACY_HEADER = re.compile(r"^\s*\[(INPUT|OUTPUT|USAGE|ERROR)\]\s+(.+?)\s*$")
_LATEX = re.compile(r"\\(?:begin|end|item|task|frac|sqrt|text|left|right)\b")
_HTTP_INFO = re.compile(r'\bINFO httpx: HTTP Request: .*"HTTP/[^ ]+ 2\d\d\b')


def structured_json(value: Any, *, field: str = "") -> Any:
    """Keep JSON types while displaying multiline strings as explicit line arrays.

    This is a display projection only. The worker log retains the original
    strings, including newlines, so the recorded request/response is lossless.
    Never unescape arbitrary strings: a literal LaTeX backslash must stay one.
    """
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        if (
            value.get("format") in ("text", "latex")
            and isinstance(value.get("lines"), list)
            and all(isinstance(line, str) for line in value["lines"])
        ):
            return dict(value)
        return {
            str(key): structured_json(item, field=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [structured_json(item, field=field) for item in value]
    if isinstance(value, str):
        is_latex = field.endswith("latex") or bool(_LATEX.search(value))
        if "\n" in value or "\r" in value or is_latex:
            return {
                "format": "latex" if is_latex else "text",
                "lines": value.replace("\r\n", "\n").replace("\r", "\n").split("\n"),
            }
    return value


def print_structured_json(
    console: Console,
    payload: Any,
    *,
    title: str | None = None,
    color: str = "#4ade80",
) -> None:
    """Print one JSON object without panels, padding, or inserted line wraps."""
    if title:
        console.print(Text(title, style=f"bold {color}"), soft_wrap=True)
    console.print(
        JSON.from_data(
            structured_json(payload), indent=2, ensure_ascii=False, default=str
        ),
        soft_wrap=True,
    )
    console.print()


def render_agent_io(
    console: Console,
    event: dict[str, Any],
    *,
    detailed_usage: bool = False,
) -> None:
    """Render a decoded event once, retaining JSON for inputs and outputs."""
    phase = str(event.get("event", "worker_log"))
    payload = {key: value for key, value in event.items() if key != "vbagent_io"}
    if phase == "worker_log":
        content = str(payload.get("content") or "")
        if not detailed_usage and _HTTP_INFO.search(content):
            return
        print_structured_json(console, payload, color="#94a3b8")
        return

    agent = str(payload.get("agent") or "Agent")
    title = f"[{phase.upper()}] {agent}"
    if payload.get("task"):
        title += f" · {payload['task']}"
    if phase == "usage" and not detailed_usage:
        tokens = payload.get("tokens")
        if not isinstance(tokens, dict):
            tokens = {}
        compact = {
            "event": "usage",
            "agent": agent,
            **({"task": payload["task"]} if payload.get("task") else {}),
            "model": payload.get("model"),
            "duration": payload.get("duration"),
            "tokens": {
                key: tokens[key]
                for key in ("input", "output", "cached", "cache_hit_percent")
                if key in tokens
            },
        }
        # Telemetry stays a small JSON line; --verbose shows every recorded field.
        console.print(Text(f"[USAGE] {agent}", style="dim"), soft_wrap=True)
        console.print(
            Text(json.dumps(compact, ensure_ascii=False, default=str), style="dim"),
            soft_wrap=True,
        )
        console.print()
        return
    print_structured_json(
        console, payload, title=title, color=_COLORS.get(phase, "#94a3b8")
    )


class WorkerLogDecoder:
    """Incrementally decode JSONL events and older Rich-panel worker logs.

    A log page may end anywhere within a JSON string. Wait for its newline
    before decoding, and keep separate decoders for separate runs. Legacy
    pretty JSON is recovered where possible; unrecognized text remains visible.
    """

    MAX_BUFFER_CHARS = 4 * 1024 * 1024

    def __init__(self) -> None:
        self._pending = ""
        self._legacy_phase: str | None = None
        self._legacy_title = ""
        self._legacy_lines: list[str] = []
        self._legacy_size = 0

    def feed(self, content: str, *, final: bool = False) -> list[dict[str, Any]]:
        self._pending += content
        lines = self._pending.split("\n")
        self._pending = lines.pop()
        events: list[dict[str, Any]] = []
        for line in lines:
            events.extend(self._line(line))
        if len(self._pending) > self.MAX_BUFFER_CHARS:
            events.append(self._text(self._pending))
            self._pending = ""
        if final:
            if self._pending:
                events.extend(self._line(self._pending))
                self._pending = ""
            events.extend(self._flush_legacy())
        return events

    def _line(self, line: str) -> list[dict[str, Any]]:
        stripped = line.strip()
        if not stripped:
            return []
        header = _LEGACY_HEADER.match(line)
        if header:
            events = self._flush_legacy()
            self._legacy_phase = header.group(1).lower()
            self._legacy_title = header.group(2)
            return events

        try:
            payload = json.loads(stripped)
        except (ValueError, TypeError):
            payload = None
        if (
            isinstance(payload, dict)
            and payload.get("vbagent_io") == IO_VERSION
            and payload.get("event") in _PHASES
        ):
            return [*self._flush_legacy(), payload]

        if self._legacy_phase is not None:
            # Old Rich panels wrap JSON strings across physical lines. These
            # spaces are presentation-only; the legacy file is never rewritten.
            if not self._legacy_lines and not stripped.startswith("{"):
                return [*self._flush_legacy(), self._text(stripped)]
            self._legacy_lines.append(stripped)
            self._legacy_size += len(stripped)
            if stripped.endswith("}"):
                for separator in ("\n", " "):
                    try:
                        recovered = json.loads(separator.join(self._legacy_lines))
                    except (ValueError, TypeError):
                        continue
                    if isinstance(recovered, dict):
                        event = {**recovered, "event": self._legacy_phase}
                        if "agent" not in event:
                            event["agent"] = self._legacy_title.split(" : ")[0]
                        self._reset_legacy()
                        return [event]
            if self._legacy_size > self.MAX_BUFFER_CHARS:
                return self._flush_legacy()
            return []
        return [self._text(stripped)]

    def _flush_legacy(self) -> list[dict[str, Any]]:
        if self._legacy_phase is None:
            return []
        text = f"[{self._legacy_phase.upper()}] {self._legacy_title}"
        if self._legacy_lines:
            text += "\n" + "\n".join(self._legacy_lines)
        self._reset_legacy()
        return [self._text(text)]

    def _reset_legacy(self) -> None:
        self._legacy_phase = None
        self._legacy_title = ""
        self._legacy_lines = []
        self._legacy_size = 0

    @staticmethod
    def _text(content: str) -> dict[str, Any]:
        return {"event": "worker_log", "content": content}
