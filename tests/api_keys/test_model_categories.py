"""Tests for current Sol/Terra/Luna API-key quota routing."""

from vbagent.api_keys.manager import KeyManager
from vbagent.api_keys.models import KeyManagerConfig


def test_current_model_defaults_keep_sol_standard_and_terra_luna_mini():
    config = KeyManagerConfig()
    manager = KeyManager.__new__(KeyManager)
    manager.config = config

    assert manager._categorize_model("gpt-5.6-sol") == "standard"
    assert manager._categorize_model("gpt-5.6-terra") == "mini"
    assert manager._categorize_model("gpt-5.6-luna") == "mini"


def test_legacy_model_category_mapping_is_normalized():
    config = KeyManagerConfig(
        model_categories={
            "standard": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6"],
            "mini": ["gpt-5.6-luna"],
        }
    )

    assert "gpt-5.6-terra" not in config.model_categories["standard"]
    assert "gpt-5.6-terra" in config.model_categories["mini"]
    assert "gpt-5.6-luna" in config.model_categories["mini"]
    assert "gpt-5.6-sol" in config.model_categories["standard"]


def test_legacy_mapping_is_persisted_when_manager_loads(tmp_path, monkeypatch):
    import json

    config_path = tmp_path / "api_keys.json"
    lock_path = tmp_path / "api_keys.lock"
    config_path.write_text(json.dumps({
        "keys": [],
        "model_categories": {
            "standard": ["gpt-5.6-sol", "gpt-5.6-terra"],
            "mini": ["gpt-5.6-luna"],
        },
    }))
    monkeypatch.setattr(KeyManager, "_config_path", config_path)
    monkeypatch.setattr(KeyManager, "_lock_path", lock_path)

    KeyManager()
    saved = json.loads(config_path.read_text())

    assert "gpt-5.6-terra" not in saved["model_categories"]["standard"]
    assert "gpt-5.6-terra" in saved["model_categories"]["mini"]
