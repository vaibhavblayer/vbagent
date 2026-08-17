"""Tests for cache-aware API profile selection."""

from vbagent.api_keys.manager import KeyManager
from vbagent.api_keys.models import ApiKeyConfig


def _keys() -> list[ApiKeyConfig]:
    return [
        ApiKeyConfig(name="profile-a", api_key="secret-a"),
        ApiKeyConfig(name="profile-b", api_key="secret-b"),
        ApiKeyConfig(name="profile-c", api_key="secret-c"),
    ]


def test_affinity_selection_is_stable_for_same_group():
    manager = KeyManager.__new__(KeyManager)
    keys = _keys()

    first = manager._select_key_affinity(keys, "question-classifier:physics")
    second = manager._select_key_affinity(keys, "question-classifier:physics")

    assert first is second


def test_affinity_selection_remaps_when_profile_is_unavailable():
    manager = KeyManager.__new__(KeyManager)
    keys = _keys()
    selected = manager._select_key_affinity(keys, "question-classifier:physics")

    available = [key for key in keys if key is not selected]
    replacement = manager._select_key_affinity(
        available,
        "question-classifier:physics",
    )

    assert replacement in available
    assert replacement is not selected
