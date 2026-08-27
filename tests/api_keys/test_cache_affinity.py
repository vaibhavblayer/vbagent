"""Tests for cache-aware API profile selection."""

from vbagent.api_keys.manager import KeyManager
from vbagent.api_keys.models import ApiKeyConfig, KeyManagerConfig


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


def _manager(keys: list[ApiKeyConfig]) -> KeyManager:
    manager = KeyManager.__new__(KeyManager)
    manager.config = KeyManagerConfig(keys=keys, rotation_strategy="least_used")
    manager.current_key_name = None
    manager._ensure_runtime_state()
    return manager


def test_legacy_profiles_are_cache_isolated_by_default():
    keys = _keys()

    assert [key.effective_cache_domain for key in keys] == [
        "profile:profile-a",
        "profile:profile-b",
        "profile:profile-c",
    ]


def test_rotation_within_declared_domain_preserves_cache_scope():
    keys = [
        ApiKeyConfig(
            name=f"profile-{suffix}",
            api_key=f"secret-{suffix}",
            cache_domain="org-main:global",
        )
        for suffix in ("a", "b", "c")
    ]
    manager = _manager(keys)

    selections = [
        manager.select_key_for_model(
            "gpt-5.6-sol",
            affinity_key="syllabus-draft",
            reserve=True,
        )
        for _ in range(3)
    ]

    assert {selection.key_name for selection in selections} == {
        "profile-a",
        "profile-b",
        "profile-c",
    }
    assert {selection.cache_domain for selection in selections} == {
        "org-main:global"
    }
    for selection in selections:
        manager.release_profile(selection.key_name)


def test_rendezvous_hashing_does_not_remap_unaffected_domains():
    keys = _keys()
    manager = _manager(keys)
    groups = [f"authoring-group-{index}" for index in range(200)]
    before = {
        group: manager._select_key_affinity(keys, group).effective_cache_domain
        for group in groups
    }

    removed_domain = "profile:profile-c"
    remaining = [
        key for key in keys if key.effective_cache_domain != removed_domain
    ]
    after = {
        group: manager._select_key_affinity(remaining, group).effective_cache_domain
        for group in groups
    }

    assert any(domain == removed_domain for domain in before.values())
    assert all(
        after[group] == domain
        for group, domain in before.items()
        if domain != removed_domain
    )


def test_excluding_failed_profile_uses_peer_in_same_cache_domain():
    keys = [
        ApiKeyConfig(
            name="profile-a",
            api_key="secret-a",
            cache_domain="org-main:global",
        ),
        ApiKeyConfig(
            name="profile-b",
            api_key="secret-b",
            cache_domain="org-main:global",
        ),
    ]
    manager = _manager(keys)
    first = manager.select_key_for_model(
        "gpt-5.6-sol",
        affinity_key="classifier",
    )
    second = manager.select_key_for_model(
        "gpt-5.6-sol",
        affinity_key="classifier",
        excluded_names={first.key_name},
    )

    assert first.key_name != second.key_name
    assert first.cache_domain == second.cache_domain == "org-main:global"
