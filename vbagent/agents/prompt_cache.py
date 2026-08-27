"""Central prompt-cache contracts for OpenAI agent runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any

_CACHE_BOUNDARY_TEXT = (
    "Reuse the stable agent instructions above. The following content is "
    "specific to this request."
)
_DEFAULT_CACHE_SHARDS = 4
_MAX_CACHE_SHARDS = 64


@dataclass(frozen=True)
class PromptCachePlan:
    """Prepared input and routing metadata for one agent run."""

    input_data: str | list
    cache_group_id: str | None
    prompt_cache_key: str | None
    affinity_key: str | None
    model_settings: Any | None
    trace_group_id: str | None
    enabled: bool
    boundary_added: bool = False


def prepare_prompt_cache(
    agent: Any,
    input_data: str | list,
    *,
    group_id: str | None = None,
    previous_response_id: str | None = None,
    allow_sharding: bool = True,
) -> PromptCachePlan:
    """Build the cache contract for an existing agent workflow.

    GPT-5.6 requests sent to the official OpenAI endpoint receive a stable
    explicit breakpoint and prompt cache key. Ordinary callers are grouped by
    model, agent instructions, and one bounded shard. Explicit groups retain
    their trace identity while their cache route may also be sharded.
    """
    model = str(getattr(agent, "model", None) or "default")
    if not _uses_explicit_prompt_cache(model):
        return PromptCachePlan(
            input_data=input_data,
            cache_group_id=group_id,
            prompt_cache_key=None,
            affinity_key=group_id,
            model_settings=None,
            trace_group_id=group_id,
            enabled=False,
        )

    base_group = group_id or _automatic_group(agent, model)
    cache_group = _sharded_group(base_group, input_data) if allow_sharding else base_group
    existing_key = _existing_prompt_cache_key(getattr(agent, "model_settings", None))
    prompt_cache_key = existing_key or _hash_prompt_cache_key(cache_group)

    prepared_input = input_data
    boundary_added = False
    if previous_response_id is None and not _contains_cache_breakpoint(input_data):
        prepared_input = _prepend_cache_boundary(input_data)
        boundary_added = True

    from agents import ModelSettings

    current_settings = getattr(agent, "model_settings", None)
    current_options = getattr(current_settings, "prompt_cache_options", None)
    settings = ModelSettings(
        extra_args=(
            None
            if existing_key
            else {"prompt_cache_key": prompt_cache_key}
        ),
        prompt_cache_options=current_options
        or {"mode": "explicit", "ttl": "30m"},
    )
    return PromptCachePlan(
        input_data=prepared_input,
        cache_group_id=cache_group,
        prompt_cache_key=prompt_cache_key,
        affinity_key=prompt_cache_key,
        model_settings=settings,
        trace_group_id=group_id,
        enabled=True,
        boundary_added=boundary_added,
    )


def _uses_explicit_prompt_cache(model: str) -> bool:
    """Return whether this is an official GPT-5.6 Responses request."""
    from vbagent.config import get_config

    normalized = model.removeprefix("openai/").lower()
    return get_config().base_url is None and normalized.startswith("gpt-5.6")


def _automatic_group(agent: Any, model: str) -> str:
    name = str(getattr(agent, "name", None) or "agent")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "agent"
    slug = slug[:24]
    instructions = getattr(agent, "instructions", None)
    instruction_text = instructions if isinstance(instructions, str) else "<dynamic>"
    prompt_digest = hashlib.sha256(
        f"{model.removeprefix('openai/').lower()}\0{instruction_text}".encode("utf-8")
    ).hexdigest()[:12]
    return f"vbagent:auto:v1:{slug}:{prompt_digest}"


def _cache_shard_count() -> int:
    raw = os.environ.get("VBAGENT_PROMPT_CACHE_SHARDS", str(_DEFAULT_CACHE_SHARDS))
    try:
        requested = int(raw)
    except ValueError:
        requested = _DEFAULT_CACHE_SHARDS
    return min(_MAX_CACHE_SHARDS, max(1, requested))


def _sharded_group(group: str, input_data: str | list) -> str:
    shards = _cache_shard_count()
    if shards == 1:
        return group
    digest = hashlib.sha256(_stable_json(input_data).encode("utf-8")).digest()
    shard = int.from_bytes(digest[:8], "big") % shards
    return f"{group}:s{shard + 1}of{shards}"


def _hash_prompt_cache_key(group: str) -> str:
    digest = hashlib.sha256(group.encode("utf-8")).hexdigest()[:32]
    return f"agents-sdk:group:{digest}"


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return repr(value)


def _existing_prompt_cache_key(settings: Any) -> str | None:
    if settings is None:
        return None
    for mapping_name in ("extra_args", "extra_body"):
        mapping = getattr(settings, mapping_name, None)
        if isinstance(mapping, dict) and mapping.get("prompt_cache_key"):
            return str(mapping["prompt_cache_key"])
    return None


def _contains_cache_breakpoint(value: Any) -> bool:
    if isinstance(value, dict):
        if "prompt_cache_breakpoint" in value:
            return True
        return any(_contains_cache_breakpoint(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_cache_breakpoint(item) for item in value)
    return False


def _prepend_cache_boundary(input_data: str | list) -> list[dict[str, Any]]:
    boundary = {
        "type": "message",
        "role": "developer",
        "content": [
            {
                "type": "input_text",
                "text": _CACHE_BOUNDARY_TEXT,
                "prompt_cache_breakpoint": {"mode": "explicit"},
            }
        ],
    }
    if isinstance(input_data, list):
        return [boundary, *input_data]
    return [
        boundary,
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": input_data}],
        },
    ]
