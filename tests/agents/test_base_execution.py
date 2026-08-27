"""Regression tests for agent request lifecycle and concurrency."""

from __future__ import annotations

import asyncio
import inspect
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from rich.console import Console

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


def test_gpt56_sync_calls_get_automatic_explicit_cache_contract(monkeypatch):
    from agents import ModelSettings

    from vbagent.agents import prompt_cache

    seen_inputs = []
    seen_configs = []
    affinities = []

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            seen_inputs.append(kwargs["input"])
            seen_configs.append(kwargs["run_config"])
            return _result("cached")

    agent = SimpleNamespace(
        name="SyllabusDraft",
        model="gpt-5.6-sol",
        model_settings=ModelSettings(reasoning={"effort": "high"}),
        instructions="Stable syllabus-constrained authoring instructions.",
    )
    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (
            affinities.append(affinity_key) or object(),
            _Client(),
            None,
        ),
    )
    monkeypatch.setattr(prompt_cache, "_uses_explicit_prompt_cache", lambda _: True)
    monkeypatch.setenv("VBAGENT_PROMPT_CACHE_SHARDS", "1")

    for input_text in ("first problem spec", "second problem spec"):
        assert base.run_agent_sync(
            agent,
            input_text,
            show_spinner=False,
        ) == "cached"

    assert affinities[0] == affinities[1]
    assert affinities[0].startswith("agents-sdk:group:")
    assert all(config.group_id is None for config in seen_configs)
    assert all(
        config.model_settings.extra_args["prompt_cache_key"] == affinities[0]
        for config in seen_configs
    )
    assert all(
        config.model_settings.prompt_cache_options
        == {"mode": "explicit", "ttl": "30m"}
        for config in seen_configs
    )
    assert all(payload[0]["role"] == "developer" for payload in seen_inputs)
    assert all(
        payload[0]["content"][0]["prompt_cache_breakpoint"]
        == {"mode": "explicit"}
        for payload in seen_inputs
    )


def test_cache_contract_reaches_responses_api_request_body(monkeypatch):
    import httpx
    from agents import Agent, ModelSettings
    from agents.models.openai_provider import OpenAIProvider
    from openai import AsyncOpenAI

    from vbagent.agents import prompt_cache

    request_bodies = []

    async def handler(request):
        request_bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp-cache-contract",
                "created_at": 0.0,
                "model": "gpt-5.6-sol",
                "object": "response",
                "output": [
                    {
                        "id": "msg-cache-contract",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "ok",
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "status": "completed",
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 1,
                    "total_tokens": 21,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 10,
                    },
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    openai_client = AsyncOpenAI(
        api_key="test",
        base_url="https://api.openai.test/v1",
        http_client=http_client,
    )
    provider = OpenAIProvider(openai_client=openai_client)
    agent = Agent(
        name="RequestBodyContract",
        instructions="Stable request-body contract.",
        model="gpt-5.6-sol",
        model_settings=ModelSettings(),
    )
    monkeypatch.setattr(prompt_cache, "_uses_explicit_prompt_cache", lambda _: True)
    monkeypatch.setenv("VBAGENT_PROMPT_CACHE_SHARDS", "1")
    monkeypatch.setattr(
        base,
        "_create_request_provider",
        lambda model, credentials=None, affinity_key=None: (
            provider,
            openai_client,
            None,
        ),
    )
    monkeypatch.setattr(base, "_track_usage", lambda *args: None)

    assert base.run_agent_sync(
        agent,
        "dynamic input",
        show_spinner=False,
    ) == "ok"

    body = request_bodies[0]
    assert body["prompt_cache_key"].startswith("agents-sdk:group:")
    assert body["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert body["input"][0]["content"][0]["prompt_cache_breakpoint"] == {
        "mode": "explicit"
    }


def test_automatic_cache_groups_use_only_bounded_shards(monkeypatch):
    from agents import ModelSettings

    from vbagent.agents import prompt_cache

    agent = SimpleNamespace(
        name="AnswerAgreement",
        model="gpt-5.6-luna",
        model_settings=ModelSettings(),
        instructions="Stable answer adjudication contract.",
    )
    monkeypatch.setattr(prompt_cache, "_uses_explicit_prompt_cache", lambda _: True)
    monkeypatch.setenv("VBAGENT_PROMPT_CACHE_SHARDS", "4")

    plans = [
        prompt_cache.prepare_prompt_cache(agent, f"candidate {index}")
        for index in range(100)
    ]
    groups = {plan.cache_group_id for plan in plans}

    assert 1 < len(groups) <= 4
    assert all(":s" in group and group.endswith("of4") for group in groups)
    assert all(len(plan.prompt_cache_key) < 64 for plan in plans)


def test_existing_cache_boundary_is_not_duplicated(monkeypatch):
    from agents import ModelSettings

    from vbagent.agents import prompt_cache

    agent = SimpleNamespace(
        name="Classifier",
        model="gpt-5.6-sol",
        model_settings=ModelSettings(),
        instructions="Stable classifier instructions.",
    )
    message = [
        {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": "existing",
                    "prompt_cache_breakpoint": {"mode": "explicit"},
                }
            ],
        },
        {"role": "user", "content": "dynamic"},
    ]
    monkeypatch.setattr(prompt_cache, "_uses_explicit_prompt_cache", lambda _: True)

    plan = prompt_cache.prepare_prompt_cache(agent, message, group_id="classifier")

    assert plan.input_data is message
    assert not plan.boundary_added


