"""Shared calculations for provider prompt-cache telemetry."""

from __future__ import annotations

GPT56_CACHE_READ_INPUT_MULTIPLIER = 0.10
GPT56_CACHE_WRITE_INPUT_MULTIPLIER = 1.25


def gpt56_effective_input_multiplier(
    *,
    input_tokens: int,
    ordinary_input_tokens: int,
    cached_tokens: int,
    cache_write_tokens: int,
    metrics_complete: bool,
) -> float | None:
    """Return GPT-5.6-equivalent input cost, or ``None`` for partial data."""
    if input_tokens <= 0 or not metrics_complete:
        return None
    return round(
        (
            ordinary_input_tokens
            + GPT56_CACHE_READ_INPUT_MULTIPLIER * cached_tokens
            + GPT56_CACHE_WRITE_INPUT_MULTIPLIER * cache_write_tokens
        )
        / input_tokens,
        4,
    )
