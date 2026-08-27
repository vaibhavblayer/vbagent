"""CLI coverage for safe prompt-cache profile domains."""

import json

from click.testing import CliRunner

from vbagent.api_keys.manager import KeyManager
from vbagent.cli.keys import keys


def _manager(tmp_path, monkeypatch) -> KeyManager:
    config_path = tmp_path / "api_keys.json"
    lock_path = tmp_path / "api_keys.lock"
    monkeypatch.setattr(KeyManager, "_config_path", config_path)
    monkeypatch.setattr(KeyManager, "_lock_path", lock_path)
    manager = KeyManager()
    monkeypatch.setattr(
        KeyManager,
        "get_instance",
        classmethod(lambda cls: manager),
    )
    return manager


def test_add_and_list_declared_cache_domain(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)

    added = CliRunner().invoke(
        keys,
        [
            "add",
            "--name",
            "profile-a",
            "--api-key",
            "secret-a",
            "--cache-domain",
            "org-main:global",
        ],
    )
    listed = CliRunner().invoke(keys, ["list"])

    assert added.exit_code == 0, added.output
    assert listed.exit_code == 0, listed.output
    assert "org-main:global" in listed.output
    saved = json.loads(manager._config_path.read_text())
    assert saved["keys"][0]["cache_domain"] == "org-main:global"


def test_update_can_restore_profile_isolation(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.add_key(
        "profile-a",
        "secret-a",
        cache_domain="org-main:global",
    )

    updated = CliRunner().invoke(
        keys,
        ["update", "profile-a", "--isolated-cache"],
    )
    listed = CliRunner().invoke(keys, ["list"])

    assert updated.exit_code == 0, updated.output
    assert "profile:profile-a (isolated)" in listed.output
    saved = json.loads(manager._config_path.read_text())
    assert saved["keys"][0]["cache_domain"] is None
