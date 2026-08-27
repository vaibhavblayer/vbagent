import io
import json

import pytest
from rich.console import Console

from vbagent.ui.agent_io import (
    WorkerLogDecoder,
    print_structured_json,
    render_agent_io,
    structured_json,
)


def test_multiline_json_uses_line_arrays_without_double_encoding():
    payload = {
        "input": "Generate a problem.\n\nTarget: functions → range\n",
        "output": {"problem_latex": "\\item Find the range.\n\\begin{tasks}(2)"},
        "literal": r"a literal \n must not become a newline",
        "count": 1,
    }

    result = structured_json(payload)

    assert result["input"] == {
        "format": "text",
        "lines": ["Generate a problem.", "", "Target: functions → range", ""],
    }
    assert result["output"]["problem_latex"] == {
        "format": "latex",
        "lines": [r"\item Find the range.", r"\begin{tasks}(2)"],
    }
    assert result["literal"] == payload["literal"]
    assert result["count"] == 1
    assert payload["input"].endswith("\n")  # No mutation of recorded data.
    assert structured_json(result) == result


@pytest.mark.parametrize("width", [32, 80, 160])
def test_pretty_json_remains_valid_when_copied_at_narrow_terminal_width(width):
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=False, width=width)
    payload = {
        "input": "a long prompt with a literal backslash \\ " * 20 + "\nnext line"
    }

    print_structured_json(console, payload)

    assert json.loads(stream.getvalue()) == structured_json(payload)
    assert "                \n" not in stream.getvalue()


@pytest.mark.parametrize("chunk_size", [1, 7, 80, 262144])
def test_decoder_reassembles_split_jsonl_events(chunk_size):
    expected = {
        "vbagent_io": 1,
        "event": "output",
        "agent": "Math",
        "task": "item 002 · abc123",
        "output": {"solution_latex": "\\begin{solution}\n1 → 2\n\\end{solution}"},
    }
    line = json.dumps(expected, ensure_ascii=False) + "\n"
    decoder = WorkerLogDecoder()
    events = []

    for offset in range(0, len(line), chunk_size):
        events.extend(decoder.feed(line[offset : offset + chunk_size]))

    assert events == [expected]
    assert decoder.feed("", final=True) == []


def test_decoder_keeps_a_large_output_across_log_pages():
    expected = {
        "vbagent_io": 1,
        "event": "output",
        "agent": "Math",
        "output": "line\n" * 70000,
    }
    serialized = json.dumps(expected) + "\n"
    decoder = WorkerLogDecoder()
    events = []
    for offset in range(0, len(serialized), 65536):
        events.extend(decoder.feed(serialized[offset : offset + 65536]))
    assert events == [expected]


def test_decoder_recovers_legacy_padded_and_wrapped_json_panel():
    legacy = (
        "   [INPUT] IdeaGenerator-mathematics : gpt-5.6-terra    \n"
        "                                                        \n"
        "   {                                                    \n"
        '     "agent": "IdeaGenerator-mathematics",              \n'
        '     "model": "gpt-5.6-terra",                          \n'
        '     "input": "Generate a mathematics problem from      \n'
        '   these ideas.\\n\\nTarget: functions."                 \n'
        "   }                                                    \n"
    )

    events = WorkerLogDecoder().feed(legacy, final=True)

    assert len(events) == 1
    assert events[0]["event"] == "input"
    assert (
        events[0]["input"]
        == "Generate a mathematics problem from these ideas.\n\nTarget: functions."
    )
    stream = io.StringIO()
    render_agent_io(Console(file=stream, width=80, force_terminal=False), events[0])
    rendered = stream.getvalue()
    assert '"lines": [' in rendered
    assert '"content": "\\n' not in rendered
    assert "                \n" not in rendered


def test_decoder_preserves_unknown_and_malformed_output_as_structured_text():
    decoder = WorkerLogDecoder()
    data = "worker warning: [red]literal[/red]\n[OUTPUT] Draft\n{bad\n"
    events = decoder.feed(data, final=True)
    assert events[0]["content"] == "worker warning: [red]literal[/red]"
    assert events[1]["content"] == "[OUTPUT] Draft\n{bad"


def test_quiet_worker_http_success_noise_remains_available_in_verbose_mode():
    event = {
        "event": "worker_log",
        "content": '2026-08-27 INFO httpx: HTTP Request: POST https://example.test "HTTP/1.1 200 OK"',
    }
    stream = io.StringIO()
    console = Console(file=stream)
    render_agent_io(console, event)
    assert stream.getvalue() == ""
    render_agent_io(console, event, detailed_usage=True)
    assert "200 OK" in stream.getvalue()
