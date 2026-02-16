"""Tests for configuration system."""

import pytest
from vbagent.config import (
    VBAgentConfig,
    AgentModelConfig,
    _migrate_flat_to_hierarchical,
    ClassificationConfig,
    ContentGenerationConfig,
    DiagramConfig,
    VariantsConfig,
    QualityConfig,
)


def test_agent_model_config_creation():
    """Test creating AgentModelConfig."""
    config = AgentModelConfig(
        model="gpt-5.2",
        reasoning_effort="high",
        max_tokens=1000
    )
    assert config.model == "gpt-5.2"
    assert config.reasoning_effort == "high"
    assert config.max_tokens == 1000


def test_agent_model_config_to_dict():
    """Test converting AgentModelConfig to dict."""
    config = AgentModelConfig(model="gpt-5.2", reasoning_effort="medium")
    d = config.to_dict()
    assert d["model"] == "gpt-5.2"
    assert d["reasoning_effort"] == "medium"


def test_agent_model_config_from_dict():
    """Test creating AgentModelConfig from dict."""
    data = {"model": "gpt-5.1", "reasoning_effort": "low", "max_tokens": 500}
    config = AgentModelConfig.from_dict(data)
    assert config.model == "gpt-5.1"
    assert config.reasoning_effort == "low"
    assert config.max_tokens == 500


def test_hierarchical_config_creation():
    """Test creating hierarchical config structures."""
    classification = ClassificationConfig()
    assert hasattr(classification, "image_classifier")
    assert hasattr(classification, "taxonomy_classifier")
    
    content_gen = ContentGenerationConfig()
    assert hasattr(content_gen, "scanner")
    assert hasattr(content_gen, "idea")
    
    diagram = DiagramConfig()
    assert hasattr(diagram, "tikz")
    assert hasattr(diagram, "fbd")
    
    variants = VariantsConfig()
    assert hasattr(variants, "variant")
    assert hasattr(variants, "multi_context")
    
    quality = QualityConfig()
    assert hasattr(quality, "reviewer")
    assert hasattr(quality, "latex_fixer")


def test_vbagent_config_creation():
    """Test creating VBAgentConfig with hierarchical structure."""
    config = VBAgentConfig()
    assert config.default_model == "gpt-5.2"
    assert config.subject == "physics"
    assert hasattr(config, "classification")
    assert hasattr(config, "content_generation")
    assert hasattr(config, "diagram")
    assert hasattr(config, "variants")
    assert hasattr(config, "quality")


def test_migration_flat_to_hierarchical():
    """Test migrating old flat config to hierarchical."""
    old_config = {
        "default_model": "gpt-5.2",
        "agents": {
            "scanner": {"model": "gpt-5.2", "reasoning_effort": "medium"},
            "tikz": {"model": "gpt-5.1-codex", "reasoning_effort": "high"},
            "reviewer": {"model": "gpt-5.2", "reasoning_effort": "high"},
        }
    }
    
    migrated = _migrate_flat_to_hierarchical(old_config)
    
    # Check hierarchical structure was created
    assert "content_generation" in migrated
    assert "scanner" in migrated["content_generation"]
    assert migrated["content_generation"]["scanner"]["model"] == "gpt-5.2"
    
    assert "diagram" in migrated
    assert "tikz" in migrated["diagram"]
    assert migrated["diagram"]["tikz"]["model"] == "gpt-5.1-codex"
    
    assert "quality" in migrated
    assert "reviewer" in migrated["quality"]
    assert migrated["quality"]["reviewer"]["model"] == "gpt-5.2"
    
    # Old agents key should still be present for backward compatibility
    assert "agents" in migrated


def test_migration_already_hierarchical():
    """Test that migration doesn't break already hierarchical config."""
    hierarchical_config = {
        "default_model": "gpt-5.2",
        "content_generation": {
            "scanner": {"model": "gpt-5.2", "reasoning_effort": "medium"}
        }
    }
    
    migrated = _migrate_flat_to_hierarchical(hierarchical_config)
    
    # Should return unchanged
    assert migrated == hierarchical_config


def test_config_from_dict_with_old_format():
    """Test loading config from old flat format."""
    old_config = {
        "default_model": "gpt-5.2",
        "subject": "physics",
        "agents": {
            "scanner": {"model": "gpt-5.2", "reasoning_effort": "medium"},
            "tikz": {"model": "gpt-5.1-codex", "reasoning_effort": "high"},
        }
    }
    
    config = VBAgentConfig.from_dict(old_config)
    
    # Check hierarchical access works
    assert config.content_generation.scanner.model == "gpt-5.2"
    assert config.diagram.tikz.model == "gpt-5.1-codex"


def test_config_from_dict_with_new_format():
    """Test loading config from new hierarchical format."""
    new_config = {
        "default_model": "gpt-5.2",
        "subject": "physics",
        "content_generation": {
            "scanner": {"model": "gpt-5.2", "reasoning_effort": "medium"}
        },
        "diagram": {
            "tikz": {"model": "gpt-5.1-codex", "reasoning_effort": "high"}
        }
    }
    
    config = VBAgentConfig.from_dict(new_config)
    
    # Check hierarchical access works
    assert config.content_generation.scanner.model == "gpt-5.2"
    assert config.diagram.tikz.model == "gpt-5.1-codex"


def test_get_model_flat_path():
    """Test get_model with flat agent type (backward compatibility)."""
    config = VBAgentConfig()
    config.scanner.model = "gpt-5.2"
    
    assert config.get_model("scanner") == "gpt-5.2"


def test_get_model_hierarchical_path():
    """Test get_model with hierarchical path."""
    config = VBAgentConfig()
    config.content_generation.scanner.model = "gpt-5.2"
    
    assert config.get_model("content_generation.scanner") == "gpt-5.2"


def test_get_model_settings_flat_path():
    """Test get_model_settings with flat agent type."""
    config = VBAgentConfig()
    config.scanner.model = "gpt-5.2"
    config.scanner.reasoning_effort = "medium"
    
    settings = config.get_model_settings("scanner")
    assert settings is not None


def test_get_model_settings_hierarchical_path():
    """Test get_model_settings with hierarchical path."""
    config = VBAgentConfig()
    config.content_generation.scanner.model = "gpt-5.2"
    config.content_generation.scanner.reasoning_effort = "medium"
    
    settings = config.get_model_settings("content_generation.scanner")
    assert settings is not None


def test_backward_compatibility_old_agent_names():
    """Test that old agent names are migrated correctly."""
    old_config = {
        "agents": {
            "compile_fixer": {"model": "gpt-5.2", "reasoning_effort": "low"},
            "multi_variant": {"model": "gpt-5.2", "reasoning_effort": "high"},
        }
    }
    
    migrated = _migrate_flat_to_hierarchical(old_config)
    
    # Old names should be mapped to new names
    assert "quality" in migrated
    assert "latex_fixer" in migrated["quality"]
    
    assert "variants" in migrated
    assert "multi_context" in migrated["variants"]


def test_config_to_dict():
    """Test converting config to dict."""
    config = VBAgentConfig()
    config.content_generation.scanner.model = "gpt-5.2"
    
    d = config.to_dict()
    assert "default_model" in d
    assert "subject" in d
    assert "agents" in d
