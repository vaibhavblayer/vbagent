"""API key manager for rotation and usage tracking."""

from __future__ import annotations

import fcntl
import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from vbagent.api_keys.models import ApiKeyConfig, CategoryLimits, KeyManagerConfig


@dataclass(frozen=True)
class KeySelection:
    """One managed profile selected for a request."""

    api_key: str
    key_name: str
    cache_domain: str


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
        self._load_error: str | None = None
        self._selection_lock = threading.Lock()
        self._inflight_by_name: dict[str, int] = {}
        self._unavailable_until: dict[str, float] = {}
        self._load_config()

    @classmethod
    def get_instance(cls) -> KeyManager:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_config(self):
        """Load configuration from file (no lock — use _locked_read for safe reads)."""
        self._load_error = None
        if not self._config_path.exists():
            self.config = None
            return

        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
            original_categories = data.get("model_categories")
            self.config = KeyManagerConfig(**data)
            if original_categories != self.config.model_categories:
                # Persist the compatibility normalization (for example,
                # moving gpt-5.6-terra from standard to mini) so subsequent
                # processes observe the same routing without relying on
                # in-memory defaults.
                self._locked_update(lambda _config: None)
        except Exception as e:
            print(f"Warning: Failed to load API key config: {e}")
            self._load_error = str(e)
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

    def is_configured(self) -> bool:
        """Return whether an API-profile configuration file is present."""
        return self.config is not None or self._config_path.exists()

    def has_profile(self, name: str | None) -> bool:
        """Return whether *name* belongs to the managed configuration."""
        return bool(
            name
            and self.config
            and any(key.name == name for key in self.config.keys)
        )

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

    def _get_available_keys(
        self,
        category: str,
        *,
        excluded_names: Iterable[str] = (),
    ) -> list[ApiKeyConfig]:
        """Get keys that haven't exceeded their limit for the category."""
        if not self.config:
            return []

        self._check_and_reset_daily()

        excluded = set(excluded_names)
        now = time.monotonic()
        unavailable = getattr(self, "_unavailable_until", {})
        available = []
        for key in self.config.keys:
            if not key.enabled or key.name in excluded:
                continue
            if unavailable.get(key.name, 0.0) > now:
                continue

            limits = key.limits.get(category)
            if limits and limits.used_today < limits.daily_limit:
                available.append(key)

        return available

    def _select_key_least_used(self, keys: list[ApiKeyConfig], category: str) -> Optional[ApiKeyConfig]:
        """Select key with least usage in the category."""
        if not keys:
            return None

        inflight = getattr(self, "_inflight_by_name", {})
        return min(
            keys,
            key=lambda key: (
                key.limits[category].used_today,
                inflight.get(key.name, 0),
                key.name,
            ),
        )

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

    def _select_key_affinity(
        self,
        keys: list[ApiKeyConfig],
        affinity_key: str,
    ) -> Optional[ApiKeyConfig]:
        """Map a stable request group to a cache domain with rendezvous hashing.

        Profiles without an explicit domain are deliberately isolated. Adding
        or removing an unrelated domain therefore remaps only the groups that
        rendezvous hashing assigns to that changed domain.
        """
        if not keys:
            return None

        by_domain: dict[str, list[ApiKeyConfig]] = {}
        for key in keys:
            by_domain.setdefault(key.effective_cache_domain, []).append(key)
        domain = max(
            by_domain,
            key=lambda candidate: hashlib.sha256(
                f"{affinity_key}\0{candidate}".encode("utf-8")
            ).digest(),
        )
        return sorted(by_domain[domain], key=lambda key: key.name)[0]

    def _select_with_strategy(
        self,
        keys: list[ApiKeyConfig],
        category: str,
    ) -> Optional[ApiKeyConfig]:
        """Apply the configured rotation strategy to one cache domain."""
        strategy = self.config.rotation_strategy if self.config else "least_used"
        if strategy == "least_used":
            return self._select_key_least_used(keys, category)
        if strategy == "round_robin":
            return self._select_key_round_robin(keys)
        if strategy == "random":
            return self._select_key_random(keys)
        return keys[0] if keys else None

    def _ensure_runtime_state(self) -> None:
        """Initialize process-local routing state for normal and test instances."""
        if not hasattr(self, "_selection_lock"):
            self._selection_lock = threading.Lock()
        if not hasattr(self, "_inflight_by_name"):
            self._inflight_by_name = {}
        if not hasattr(self, "_unavailable_until"):
            self._unavailable_until = {}

    def select_key_for_model(
        self,
        model: str,
        affinity_key: Optional[str] = None,
        *,
        excluded_names: Iterable[str] = (),
        reserve: bool = False,
    ) -> KeySelection:
        """Select a managed profile and return its cache-domain metadata.

        An affinity key first chooses an OpenAI cache domain. Rotation then
        occurs only among profiles explicitly declared to share that domain.
        This keeps cache reuse valid across same-domain key rotation while
        treating legacy profiles as isolated by default.
        """
        if getattr(self, "_load_error", None):
            raise RuntimeError(
                "API key configuration exists but could not be loaded; "
                "fix it before making provider requests"
            )
        if not self.is_enabled():
            raise RuntimeError("API key manager has no configured profiles")

        self._ensure_runtime_state()
        category = self._categorize_model(model)
        with self._selection_lock:
            available_keys = self._get_available_keys(
                category,
                excluded_names=excluded_names,
            )
            if not available_keys:
                raise RuntimeError(
                    f"No available API profiles for {category} models. "
                    "Profiles may be disabled, over their daily limit, or in "
                    "provider cooldown. Use 'vbagent keys list' to inspect them."
                )

            candidates = available_keys
            if affinity_key:
                domain_key = self._select_key_affinity(available_keys, affinity_key)
                if domain_key is not None:
                    candidates = [
                        key
                        for key in available_keys
                        if key.effective_cache_domain
                        == domain_key.effective_cache_domain
                    ]

            selected = self._select_with_strategy(candidates, category)
            if selected is None:
                raise RuntimeError(f"No API profile could be selected for {model}")

            if reserve:
                self._inflight_by_name[selected.name] = (
                    self._inflight_by_name.get(selected.name, 0) + 1
                )
            self.current_key_name = selected.name
            return KeySelection(
                api_key=selected.api_key,
                key_name=selected.name,
                cache_domain=selected.effective_cache_domain,
            )

    def get_key_for_model(
        self,
        model: str,
        affinity_key: Optional[str] = None,
    ) -> Optional[str]:
        """Get appropriate API key for the model.

        Args:
            model: Model name (e.g., "gpt-5.4", "gpt-5.4-mini")
            affinity_key: Stable cache/request group. When supplied, requests
                in the same group reuse one available profile so provider-side
                prompt caches remain reachable across calls.

        Returns:
            API key string, or None if key manager is disabled
        """
        if not self.is_configured():
            return None
        return self.select_key_for_model(
            model,
            affinity_key=affinity_key,
        ).api_key

    def release_profile(self, name: str | None) -> None:
        """Release one process-local in-flight reservation."""
        if not name:
            return
        self._ensure_runtime_state()
        with self._selection_lock:
            current = self._inflight_by_name.get(name, 0)
            if current <= 1:
                self._inflight_by_name.pop(name, None)
            else:
                self._inflight_by_name[name] = current - 1

    def mark_profile_unavailable(self, name: str, cooldown_seconds: float) -> None:
        """Temporarily exclude a profile after a terminal provider response."""
        self._ensure_runtime_state()
        with self._selection_lock:
            self._unavailable_until[name] = max(
                self._unavailable_until.get(name, 0.0),
                time.monotonic() + max(0.0, cooldown_seconds),
            )

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
                "cache_domain": key.effective_cache_domain,
                "cache_domain_declared": key.cache_domain is not None,
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
        cache_domain: str | None = None,
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
            cache_domain=cache_domain,
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

    def update_limits(
        self,
        name: str,
        standard_limit: Optional[int] = None,
        mini_limit: Optional[int] = None,
        cache_domain: str | None = None,
        *,
        update_cache_domain: bool = False,
    ):
        """Update limits and, when requested, the cache domain for a key."""
        if not self.is_enabled():
            raise RuntimeError("Key manager not enabled")

        def _update(config: KeyManagerConfig):
            for key in config.keys:
                if key.name == name:
                    if standard_limit is not None:
                        key.limits["standard"].daily_limit = standard_limit
                    if mini_limit is not None:
                        key.limits["mini"].daily_limit = mini_limit
                    if update_cache_domain:
                        key.cache_domain = cache_domain.strip() if cache_domain else None
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
