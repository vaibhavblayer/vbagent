"""Configuration for vbagent agents.

Supports different models for different agent types:
- classifier: Image classification
- scanner: LaTeX extraction from images
- tikz: TikZ diagram generation
- idea: Concept extraction
- alternate: Alternate solution generation
- variant: Problem variant generation
- converter: Format conversion
- reviewer: QA review agent for quality checking

Configuration hierarchy (later overrides earlier):
1. Global config: ~/.config/vbagent/models.json (or %APPDATA%/vbagent on Windows)
2. Workspace config: .vbagent.json in current directory

Use `vbagent init` to create a workspace config from defaults.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# Only import for type checking - avoids heavy runtime import
if TYPE_CHECKING:
    from agents import ModelSettings


def _get_config_dir() -> Path:
    """Get the platform-specific config directory.
    
    Returns:
        Path to config directory:
        - Windows: %APPDATA%/vbagent
        - macOS/Linux: ~/.config/vbagent
    """
    if sys.platform == "win32":
        # Windows: use APPDATA
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "vbagent"
        # Fallback to home directory
        return Path.home() / "AppData" / "Roaming" / "vbagent"
    else:
        # Unix-like: use XDG_CONFIG_HOME or ~/.config
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "vbagent"
        return Path.home() / ".config" / "vbagent"


# Config file locations
CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "models.json"  # Global config
WORKSPACE_CONFIG_FILE = ".vbagent.json"  # Workspace config filename

# Valid subjects
SUBJECTS = ["physics", "chemistry", "mathematics", "biology"]


# Available model presets
MODELS = {
    "gpt-5.2": "gpt-5.2",
    "gpt-5.1": "gpt-5.1",
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5.1-codex": "gpt-5.1-codex",
    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
}

# Agent types
AGENT_TYPES = [
    "classifier",
    "scanner",
    "tikz",
    "tikz_checker",
    "idea",
    "alternate",
    "variant",
    "converter",
    "reviewer",
]


def _get_model_settings_class():
    """Lazy import of ModelSettings to avoid heavy import at module load."""
    from agents import ModelSettings
    return ModelSettings


@dataclass
class AgentModelConfig:
    """Configuration for a specific agent's model settings."""

    model: str = "gpt-5.2"
    reasoning_effort: str = "high"  # low, medium, high
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    def to_model_settings(self) -> "ModelSettings":
        """Convert to ModelSettings for the agent."""
        ModelSettings = _get_model_settings_class()
        settings_dict = {}

        # Add reasoning effort
        settings_dict["reasoning"] = {"effort": self.reasoning_effort}

        # Add optional settings
        if self.temperature is not None:
            settings_dict["temperature"] = self.temperature
        if self.max_tokens is not None:
            settings_dict["max_tokens"] = self.max_tokens

        return ModelSettings(**settings_dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentModelConfig":
        """Create from dictionary."""
        return cls(
            model=data.get("model", "gpt-5.2"),
            reasoning_effort=data.get("reasoning_effort", "high"),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
        )


@dataclass
class VBAgentConfig:
    """Main configuration for all vbagent agents."""

    # Default model for all agents
    default_model: str = "gpt-5.2"
    default_reasoning_effort: str = "high"
    
    # Subject for prompts (physics, chemistry, mathematics, biology)
    subject: str = "physics"

    # Per-agent model overrides
    classifier: AgentModelConfig = field(default_factory=AgentModelConfig)
    scanner: AgentModelConfig = field(default_factory=AgentModelConfig)
    tikz: AgentModelConfig = field(default_factory=AgentModelConfig)
    tikz_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    idea: AgentModelConfig = field(default_factory=AgentModelConfig)
    alternate: AgentModelConfig = field(default_factory=AgentModelConfig)
    variant: AgentModelConfig = field(default_factory=AgentModelConfig)
    converter: AgentModelConfig = field(default_factory=AgentModelConfig)
    reviewer: AgentModelConfig = field(default_factory=AgentModelConfig)

    def get_model(self, agent_type: str) -> str:
        """Get the model for a specific agent type."""
        config = getattr(self, agent_type, None)
        if config and config.model:
            return config.model
        return self.default_model

    def get_model_settings(self, agent_type: str) -> "ModelSettings":
        """Get ModelSettings for a specific agent type."""
        config = getattr(self, agent_type, None)
        if config:
            return config.to_model_settings()
        ModelSettings = _get_model_settings_class()
        return ModelSettings(reasoning={"effort": self.default_reasoning_effort})

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "default_model": self.default_model,
            "default_reasoning_effort": self.default_reasoning_effort,
            "subject": self.subject,
            "agents": {
                agent_type: getattr(self, agent_type).to_dict()
                for agent_type in AGENT_TYPES
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VBAgentConfig":
        """Create from dictionary."""
        config = cls(
            default_model=data.get("default_model", "gpt-5.2"),
            default_reasoning_effort=data.get("default_reasoning_effort", "high"),
            subject=data.get("subject", "physics"),
        )
        agents_data = data.get("agents", {})
        for agent_type in AGENT_TYPES:
            if agent_type in agents_data:
                setattr(
                    config,
                    agent_type,
                    AgentModelConfig.from_dict(agents_data[agent_type]),
                )
        return config
    
    def merge_with(self, other: "VBAgentConfig") -> "VBAgentConfig":
        """Merge another config into this one (other takes precedence).
        
        Used for workspace config overriding global config.
        """
        # Start with a copy of self
        merged = VBAgentConfig.from_dict(self.to_dict())
        
        other_dict = other.to_dict()
        
        # Override top-level settings if specified in other
        if other_dict.get("default_model"):
            merged.default_model = other_dict["default_model"]
        if other_dict.get("default_reasoning_effort"):
            merged.default_reasoning_effort = other_dict["default_reasoning_effort"]
        if other_dict.get("subject"):
            merged.subject = other_dict["subject"]
        
        # Merge agent configs
        for agent_type in AGENT_TYPES:
            other_agent = other_dict.get("agents", {}).get(agent_type, {})
            if other_agent:
                merged_agent = getattr(merged, agent_type)
                if other_agent.get("model"):
                    merged_agent.model = other_agent["model"]
                if other_agent.get("reasoning_effort"):
                    merged_agent.reasoning_effort = other_agent["reasoning_effort"]
                if other_agent.get("temperature") is not None:
                    merged_agent.temperature = other_agent["temperature"]
                if other_agent.get("max_tokens") is not None:
                    merged_agent.max_tokens = other_agent["max_tokens"]
        
        return merged

    def save(self, workspace: bool = False) -> Path:
        """Save configuration to file.
        
        Args:
            workspace: If True, save to .vbagent.json in current directory.
                      If False, save to global config.
        
        Returns:
            Path to the saved config file.
        """
        if workspace:
            config_path = Path.cwd() / WORKSPACE_CONFIG_FILE
        else:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config_path = CONFIG_FILE
        
        config_path.write_text(json.dumps(self.to_dict(), indent=2))
        return config_path

    @classmethod
    def load(cls, workspace_path: Optional[Path] = None) -> "VBAgentConfig":
        """Load configuration with workspace override.
        
        Loads global config first, then merges workspace config if present.
        
        Args:
            workspace_path: Path to look for .vbagent.json. Defaults to cwd.
        
        Returns:
            Merged configuration (workspace overrides global).
        """
        # Load global config
        global_config = cls()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                global_config = cls.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Check for workspace config
        if workspace_path is None:
            workspace_path = Path.cwd()
        
        workspace_config_file = workspace_path / WORKSPACE_CONFIG_FILE
        if workspace_config_file.exists():
            try:
                data = json.loads(workspace_config_file.read_text())
                workspace_config = cls.from_dict(data)
                # Merge: workspace overrides global
                return global_config.merge_with(workspace_config)
            except (json.JSONDecodeError, KeyError):
                pass
        
        return global_config
    
    @classmethod
    def load_global(cls) -> "VBAgentConfig":
        """Load only global configuration (ignores workspace config)."""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return cls.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return cls()


def get_workspace_config_path() -> Optional[Path]:
    """Get path to workspace config if it exists."""
    workspace_config = Path.cwd() / WORKSPACE_CONFIG_FILE
    if workspace_config.exists():
        return workspace_config
    return None


def has_workspace_config() -> bool:
    """Check if workspace config exists in current directory."""
    return (Path.cwd() / WORKSPACE_CONFIG_FILE).exists()


# Global configuration instance
_config: Optional[VBAgentConfig] = None


def get_config() -> VBAgentConfig:
    """Get the global configuration instance (loads from file if needed)."""
    global _config
    if _config is None:
        _config = VBAgentConfig.load()
    return _config


def set_config(config: VBAgentConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def save_config(workspace: bool = False) -> Path:
    """Save current configuration to file.
    
    Args:
        workspace: If True, save to .vbagent.json in current directory.
    
    Returns:
        Path to the saved config file.
    """
    config = get_config()
    return config.save(workspace=workspace)


def reset_config(workspace: bool = False) -> None:
    """Reset configuration to defaults.
    
    Args:
        workspace: If True, delete workspace config. If False, delete global config.
    """
    global _config
    
    if workspace:
        workspace_config = Path.cwd() / WORKSPACE_CONFIG_FILE
        if workspace_config.exists():
            workspace_config.unlink()
    else:
        _config = None
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()


def init_workspace(subject: str = "physics", force: bool = False) -> Path:
    """Initialize workspace config from global defaults.
    
    Creates .vbagent.json in current directory with settings from global config.
    
    Args:
        subject: Subject for this workspace (physics, chemistry, etc.)
        force: If True, overwrite existing workspace config.
    
    Returns:
        Path to created config file.
    
    Raises:
        FileExistsError: If workspace config exists and force=False.
    """
    workspace_config = Path.cwd() / WORKSPACE_CONFIG_FILE
    
    if workspace_config.exists() and not force:
        raise FileExistsError(f"Workspace config already exists: {workspace_config}")
    
    # Load global config as base
    config = VBAgentConfig.load_global()
    config.subject = subject
    
    return config.save(workspace=True)


# Convenience functions for backward compatibility
def get_model(agent_type: str = "default") -> str:
    """Get model for an agent type."""
    config = get_config()
    if agent_type == "default":
        return config.default_model
    return config.get_model(agent_type)


def get_model_settings(agent_type: str = "default") -> "ModelSettings":
    """Get ModelSettings for an agent type."""
    config = get_config()
    if agent_type == "default":
        ModelSettings = _get_model_settings_class()
        return ModelSettings(reasoning={"effort": config.default_reasoning_effort})
    return config.get_model_settings(agent_type)


# Legacy exports for backward compatibility
DEFAULT_MODEL = "gpt-5.1"


def _get_default_model_settings() -> "ModelSettings":
    """Lazy getter for default model settings."""
    ModelSettings = _get_model_settings_class()
    return ModelSettings(reasoning={"effort": "high"})


# Use property-like access for lazy loading
class _LazyModelSettings:
    """Lazy wrapper for DEFAULT_MODEL_SETTINGS."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = _get_default_model_settings()
        return cls._instance


# For backward compatibility - will be lazily evaluated when accessed
DEFAULT_MODEL_SETTINGS = None  # Set to None, actual value created on first use


def get_default_model_settings() -> "ModelSettings":
    """Get default model settings (lazy loaded)."""
    return _get_default_model_settings()
