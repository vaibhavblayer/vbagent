"""Behavior tests for compact, debug, quiet, and persistent agent logging."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

from rich.console import Console

from vbagent.config import VBAgentConfig
from vbagent.ui.logging import (
    agent_logging_context,
    log_agent_input,
    log_agent_output,
    log_agent_usage,
)


def _usage():
    return SimpleNamespace(
        input_tokens=3200,
        output_tokens=850,
        requests=1,
        input_tokens_details=SimpleNamespace(
            cached_tokens=1200,
            cache_write_tokens=1600,
        ),
        output_tokens_details=SimpleNamespace(reasoning_tokens=400),
    )


def _set_level(monkeypatch, level: str):
    import vbagent.config

    config = VBAgentConfig(debug=level == "DEBUG", log_level=level)
    monkeypatch.setattr(vbagent.config, "get_config", lambda: config)


def test_info_mode_logs_json_input_usage_and_output(monkeypatch):
    _set_level(monkeypatch, "INFO")
    stream = io.StringIO()
    output = Console(file=stream, force_terminal=False, width=160)

    with agent_logging_context(output_console=output):
        log_agent_input("Mechanics", "full private prompt", "gpt-5.4")
        log_agent_usage(
            "Mechanics",
            model="gpt-5.4",
            duration=42.3,
            request_duration=41.8,
            queue_duration=0.5,
            usage=_usage(),
            response_id="resp_1234567890abcdefghijkl",
            key_name="Calculus With Cigarettes",
        )
        log_agent_output("Mechanics", "full generated output", 42.3)

    rendered = stream.getvalue()
    assert "[INPUT] Mechanics" in rendered
    assert "[USAGE] Mechanics" in rendered
    assert "[OUTPUT] Mechanics" in rendered
    assert '"input": "full private prompt"' in rendered
    assert '"request_duration": "41.8s"' in rendered
    assert '"queue_duration": "0.5s"' in rendered
    assert '"input": 3200' in rendered
    assert '"cached": 1200' in rendered
    assert '"cache_write": 1600' in rendered
    assert '"cache_write_percent": 50.0' in rendered
    assert '"key_name": "Calculus With Cigarettes"' in rendered
    assert '"output": "full generated output"' in rendered


def test_debug_mode_keeps_full_scanner_output(monkeypatch):
    _set_level(monkeypatch, "DEBUG")
    monkeypatch.setenv("VBAGENT_LOG_FILE", "off")
    stream = io.StringIO()
    output = Console(file=stream, force_terminal=False, width=120)
    long_output = "generated output " * 400

    with agent_logging_context(output_console=output):
        log_agent_input("Scanner", "problem preview", "gpt-5.4-mini")
        log_agent_output("Scanner", long_output, 2.0)

    rendered = stream.getvalue()
    assert "[INPUT] Scanner" in rendered
    assert "[OUTPUT] Scanner" in rendered
    assert "chars total" not in rendered
    assert rendered.count("generated output") > 300


def test_quiet_mode_suppresses_ui_but_keeps_jsonl_events(monkeypatch, tmp_path):
    _set_level(monkeypatch, "INFO")
    event_log = tmp_path / "agent-events.jsonl"
    monkeypatch.setenv("VBAGENT_LOG_FILE", str(event_log))
    stream = io.StringIO()
    output = Console(file=stream, force_terminal=False)
    response_id = "resp_full_identifier_for_diagnostics"

    with agent_logging_context(output_console=output, quiet=True):
        log_agent_usage(
            "Classifier",
            model="gpt-5.4-mini",
            duration=1.2,
            usage=_usage(),
            response_id=response_id,
        )

    assert stream.getvalue() == ""
    event = json.loads(event_log.read_text())
    assert event["event"] == "completed"
    assert event["response_id"] == response_id
    assert event["tokens"]["cached"] == 1200
    assert event["tokens"]["cache_write"] == 1600
    assert event["tokens"]["cache_hit_percent"] == 37.5


def test_cli_and_agent_logging_share_the_same_console():
    from vbagent.cli.common import _get_console

    output = Console(file=io.StringIO())
    with agent_logging_context(output_console=output):
        assert _get_console() is output


def test_quiet_pipeline_context_is_restored_after_call(monkeypatch):
    _set_level(monkeypatch, "INFO")
    import vbagent.pipeline.runner as pipeline_runner

    def fake_pipeline(**kwargs):
        log_agent_usage("Worker", model="test", duration=0.1)
        return "result"

    monkeypatch.setattr(
        pipeline_runner,
        "_process_image_impl",
        fake_pipeline,
    )
    stream = io.StringIO()
    output = Console(file=stream, force_terminal=False)

    with agent_logging_context(output_console=output):
        assert pipeline_runner.process_image("question.png", quiet=True) == "result"
        assert stream.getvalue() == ""
        log_agent_usage("After", model="test", duration=0.1)

    assert "[USAGE] After" in stream.getvalue()
    assert "Worker" not in stream.getvalue()
