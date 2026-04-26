"""API key manager for rotation and usage tracking."""

from __future__ import annotations

import fcntl
import json
import random
from datetime import date
from pathlib import Path
from typing import Optional

from vbagent.api_keys.models import KeyManagerConfig, ApiKeyConfig, CategoryLimits


class KeyManager:
    """Manages multiple API keys with usage tracking and rotation.
    
    Uses file locking (fcntl.flock) to prevent race conditions when
    multiple processes track usage concurrently.
    """

    _instance: Optional[KeyManager] = None
    _config_path = Path.home() / ".config" / "vbagent" / "api_keys.json"
    _lock_path = Path.home() / ".config" / "vbagent" / "api_keys.lock"

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
        """Load configuration from file (no lock — use _locked_read for safe reads)."""
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
        """Save configuration to file (no lock — use _locked_update for safe writes)."""
        if self.config is None:
            return

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    def _locked_update(self, updater):
        """Atomically read-modify-write the config file with file locking.
        
        Args:
            updater: Callable that receives the KeyManagerConfig and mutates it.
                     Called while the lock is held.
        """
        if self.config is None:
            return

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._lock_path, "w") as lock_file:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                # Re-read the latest state from disk (another process may have written)
                if self._config_path.exists():
                    with open(self._config_path, "r") as f:
                        data = json.load(f)
                    self.config = KeyManagerConfig(**data)

                # Apply the mutation
                updater(self.config)

                # Write back
                with open(self._config_path, "w") as f:
                    json.dump(self.config.model_dump(), f, indent=2)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

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
        """Reset daily counters if date has changed (UTC timezone).
        
        5:30 AM IST = midnight UTC — counters reset at this boundary.
        """
        if not self.config:
            return

        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()

        # Quick check on in-memory config — if no reset needed, skip the lock
        needs_reset = False
        for key in self.config.keys:
            for category, limits in key.limits.items():
                if limits.last_reset != today:
                    needs_reset = True
                    break
            if needs_reset:
                break

        if not needs_reset:
            return

        # Apply reset under lock (re-reads from disk first)
        def _do_reset(config: KeyManagerConfig):
            utc_today = datetime.now(timezone.utc).date().isoformat()
            for key in config.keys:
                for category, limits in key.limits.items():
                    if limits.last_reset != utc_today:
                        limits.used_today = 0
                        limits.last_reset = utc_today

        self._locked_update(_do_reset)

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

        selected = None
        for i in range(len(self.config.keys)):
            idx = (start_idx + i) % len(self.config.keys)
            key = self.config.keys[idx]
            if key.name in key_names:
                next_idx = (idx + 1) % len(self.config.keys)
                selected = key

                def _update_rr(config: KeyManagerConfig, new_idx=next_idx):
                    config.last_used_index = new_idx

                self._locked_update(_update_rr)
                return selected

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

        Uses file locking to prevent race conditions across processes.

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

        def _apply_usage(config: KeyManagerConfig):
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date().isoformat()

            for key in config.keys:
                if key.name == key_name:
                    if category in key.limits:
                        # Reset if date changed
                        if key.limits[category].last_reset != today:
                            key.limits[category].used_today = 0
                            key.limits[category].last_reset = today
                        key.limits[category].used_today += tokens
                    break

        self._locked_update(_apply_usage)

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

        def _reset(config: KeyManagerConfig):
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date().isoformat()
            for key in config.keys:
                for limits in key.limits.values():
                    limits.used_today = 0
                    limits.last_reset = today

        self._locked_update(_reset)

    def add_key(
        self,
        name: str,
        api_key: str,
        standard_limit: int = 1_000_000,
        mini_limit: int = 2_000_000,
    ):
        """Add a new API key."""
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

        def _add(config: KeyManagerConfig):
            for key in config.keys:
                if key.name == name:
                    raise ValueError(f"Key with name '{name}' already exists")
            config.keys.append(new_key)

        self._locked_update(_add)

    def update_limits(self, name: str, standard_limit: Optional[int] = None, mini_limit: Optional[int] = None):
        """Update limits for an existing key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        def _update(config: KeyManagerConfig):
            for key in config.keys:
                if key.name == name:
                    if standard_limit is not None:
                        key.limits["standard"].daily_limit = standard_limit
                    if mini_limit is not None:
                        key.limits["mini"].daily_limit = mini_limit
                    return
            raise ValueError(f"Key '{name}' not found")

        self._locked_update(_update)

    def enable_key(self, name: str):
        """Enable a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        def _enable(config: KeyManagerConfig):
            for key in config.keys:
                if key.name == name:
                    key.enabled = True
                    return
            raise ValueError(f"Key '{name}' not found")

        self._locked_update(_enable)

    def disable_key(self, name: str):
        """Disable a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        def _disable(config: KeyManagerConfig):
            for key in config.keys:
                if key.name == name:
                    key.enabled = False
                    return
            raise ValueError(f"Key '{name}' not found")

        self._locked_update(_disable)

    def remove_key(self, name: str):
        """Remove a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        def _remove(config: KeyManagerConfig):
            config.keys = [k for k in config.keys if k.name != name]

        self._locked_update(_remove)
