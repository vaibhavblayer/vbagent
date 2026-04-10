"""API key manager for rotation and usage tracking."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Optional

from vbagent.api_keys.models import KeyManagerConfig, ApiKeyConfig, CategoryLimits


class KeyManager:
    """Manages multiple API keys with usage tracking and rotation."""

    _instance: Optional[KeyManager] = None
    _config_path = Path.home() / ".config" / "vbagent" / "api_keys.json"

    def __init__(self):
        """Initialize key manager."""
        self.config: Optional[KeyManagerConfig] = None
        self.current_key_name: Optional[str] = None
        self._load_config()

    @classmethod
    def get_instance(cls) -> KeyManager:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_config(self):
        """Load configuration from file."""
        if not self._config_path.exists():
            self.config = None
            return

        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
            self.config = KeyManagerConfig(**data)
        except Exception as e:
            print(f"Warning: Failed to load API key config: {e}")
            self.config = None

    def _save_config(self):
        """Save configuration to file."""
        if self.config is None:
            return

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    def is_enabled(self) -> bool:
        """Check if key manager is enabled (config file exists)."""
        return self.config is not None and len(self.config.keys) > 0

    def _categorize_model(self, model: str) -> str:
        """Determine if model is 'standard' or 'mini'.
        
        Args:
            model: Model name (e.g., "gpt-5.4", "gpt-5.4-mini")
            
        Returns:
            Category: "standard" or "mini"
        """
        if not self.config:
            return "standard"

        model_lower = model.lower()
        
        # Check mini patterns first (more specific)
        # This ensures "gpt-5.4-mini" matches "mini" before "standard"
        if "mini" in self.config.model_categories:
            for pattern in self.config.model_categories["mini"]:
                pattern_lower = pattern.lower()
                if pattern_lower in model_lower:
                    return "mini"
        
        # Then check standard patterns
        if "standard" in self.config.model_categories:
            for pattern in self.config.model_categories["standard"]:
                pattern_lower = pattern.lower()
                if pattern_lower in model_lower:
                    return "standard"
        
        # Check any other categories
        for category, patterns in self.config.model_categories.items():
            if category in ("mini", "standard"):
                continue  # Already checked
            for pattern in patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in model_lower:
                    return category

        # Default to standard if no match
        return "standard"

    def _check_and_reset_daily(self):
        """Reset daily counters if date has changed (UTC timezone)."""
        if not self.config:
            return

        from datetime import datetime, timezone
        
        # Use UTC time so reset happens at midnight UTC (5:30 AM IST)
        today = datetime.now(timezone.utc).date().isoformat()
        changed = False

        for key in self.config.keys:
            for category, limits in key.limits.items():
                if limits.last_reset != today:
                    limits.used_today = 0
                    limits.last_reset = today
                    changed = True

        if changed:
            self._save_config()

    def _get_available_keys(self, category: str) -> list[ApiKeyConfig]:
        """Get keys that haven't exceeded their limit for the category."""
        if not self.config:
            return []

        self._check_and_reset_daily()

        available = []
        for key in self.config.keys:
            if not key.enabled:
                continue

            limits = key.limits.get(category)
            if limits and limits.used_today < limits.daily_limit:
                available.append(key)

        return available

    def _select_key_least_used(self, keys: list[ApiKeyConfig], category: str) -> Optional[ApiKeyConfig]:
        """Select key with least usage in the category."""
        if not keys:
            return None

        return min(keys, key=lambda k: k.limits[category].used_today)

    def _select_key_round_robin(self, keys: list[ApiKeyConfig]) -> Optional[ApiKeyConfig]:
        """Select key using round-robin strategy."""
        if not keys or not self.config:
            return None

        # Find next key in rotation
        key_names = [k.name for k in keys]
        start_idx = self.config.last_used_index

        for i in range(len(self.config.keys)):
            idx = (start_idx + i) % len(self.config.keys)
            key = self.config.keys[idx]
            if key.name in key_names:
                self.config.last_used_index = (idx + 1) % len(self.config.keys)
                self._save_config()
                return key

        return keys[0]

    def _select_key_random(self, keys: list[ApiKeyConfig]) -> Optional[ApiKeyConfig]:
        """Select random key."""
        if not keys:
            return None
        return random.choice(keys)

    def get_key_for_model(self, model: str) -> Optional[str]:
        """Get appropriate API key for the model.

        Args:
            model: Model name (e.g., "gpt-5.4", "gpt-5.4-mini")

        Returns:
            API key string, or None if key manager is disabled
        """
        if not self.is_enabled():
            return None

        category = self._categorize_model(model)
        available_keys = self._get_available_keys(category)

        if not available_keys:
            raise RuntimeError(
                f"No available API keys for {category} models. "
                f"All keys have exceeded their daily limits. "
                f"Use 'vbagent keys list' to check usage."
            )

        # Select key based on strategy
        strategy = self.config.rotation_strategy if self.config else "least_used"

        if strategy == "least_used":
            selected = self._select_key_least_used(available_keys, category)
        elif strategy == "round_robin":
            selected = self._select_key_round_robin(available_keys)
        elif strategy == "random":
            selected = self._select_key_random(available_keys)
        else:
            selected = available_keys[0]

        if selected:
            self.current_key_name = selected.name
            return selected.api_key

        return None

    def track_usage(self, model: str, tokens: int, key_name: Optional[str] = None):
        """Record token usage for a key.

        Args:
            model: Model name used
            tokens: Number of tokens consumed
            key_name: Key name (uses current_key_name if not provided)
        """
        if not self.is_enabled():
            return

        key_name = key_name or self.current_key_name
        if not key_name:
            return

        category = self._categorize_model(model)
        self._check_and_reset_daily()

        # Find the key and update usage
        for key in self.config.keys:
            if key.name == key_name:
                if category in key.limits:
                    key.limits[category].used_today += tokens
                    self._save_config()
                break

    def get_usage_summary(self) -> dict:
        """Get usage statistics for all keys.

        Returns:
            Dictionary with usage stats per key and category
        """
        if not self.is_enabled():
            return {}

        self._check_and_reset_daily()

        summary = {}
        for key in self.config.keys:
            summary[key.name] = {
                "enabled": key.enabled,
                "categories": {},
            }

            for category, limits in key.limits.items():
                remaining = limits.daily_limit - limits.used_today
                percentage = (limits.used_today / limits.daily_limit * 100) if limits.daily_limit > 0 else 0

                summary[key.name]["categories"][category] = {
                    "used": limits.used_today,
                    "limit": limits.daily_limit,
                    "remaining": remaining,
                    "percentage": percentage,
                    "last_reset": limits.last_reset,
                }

        return summary

    def reset_daily_usage(self):
        """Manually reset all daily usage counters."""
        if not self.is_enabled():
            return

        from datetime import datetime, timezone
        
        # Use UTC time
        today = datetime.now(timezone.utc).date().isoformat()
        for key in self.config.keys:
            for limits in key.limits.values():
                limits.used_today = 0
                limits.last_reset = today

        self._save_config()

    def add_key(
        self,
        name: str,
        api_key: str,
        standard_limit: int = 1_000_000,
        mini_limit: int = 2_000_000,
    ):
        """Add a new API key.

        Args:
            name: Friendly name for the key
            api_key: OpenAI API key
            standard_limit: Daily token limit for standard models
            mini_limit: Daily token limit for mini models
        """
        if not self.config:
            self.config = KeyManagerConfig()

        # Check if key name already exists
        for key in self.config.keys:
            if key.name == name:
                raise ValueError(f"Key with name '{name}' already exists")

        new_key = ApiKeyConfig(
            name=name,
            api_key=api_key,
            limits={
                "standard": CategoryLimits(daily_limit=standard_limit),
                "mini": CategoryLimits(daily_limit=mini_limit),
            },
        )

        self.config.keys.append(new_key)
        self._save_config()

    def update_limits(self, name: str, standard_limit: Optional[int] = None, mini_limit: Optional[int] = None):
        """Update limits for an existing key.

        Args:
            name: Key name
            standard_limit: New daily limit for standard models (optional)
            mini_limit: New daily limit for mini models (optional)
        """
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        for key in self.config.keys:
            if key.name == name:
                if standard_limit is not None:
                    key.limits["standard"].daily_limit = standard_limit
                if mini_limit is not None:
                    key.limits["mini"].daily_limit = mini_limit
                self._save_config()
                return

        raise ValueError(f"Key '{name}' not found")

    def enable_key(self, name: str):
        """Enable a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        for key in self.config.keys:
            if key.name == name:
                key.enabled = True
                self._save_config()
                return

        raise ValueError(f"Key '{name}' not found")

    def disable_key(self, name: str):
        """Disable a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        for key in self.config.keys:
            if key.name == name:
                key.enabled = False
                self._save_config()
                return

        raise ValueError(f"Key '{name}' not found")

    def remove_key(self, name: str):
        """Remove a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        self.config.keys = [k for k in self.config.keys if k.name != name]
        self._save_config()
