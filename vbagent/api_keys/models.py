"""Pydantic models for API key configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _get_utc_date() -> str:
    """Get current date in UTC timezone."""
    return datetime.now(timezone.utc).date().isoformat()


class CategoryLimits(BaseModel):
    """Token limits for a model category."""

    daily_limit: int = Field(default=1_000_000, description="Daily token limit")
    used_today: int = Field(default=0, description="Tokens used today")
    last_reset: str = Field(default_factory=_get_utc_date, description="Last reset date (UTC)")


class ApiKeyConfig(BaseModel):
    """Configuration for a single API key."""

    name: str = Field(description="Friendly name for the key")
    api_key: str = Field(description="OpenAI API key")
    limits: dict[str, CategoryLimits] = Field(
        default_factory=lambda: {
            "standard": CategoryLimits(daily_limit=1_000_000),
            "mini": CategoryLimits(daily_limit=2_000_000),
        },
        description="Token limits per model category",
    )
    enabled: bool = Field(default=True, description="Whether this key is active")


class KeyManagerConfig(BaseModel):
    """Root configuration for key manager."""

    keys: list[ApiKeyConfig] = Field(default_factory=list, description="List of API keys")
    rotation_strategy: Literal["least_used", "round_robin", "random"] = Field(
        default="least_used",
        description="Strategy for selecting keys",
    )
    model_categories: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "standard": ["gpt-5.5", "gpt-5.4", "gpt-4o", "gpt-4-turbo", "gpt-4"],
            "mini": ["gpt-5.5-mini", "gpt-5.4-mini", "gpt-4o-mini", "gpt-3.5-turbo"],
        },
        description="Model name patterns for each category",
    )
    last_used_index: int = Field(default=0, description="Index for round-robin rotation")
