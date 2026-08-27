"""Pydantic models for API key configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_MODEL_CATEGORIES = {
    # Sol remains in the standard-capability quota. Terra and Luna share the
    # mini quota for the current model lineup.
    "standard": [
        "gpt-5.6-sol",
        "gpt-5.6",
        "gpt-5.5",
        "gpt-5.4",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
    ],
    "mini": [
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "gpt-5.5-mini",
        "gpt-5.4-mini",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
    ],
}


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
    cache_domain: str | None = Field(
        default=None,
        description=(
            "Prompt-cache scope shared by profiles in the same OpenAI "
            "organization and processing region. Missing values are isolated "
            "to this profile."
        ),
    )
    limits: dict[str, CategoryLimits] = Field(
        default_factory=lambda: {
            "standard": CategoryLimits(daily_limit=1_000_000),
            "mini": CategoryLimits(daily_limit=2_000_000),
        },
        description="Token limits per model category",
    )
    enabled: bool = Field(default=True, description="Whether this key is active")

    @field_validator("cache_domain")
    @classmethod
    def normalize_cache_domain(cls, value: str | None) -> str | None:
        """Treat blank cache domains as the safe, profile-isolated default."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @property
    def effective_cache_domain(self) -> str:
        """Return the declared cache domain or a profile-specific fallback."""
        return self.cache_domain or f"profile:{self.name}"


class KeyManagerConfig(BaseModel):
    """Root configuration for key manager."""

    keys: list[ApiKeyConfig] = Field(default_factory=list, description="List of API keys")
    rotation_strategy: Literal["least_used", "round_robin", "random"] = Field(
        default="least_used",
        description="Strategy for selecting keys",
    )
    model_categories: dict[str, list[str]] = Field(
        default_factory=lambda: {
            category: list(patterns)
            for category, patterns in DEFAULT_MODEL_CATEGORIES.items()
        },
        description="Model name patterns for each category",
    )
    last_used_index: int = Field(default=0, description="Index for round-robin rotation")

    @model_validator(mode="before")
    @classmethod
    def normalize_current_model_categories(cls, values):
        """Move current Terra/Luna models into the mini quota.

        Existing configuration files commonly contain the former mapping,
        where Terra was listed under ``standard``. Normalize only the known
        current model names so custom provider patterns remain untouched.
        """
        if not isinstance(values, dict) or "model_categories" not in values:
            return values

        categories = values.get("model_categories")
        if not isinstance(categories, dict):
            return values

        normalized = {
            category: list(patterns)
            for category, patterns in categories.items()
        }
        standard = normalized.setdefault("standard", [])
        mini = normalized.setdefault("mini", [])

        def move_pattern(pattern: str, source: list[str], target: list[str]) -> None:
            source[:] = [item for item in source if item.lower() != pattern.lower()]
            if not any(item.lower() == pattern.lower() for item in target):
                target.insert(0, pattern)

        move_pattern("gpt-5.6-terra", standard, mini)
        move_pattern("gpt-5.6-luna", standard, mini)
        if not any(item.lower() == "gpt-5.6-sol" for item in standard):
            standard.insert(0, "gpt-5.6-sol")

        values = dict(values)
        values["model_categories"] = normalized
        return values