def test_third_party_provider_keeps_original_input_and_settings(monkeypatch):
    from agents import ModelSettings

    from vbagent.agents import prompt_cache

    agent = SimpleNamespace(
        name="CompatibleProvider",
        model="gpt-5.6-sol",
        model_settings=ModelSettings(),
        instructions="Provider-specific instructions.",
    )
    monkeypatch.setattr(prompt_cache, "_uses_explicit_prompt_cache", lambda _: False)

    plan = prompt_cache.prepare_prompt_cache(
        agent,
        "original input",
        group_id="explicit-group",
    )

    assert plan.input_data == "original input"
    assert plan.model_settings is None
    assert plan.affinity_key == "explicit-group"
    assert not plan.enabled


def test_terminal_rate_limit_fails_over_to_another_managed_profile(monkeypatch, tmp_path):
    attempts = []
    released = []
    cooled = []

    class RateLimited(RuntimeError):
        status_code = 429

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            attempts.append(kwargs)
            if len(attempts) == 1:
                raise RateLimited("profile quota exhausted")
            return _result("recovered")

    def create_provider(model, credentials=None, affinity_key=None, excluded_key_names=None):
        name = "profile-b" if excluded_key_names else "profile-a"
        pinned = base.PinnedRequestCredentials(
            f"secret-{name}",
            None,
            name,
            "org-main:global",
            True,
        )
        return object(), _Client(), name, pinned

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(base, "_create_request_provider", create_provider)
    monkeypatch.setattr(base, "_release_managed_profile", released.append)
    monkeypatch.setattr(
        base,
        "_mark_profile_unavailable",
        lambda name, seconds: cooled.append((name, seconds)),
    )
    event_log = tmp_path / "events.jsonl"
    monkeypatch.setenv("VBAGENT_LOG_FILE", str(event_log))

    output = base.run_agent_sync(_agent(), "input", show_spinner=False)

    assert output == "recovered"
    assert len(attempts) == 2
    assert cooled == [("profile-a", 60.0)]
    assert released == ["profile-a", "profile-b"]
    events = [json.loads(line) for line in event_log.read_text().splitlines()]
    failover = next(event for event in events if event["event"] == "profile_failover")
    assert failover["key_name"] == "profile-a"
    assert failover["status_code"] == 429


def test_response_chain_never_rotates_pinned_credentials(monkeypatch):
    class RateLimited(RuntimeError):
        status_code = 429

    calls = []
    pinned = base.PinnedRequestCredentials(
        "secret",
        None,
        "profile-a",
        "org-main:global",
        True,
    )

    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            raise RateLimited("do not rotate this response chain")

    def create_provider(model, credentials=None, affinity_key=None):
        calls.append(credentials)
        return object(), _Client(), credentials.key_name, credentials

    monkeypatch.setattr(base, "_get_runner_class", lambda: Runner)
    monkeypatch.setattr(base, "_create_request_provider", create_provider)
    monkeypatch.setattr(
        base,
        "_mark_profile_unavailable",
        lambda *args: pytest.fail("pinned response chains must not fail over"),
    )

    with pytest.raises(RateLimited):
        base.run_agent_sync_continued(
            _agent(),
            "next",
            "repair-group",
            previous_response_id="resp-existing",
            credentials=pinned,
            show_spinner=False,
        )

    assert calls == [pinned]


def test_response_chain_requires_credentials_with_previous_response_id():
    with pytest.raises(ValueError, match="credentials.*required"):
        base.run_agent_sync_continued(
            _agent(),
            "next",
            "repair-group",
            previous_response_id="resp-existing",
            show_spinner=False,
        )


def test_configured_profile_manager_fails_closed_without_available_profile(monkeypatch):
    import vbagent.config
    from vbagent.api_keys import KeyManager

    class Manager:
        @staticmethod
        def is_configured():
            return True

        @staticmethod
        def select_key_for_model(*args, **kwargs):
            raise RuntimeError("No available API profiles")

    monkeypatch.setattr(
        vbagent.config,
        "get_config",
        lambda: SimpleNamespace(
            base_url=None,
            api_key="configured-fallback-must-not-be-used",
        ),
    )
    monkeypatch.setattr(
        KeyManager,
        "get_instance",
        classmethod(lambda cls: Manager()),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "environment-fallback-must-not-be-used")

    with pytest.raises(RuntimeError, match="No available API profiles"):
        base._resolve_request_credentials("gpt-5.6-sol")
