"""Tests for configuration system."""

import pytest
from vbagent.config import (
    VBAgentConfig,
    AgentModelConfig,
)


def test_agent_model_config_creation():
    """Test creating AgentModelConfig."""
    config = AgentModelConfig(
        model="gpt-5.4-mini",
        reasoning_effort="high",
        max_tokens=1000
    )
    assert config.model == "gpt-5.4-mini"
    assert config.reasoning_effort == "high"
    assert config.max_tokens == 1000


def test_agent_model_config_to_dict():
    """Test converting AgentModelConfig to dict."""
    config = AgentModelConfig(model="gpt-5.4-mini", reasoning_effort="medium")
    d = config.to_dict()
    assert d["model"] == "gpt-5.4-mini"
    assert d["reasoning_effort"] == "medium"


def test_agent_model_config_from_dict():
    """Test creating AgentModelConfig from dict."""
    data = {"model": "gpt-5.1", "reasoning_effort": "low", "max_tokens": 500}
    config = AgentModelConfig.from_dict(data)
    assert config.model == "gpt-5.1"
    assert config.reasoning_effort == "low"
    assert config.max_tokens == 500


def test_vbagent_config_creation():
    """Test creating VBAgentConfig with simplified structure."""
    config = VBAgentConfig()
    assert config.default_model == "gpt-5.4-mini"
    assert config.subject == "physics"
    assert isinstance(config.agents, dict)
    # Check smart defaults were applied
    assert "classifier" in config.agents
    assert config.agents["classifier"].model == "gpt-5.4-mini"
    assert config.agents["classifier"].reasoning_effort == "low"


def test_config_from_dict():
    """Test loading config from dict."""
    config_data = {
        "default_model": "gpt-5.4-mini",
        "subject": "physics",
        "agents": {
            "scanner": {"model": "gpt-5.4-mini", "reasoning_effort": "medium"},
            "tikz": {"model": "gpt-5.1-codex", "reasoning_effort": "high"},
        }
    }
    
    config = VBAgentConfig.from_dict(config_data)
    
    # Check agent configs
    assert config.agents["scanner"].model == "gpt-5.4-mini"
    assert config.agents["tikz"].model == "gpt-5.1-codex"


def test_get_agent_config():
    """Test getting agent config with fallback to defaults."""
    config = VBAgentConfig()
    config.agents["scanner"] = AgentModelConfig(model="gpt-5.4-mini", reasoning_effort="medium")
    
    # Existing agent
    scanner_cfg = config.get_agent_config("scanner")
    assert scanner_cfg.model == "gpt-5.4-mini"
    
    # Non-existing agent (should return default)
    unknown_cfg = config.get_agent_config("unknown_agent")
    assert unknown_cfg.model == config.default_model
    assert unknown_cfg.reasoning_effort == config.default_reasoning_effort


def test_get_model():
    """Test get_model method."""
    config = VBAgentConfig()
    config.agents["scanner"] = AgentModelConfig(model="gpt-5.4-mini")
    
    assert config.get_model("scanner") == "gpt-5.4-mini"


def test_config_to_dict():
    """Test converting config to dict."""
    config = VBAgentConfig()
    config.agents["scanner"] = AgentModelConfig(model="gpt-5.4-mini", reasoning_effort="medium")
    
    d = config.to_dict()
    assert "default_model" in d
    assert "subject" in d
    assert "agents" in d
    assert "scanner" in d["agents"]
    assert d["agents"]["scanner"]["model"] == "gpt-5.4-mini"


def test_merge_with():
    """Test merging configs (workspace overrides global)."""
    global_config = VBAgentConfig()
    global_config.default_model = "gpt-5.1"
    global_config.agents["scanner"] = AgentModelConfig(model="gpt-5.1")
    
    workspace_config = VBAgentConfig()
    workspace_config.default_model = "gpt-5.4-mini"
    workspace_config.agents["scanner"] = AgentModelConfig(model="gpt-5.4-mini")
    workspace_config.agents["tikz"] = AgentModelConfig(model="gpt-5.1-codex")
    
    merged = global_config.merge_with(workspace_config)
    
    # Workspace values should override
    assert merged.default_model == "gpt-5.4-mini"
    assert merged.agents["scanner"].model == "gpt-5.4-mini"
    assert merged.agents["tikz"].model == "gpt-5.1-codex"
