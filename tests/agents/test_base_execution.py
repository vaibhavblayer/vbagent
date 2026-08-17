"""Regression tests for agent request lifecycle and concurrency."""

from __future__ import annotations

import asyncio
import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from rich.console import Console
import io
import json

from vbagent.agents import base


class _Client:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def _agent(name: str = "TestAgent"):
    return SimpleNamespace(name=name, model="test-model", model_settings=None)


def _result(value="ok"):
    return SimpleNamespace(
        final_output=value,
        context_wrapper=None,
        raw_responses=[],
    )


@pytest.fixture(autouse=True)
def _quiet_agent_logs():
    from vbagent.ui.logging import agent_logging_context

    with agent_logging_context(
        output_console=Console(file=io.StringIO()),
        quiet=True,
    ):
        yield


def test_sync_timeout_cancels_sdk_task_and_closes_client(monkeypatch, tmp_path):
    cancelled = threading.Event()
    completed = threading.Event()
    client = _Client()

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            try:
                await asyncio.sleep(10)
                completed.set()
                return _result()
            finally:
                cancelled.set()

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (object(), client, None),
    )
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("VBAGENT_LOG_FILE", str(event_log))

    with pytest.raises(TimeoutError, match="timed out"):
        base.run_agent_sync(_agent(), "input", show_spinner=False, timeout=0.02)

    assert cancelled.wait(0.2)
    assert not completed.is_set()
    assert client.closed
    events = [json.loads(line) for line in event_log.read_text().splitlines()]
    assert [event["event"] for event in events] == [
        "request_queued",
        "request_started",
        "cancelled",
    ]
    assert events[-1]["request_duration"] >= 0.01


def test_completed_response_is_returned_and_client_is_closed(monkeypatch):
    client = _Client()

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            await asyncio.sleep(0.01)
            return _result("received")

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (object(), client, "key-a"),
    )

    output = base.run_agent_sync(
        _agent(), "input", show_spinner=False, timeout=0.2
    )

    assert output == "received"
    assert client.closed


def test_sync_wrapper_remains_usable_inside_running_event_loop(monkeypatch):
    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            return _result("nested")

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (object(), _Client(), None),
    )

    async def caller():
        return base.run_agent_sync(
            _agent(), "input", show_spinner=False, timeout=1
        )

    assert asyncio.run(caller()) == "nested"


def test_global_request_limit_covers_parallel_sync_callers(monkeypatch):
    active = 0
    peak = 0
    lock = threading.Lock()

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                await asyncio.sleep(0.03)
                return _result()
            finally:
                with lock:
                    active -= 1

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(base, "_request_slots", threading.BoundedSemaphore(2))
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (object(), _Client(), None),
    )

    with ThreadPoolExecutor(max_workers=6) as executor:
        outputs = list(
            executor.map(
                lambda _: base.run_agent_sync(
                    _agent(), "input", show_spinner=False, timeout=1
                ),
                range(6),
            )
        )

    assert outputs == ["ok"] * 6
    assert peak == 2


def test_vbsocial_consumed_signatures_remain_stable():
    assert list(inspect.signature(base.create_agent).parameters) == [
        "name",
        "instructions",
        "model",
        "model_settings",
        "output_type",
        "tools",
        "agent_type",
    ]
    assert list(inspect.signature(base.run_agent_sync).parameters) == [
        "agent",
        "input_text",
        "show_spinner",
        "timeout",
    ]


def test_cacheable_image_message_places_boundary_before_image(tmp_path):
    image = tmp_path / "question.png"
    image.write_bytes(b"not-a-real-png")

    message = base.create_cacheable_image_message(
        str(image),
        "Analyze this image.",
        "Stable classifier boundary.",
    )

    boundary = message[0]
    assert boundary["role"] == "developer"
    assert boundary["content"][0]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert boundary["content"][0]["text"] == "Stable classifier boundary."
    assert message[1]["role"] == "user"
    assert message[1]["content"][0]["type"] == "input_image"


def test_grouped_run_forwards_stable_group_id(monkeypatch):
    seen = []

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            seen.append(kwargs["run_config"].group_id)
            return _result("grouped")

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (object(), _Client(), None),
    )

    for _ in range(2):
        assert base.run_agent_sync_grouped(
            _agent(),
            "changing attempt input",
            "vbagent:tikz-fix:v1:abc",
            show_spinner=False,
        ) == "grouped"

    assert seen == ["vbagent:tikz-fix:v1:abc"] * 2


def test_grouped_calls_forward_affinity_and_log_profile(monkeypatch, tmp_path):
    provider_credentials = []
    affinity_keys = []

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            return _result("grouped")

    def create_provider(model, credentials=None, affinity_key=None):
        provider_credentials.append(credentials)
        affinity_keys.append(affinity_key)
        name = "profile-a"
        pinned = base.PinnedRequestCredentials("secret", None, name)
        return object(), _Client(), name, pinned

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(base, "_create_request_provider", create_provider)
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("VBAGENT_LOG_FILE", str(event_log))

    for _ in range(2):
        assert base.run_agent_sync_grouped(
            _agent(),
            "input",
            "classifier-group",
            show_spinner=False,
        ) == "grouped"

    assert provider_credentials == [None, None]
    assert affinity_keys == ["classifier-group", "classifier-group"]
    completed = [
        json.loads(line)
        for line in event_log.read_text().splitlines()
        if json.loads(line)["event"] == "completed"
    ]
    assert [event["key_name"] for event in completed] == ["profile-a", "profile-a"]


def test_continued_run_forwards_response_id_and_pins_credentials(monkeypatch):
    seen_response_ids = []
    seen_credentials = []
    pinned = base.PinnedRequestCredentials("secret", None, "key-a")

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            seen_response_ids.append(kwargs["previous_response_id"])
            result = _result("continued")
            result.raw_responses = [SimpleNamespace(response_id="resp-next", model="test-model")]
            return result

    def create_provider(model, credentials=None, affinity_key=None):
        seen_credentials.append(credentials)
        selected = credentials or pinned
        return object(), _Client(), selected.key_name, selected

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(base, "_create_request_provider", create_provider)

    first = base.run_agent_sync_continued(
        _agent(), "first", "repair-group", show_spinner=False
    )
    second = base.run_agent_sync_continued(
        _agent(),
        "second",
        "repair-group",
        previous_response_id=first.response_id,
        credentials=first.credentials,
        show_spinner=False,
    )

    assert seen_response_ids == [None, "resp-next"]
    assert seen_credentials == [None, pinned]
    assert second.credentials is pinned
