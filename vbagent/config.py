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
    # OpenAI
    "gpt-5.2": "gpt-5.2",
    "gpt-5.1": "gpt-5.1",
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5.1-codex": "gpt-5.1-codex",
    "gpt-5.1-codex-mini": "gpt-5.1-codex-mini",
    "gpt-5.1-codex-max": "gpt-5.1-codex-max",
    # xAI Grok
    "grok-4": "grok-4",                                  # Frontier reasoning, 256k ctx, $3/$15
    "grok-4-fast-reasoning": "grok-4-fast-reasoning",     # 2M ctx, reasoning + tools, $0.20/$0.50
    "grok-4-fast-non-reasoning": "grok-4-fast-non-reasoning",  # 2M ctx, no reasoning tokens, $0.20/$0.50
    "grok-4-1-fast-reasoning": "grok-4-1-fast-reasoning",     # 2M ctx, agentic reasoning + tools
    "grok-4-1-fast-non-reasoning": "grok-4-1-fast-non-reasoning",  # 2M ctx, fast non-reasoning
    "grok-code-fast-1": "grok-code-fast-1",               # Agentic coding, 256k ctx, $0.20/$1.50
    "grok-3": "grok-3",                                   # Enterprise generalist, 131k ctx
    "grok-3-mini": "grok-3-mini",                         # Budget generalist, 131k ctx
    "grok-2-vision-1212": "grok-2-vision-1212",           # Image understanding, 32k ctx
    # Google
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-3-flash-preview": "gemini-3-flash-preview",   # 1M ctx, thinking model
}

# Known providers with their base URLs and env var names
PROVIDERS = {
    "openai": {"base_url": None, "env_key": "OPENAI_API_KEY"},
    "xai": {"base_url": "https://api.x.ai/v1", "env_key": "XAI_API_KEY"},
    "google": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "env_key": "GOOGLE_API_KEY"},
}

# Agent types
AGENT_TYPES = [
    "classifier",
    "scanner",
    "tikz",
    "fbd",
    "tikz_checker",
    "idea",
    "alternate",
    "variant",
    "converter",
    "reviewer",
    "taxonomy_classifier",
    "difficulty_assessor",
    "solution_checker",
    "grammar_checker",
    "clarity_checker",
    "latex_fixer",
    "format_checker",
]

# Model groups: per-provider default models for each agent type.
# When switching providers, these get auto-applied so every agent
# gets the right model for that provider.
MODEL_GROUPS: dict[str, dict[str, str]] = {
    "openai": {
        "default_model": "gpt-5.2",
        "classifier": "gpt-5-nano",
        "scanner": "gpt-5.2",
        "tikz": "gpt-5.1-codex",
        "fbd": "gpt-5.1-codex",
        "tikz_checker": "gpt-5-mini",
        "idea": "gpt-5.2",
        "alternate": "gpt-5.2",
        "variant": "gpt-5.2",
        "converter": "gpt-5-mini",
        "reviewer": "gpt-5.2",
        "taxonomy_classifier": "gpt-5-nano",
        "difficulty_assessor": "gpt-5.1",
    },
    "xai": {
        "default_model": "grok-4-1-fast-reasoning",
        "classifier": "grok-4-1-fast-reasoning",
        "scanner": "grok-4-1-fast-reasoning",
        "tikz": "grok-4-1-fast-reasoning",
        "fbd": "grok-4-1-fast-reasoning",
        "tikz_checker": "grok-4-1-fast-reasoning",
        "idea": "grok-4-1-fast-reasoning",
        "alternate": "grok-4-1-fast-reasoning",
        "variant": "grok-4-1-fast-reasoning",
        "converter": "grok-4-1-fast-reasoning",
        "reviewer": "grok-4-1-fast-reasoning",
    },
    "google": {
        "default_model": "gemini-3-flash-preview",
        "classifier": "gemini-3-flash-preview",
        "scanner": "gemini-3-flash-preview",
        "tikz": "gemini-3-flash-preview",
        "fbd": "gemini-3-flash-preview",
        "tikz_checker": "gemini-3-flash-preview",
        "idea": "gemini-3-flash-preview",
        "alternate": "gemini-3-flash-preview",
        "variant": "gemini-3-flash-preview",
        "converter": "gemini-3-flash-preview",
        "reviewer": "gemini-3-flash-preview",
    },
}

# Per-model reasoning_effort support.
# Maps model prefix -> set of valid effort values, or None if not supported.
# Sources:
#   OpenAI: low, medium, high (gpt-5.1+ also supports none; codex models vary)
#   xAI: only grok-3-mini supports low/high; all others error on reasoning_effort
#   Google: low, medium, high (2.5 models also support none/minimal)
REASONING_SUPPORT: dict[str, Optional[set[str]]] = {
    # OpenAI models
    "gpt-5.2": {"low", "medium", "high", "xhigh"},
    "gpt-5.1": {"none", "low", "medium", "high"},
    "gpt-5-mini": {"low", "medium", "high"},
    "gpt-5-nano": None,  # nano doesn't support reasoning
    "gpt-5.1-codex": {"low", "medium", "high"},
    "gpt-5.1-codex-mini": {"low", "medium", "high"},
    "gpt-5.1-codex-max": {"low", "medium", "high"},
    # xAI models — only grok-3-mini supports reasoning_effort
    "grok-4": None,
    "grok-4-fast-reasoning": None,
    "grok-4-fast-non-reasoning": None,
    "grok-4-1-fast-reasoning": None,
    "grok-4-1-fast-non-reasoning": None,
    "grok-code-fast-1": None,
    "grok-3": None,
    "grok-3-mini": {"low", "high"},
    "grok-2-vision-1212": None,
    # Google models
    "gemini-2.5-pro": {"none", "low", "medium", "high"},
    "gemini-2.5-flash": {"none", "low", "medium", "high"},
    "gemini-3-flash-preview": {"low", "medium", "high"},
}


def get_reasoning_support(model: str) -> Optional[set[str]]:
    """Get the set of valid reasoning_effort values for a model.
    
    Returns:
        Set of valid effort strings, or None if reasoning_effort is not supported.
    """
    # Exact match first
    if model in REASONING_SUPPORT:
        return REASONING_SUPPORT[model]
    # Prefix match for unknown model variants
    for prefix, values in REASONING_SUPPORT.items():
        if model.startswith(prefix):
            return values
    # Unknown model — assume it supports standard values
    return {"low", "medium", "high"}


def _provider_from_base_url(base_url: Optional[str]) -> Optional[str]:
    """Detect provider name from a base_url.
    
    Returns:
        Provider name ('openai', 'xai', 'google') or None if unknown.
    """
    if not base_url:
        return "openai"
    for name, info in PROVIDERS.items():
        if info["base_url"] and base_url.rstrip("/") == info["base_url"].rstrip("/"):
            return name
    return None


def apply_model_group(config: "VBAgentConfig", provider_name: str) -> None:
    """Apply a model group to a config, setting all agent models AND the base_url.
    
    This ensures the provider URL and models are always in sync.
    
    Args:
        config: The VBAgentConfig to update.
        provider_name: Provider key in MODEL_GROUPS (openai, xai, google).
    """
    group = MODEL_GROUPS.get(provider_name)
    if not group:
        return
    
    # Update base_url to match the provider
    if provider_name in PROVIDERS:
        config.base_url = PROVIDERS[provider_name]["base_url"]
    
    config.default_model = group["default_model"]
    for agent_type in AGENT_TYPES:
        if agent_type in group:
            getattr(config, agent_type).model = group[agent_type]


def _get_model_settings_class():
    """Lazy import of ModelSettings to avoid heavy import at module load."""
    from agents import ModelSettings
    return ModelSettings
def _migrate_flat_to_hierarchical(data: dict) -> dict:
    """Migrate old flat config structure to new hierarchical structure.

    Old format:
        {
            "agents": {
                "scanner": {...},
                "tikz": {...},
                ...
            }
        }

    New format:
        {
            "classification": {
                "image_classifier": {...},
                ...
            },
            "content_generation": {
                "scanner": {...},
                ...
            },
            ...
        }

    Args:
        data: Config dictionary (may be old or new format)

    Returns:
        Config dictionary in new hierarchical format
    """
    # If already in new format (has hierarchical keys), return as-is
    if any(key in data for key in ["classification", "content_generation", "diagram", "variants", "quality"]):
        return data

    # Check if we have old flat format with "agents" key
    agents_data = data.get("agents", {})
    if not agents_data:
        return data

    # Create new hierarchical structure
    migrated = data.copy()

    # Map old agent names to new hierarchical structure
    classification_agents = {
        "classifier": "image_classifier",
        "taxonomy_classifier": "taxonomy_classifier",
        "difficulty_assessor": "difficulty_assessor",
    }

    content_generation_agents = {
        "scanner": "scanner",
        "idea": "idea",
        "alternate": "alternate",
        "converter": "converter",
    }

    diagram_agents = {
        "tikz": "tikz",
        "fbd": "fbd",
        "tikz_checker": "tikz_checker",
    }

    variants_agents = {
        "variant": "variant",
        "multi_variant": "multi_context",  # Handle old name
    }

    quality_agents = {
        "reviewer": "reviewer",
        "solution_checker": "solution_checker",
        "grammar_checker": "grammar_checker",
        "clarity_checker": "clarity_checker",
        "compile_fixer": "latex_fixer",  # Handle old name
    }

    # Build hierarchical structure
    classification_config = {}
    for old_name, new_name in classification_agents.items():
        if old_name in agents_data:
            classification_config[new_name] = agents_data[old_name]

    content_generation_config = {}
    for old_name, new_name in content_generation_agents.items():
        if old_name in agents_data:
            content_generation_config[new_name] = agents_data[old_name]

    diagram_config = {}
    for old_name, new_name in diagram_agents.items():
        if old_name in agents_data:
            diagram_config[new_name] = agents_data[old_name]

    variants_config = {}
    for old_name, new_name in variants_agents.items():
        if old_name in agents_data:
            variants_config[new_name] = agents_data[old_name]

    quality_config = {}
    for old_name, new_name in quality_agents.items():
        if old_name in agents_data:
            quality_config[new_name] = agents_data[old_name]

    # Add hierarchical configs to migrated data
    if classification_config:
        migrated["classification"] = classification_config
    if content_generation_config:
        migrated["content_generation"] = content_generation_config
    if diagram_config:
        migrated["diagram"] = diagram_config
    if variants_config:
        migrated["variants"] = variants_config
    if quality_config:
        migrated["quality"] = quality_config

    # Keep old "agents" key for backward compatibility during transition
    # It will be ignored by the new from_dict() but allows old code to still work

    return migrated





@dataclass
class AgentModelConfig:
    """Configuration for a specific agent's model settings."""

    model: str = "gpt-5.2"
    reasoning_effort: str = "high"  # low, medium, high
    max_tokens: Optional[int] = None

    def to_model_settings(self) -> "ModelSettings":
        """Convert to ModelSettings for the agent."""
        ModelSettings = _get_model_settings_class()
        settings_dict = {}

        # Check per-model reasoning_effort support
        supported = get_reasoning_support(self.model)
        if supported is not None:
            effort = self.reasoning_effort
            # Clamp to nearest valid value if the configured effort isn't supported
            if effort not in supported:
                # Pick the closest valid effort
                priority = ["high", "medium", "low"]
                effort = next((e for e in priority if e in supported), None)
            if effort:
                settings_dict["reasoning"] = {"effort": effort}

        # Add optional settings
        if self.max_tokens is not None:
            settings_dict["max_tokens"] = self.max_tokens

        return ModelSettings(**settings_dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentModelConfig":
        """Create from dictionary."""
        return cls(
            model=data.get("model", "gpt-5.2"),
            reasoning_effort=data.get("reasoning_effort", "high"),
            max_tokens=data.get("max_tokens"),
        )


@dataclass
class ClassificationConfig:
    """Configuration for classification agents."""
    image_classifier: AgentModelConfig = field(default_factory=AgentModelConfig)
    diagram_analyzer: AgentModelConfig = field(default_factory=AgentModelConfig)
    difficulty_assessor: AgentModelConfig = field(default_factory=AgentModelConfig)
    latex_classifier: AgentModelConfig = field(default_factory=AgentModelConfig)
    taxonomy_classifier: AgentModelConfig = field(default_factory=AgentModelConfig)


@dataclass
class ContentGenerationConfig:
    """Configuration for content generation agents."""
    scanner: AgentModelConfig = field(default_factory=AgentModelConfig)
    solution: AgentModelConfig = field(default_factory=AgentModelConfig)
    idea: AgentModelConfig = field(default_factory=AgentModelConfig)
    alternate: AgentModelConfig = field(default_factory=AgentModelConfig)
    converter: AgentModelConfig = field(default_factory=AgentModelConfig)


@dataclass
class DiagramConfig:
    """Configuration for diagram agents."""
    tikz: AgentModelConfig = field(default_factory=AgentModelConfig)
    fbd: AgentModelConfig = field(default_factory=AgentModelConfig)
    tikz_checker: AgentModelConfig = field(default_factory=AgentModelConfig)


@dataclass
class VariantsConfig:
    """Configuration for variant agents."""
    variant: AgentModelConfig = field(default_factory=AgentModelConfig)
    multi_context: AgentModelConfig = field(default_factory=AgentModelConfig)


@dataclass
class QualityConfig:
    """Configuration for quality agents."""
    reviewer: AgentModelConfig = field(default_factory=AgentModelConfig)
    solution_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    grammar_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    clarity_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    latex_fixer: AgentModelConfig = field(default_factory=AgentModelConfig)
    format_checker: AgentModelConfig = field(default_factory=AgentModelConfig)





@dataclass
class VBAgentConfig:
    """Main configuration for all vbagent agents."""

    # Default model for all agents
    default_model: str = "gpt-5.2"
    default_reasoning_effort: str = "high"
    
    # Subject for prompts (physics, chemistry, mathematics, biology)
    subject: str = "physics"
    
    # Debug mode
    debug: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Provider settings
    base_url: Optional[str] = None  # None = OpenAI default
    api_key: Optional[str] = None   # None = use OPENAI_API_KEY env var

    # Per-agent model overrides (DEPRECATED - use hierarchical config below)
    classifier: AgentModelConfig = field(default_factory=AgentModelConfig)
    scanner: AgentModelConfig = field(default_factory=AgentModelConfig)
    tikz: AgentModelConfig = field(default_factory=AgentModelConfig)
    fbd: AgentModelConfig = field(default_factory=AgentModelConfig)
    tikz_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    idea: AgentModelConfig = field(default_factory=AgentModelConfig)
    alternate: AgentModelConfig = field(default_factory=AgentModelConfig)
    variant: AgentModelConfig = field(default_factory=AgentModelConfig)
    converter: AgentModelConfig = field(default_factory=AgentModelConfig)
    reviewer: AgentModelConfig = field(default_factory=AgentModelConfig)
    taxonomy_classifier: AgentModelConfig = field(default_factory=AgentModelConfig)
    difficulty_assessor: AgentModelConfig = field(default_factory=AgentModelConfig)
    solution_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    grammar_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    clarity_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    latex_fixer: AgentModelConfig = field(default_factory=AgentModelConfig)
    format_checker: AgentModelConfig = field(default_factory=AgentModelConfig)
    
    # Hierarchical agent configs (NEW - preferred)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    content_generation: ContentGenerationConfig = field(default_factory=ContentGenerationConfig)
    diagram: DiagramConfig = field(default_factory=DiagramConfig)
    variants: VariantsConfig = field(default_factory=VariantsConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    
    # Pipeline settings
    enable_taxonomy: bool = True
    enable_difficulty: bool = True
    run_metadata_parallel: bool = True
    
    # Confidence thresholds for fallback
    classifier_confidence_threshold: float = 0.7
    taxonomy_confidence_threshold: float = 0.8

    def __post_init__(self):
        """Set better defaults for specific agents."""
        # Classifier uses nano with no reasoning
        if self.classifier.model == "gpt-5.2":
            self.classifier.model = "gpt-5-nano"
        if self.classifier.reasoning_effort == "high":
            self.classifier.reasoning_effort = "low"
            
        # Scanner uses medium reasoning
        if self.scanner.reasoning_effort == "high":
            self.scanner.reasoning_effort = "medium"
            
        # Solution agent uses high reasoning (default gpt-5.2)
        # No changes needed - uses defaults
            
        # TikZ checker doesn't need high reasoning
        if self.tikz_checker.reasoning_effort == "high":
            self.tikz_checker.reasoning_effort = "low"
            
        # Taxonomy classifier uses nano with no reasoning
        if self.taxonomy_classifier.model == "gpt-5.2":
            self.taxonomy_classifier.model = "gpt-5-nano"
        if self.taxonomy_classifier.reasoning_effort == "high":
            self.taxonomy_classifier.reasoning_effort = "low"
            
        # Difficulty assessor uses low reasoning
        if self.difficulty_assessor.model == "gpt-5.2":
            self.difficulty_assessor.model = "gpt-5.1"
        if self.difficulty_assessor.reasoning_effort == "high":
            self.difficulty_assessor.reasoning_effort = "low"

    def get_model(self, agent_type: str) -> str:
        """Get the model for a specific agent type.
        
        Supports both flat and hierarchical paths:
        - Flat: "scanner", "tikz", "reviewer"
        - Hierarchical: "content_generation.scanner", "diagram.tikz", "quality.reviewer"
        
        Args:
            agent_type: Agent type (flat or hierarchical path)
            
        Returns:
            Model name for the agent
        """
        # Try hierarchical path first (e.g., "content_generation.scanner")
        if "." in agent_type:
            category, agent_name = agent_type.split(".", 1)
            category_config = getattr(self, category, None)
            if category_config:
                agent_config = getattr(category_config, agent_name, None)
                if agent_config and agent_config.model:
                    return agent_config.model
        
        # Try flat path (backward compatibility)
        config = getattr(self, agent_type, None)
        if config and isinstance(config, AgentModelConfig) and config.model:
            return config.model
        
        return self.default_model

    def get_model_settings(self, agent_type: str) -> "ModelSettings":
        """Get ModelSettings for a specific agent type.
        
        Supports both flat and hierarchical paths:
        - Flat: "scanner", "tikz", "reviewer"
        - Hierarchical: "content_generation.scanner", "diagram.tikz", "quality.reviewer"
        
        Args:
            agent_type: Agent type (flat or hierarchical path)
            
        Returns:
            ModelSettings for the agent
        """
        # Try hierarchical path first (e.g., "content_generation.scanner")
        if "." in agent_type:
            category, agent_name = agent_type.split(".", 1)
            category_config = getattr(self, category, None)
            if category_config:
                agent_config = getattr(category_config, agent_name, None)
                if agent_config:
                    return agent_config.to_model_settings()
        
        # Try flat path (backward compatibility)
        config = getattr(self, agent_type, None)
        if config and isinstance(config, AgentModelConfig):
            return config.to_model_settings()
        
        ModelSettings = _get_model_settings_class()
        return ModelSettings(reasoning={"effort": self.default_reasoning_effort})

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            "default_model": self.default_model,
            "default_reasoning_effort": self.default_reasoning_effort,
            "subject": self.subject,
            "debug": self.debug,
            "log_level": self.log_level,
            "enable_taxonomy": self.enable_taxonomy,
            "enable_difficulty": self.enable_difficulty,
            "run_metadata_parallel": self.run_metadata_parallel,
            "classifier_confidence_threshold": self.classifier_confidence_threshold,
            "taxonomy_confidence_threshold": self.taxonomy_confidence_threshold,
            "agents": {
                agent_type: getattr(self, agent_type).to_dict()
                for agent_type in AGENT_TYPES
            },
            # Hierarchical configs (NEW format)
            "classification": {
                "image_classifier": self.classification.image_classifier.to_dict(),
                "diagram_analyzer": self.classification.diagram_analyzer.to_dict(),
                "difficulty_assessor": self.classification.difficulty_assessor.to_dict(),
                "latex_classifier": self.classification.latex_classifier.to_dict(),
                "taxonomy_classifier": self.classification.taxonomy_classifier.to_dict(),
            },
            "content_generation": {
                "scanner": self.content_generation.scanner.to_dict(),
                "solution": self.content_generation.solution.to_dict(),
                "idea": self.content_generation.idea.to_dict(),
                "alternate": self.content_generation.alternate.to_dict(),
                "converter": self.content_generation.converter.to_dict(),
            },
            "diagram": {
                "tikz": self.diagram.tikz.to_dict(),
                "fbd": self.diagram.fbd.to_dict(),
                "tikz_checker": self.diagram.tikz_checker.to_dict(),
            },
            "variants": {
                "variant": self.variants.variant.to_dict(),
                "multi_context": self.variants.multi_context.to_dict(),
            },
            "quality": {
                "reviewer": self.quality.reviewer.to_dict(),
                "solution_checker": self.quality.solution_checker.to_dict(),
                "grammar_checker": self.quality.grammar_checker.to_dict(),
                "clarity_checker": self.quality.clarity_checker.to_dict(),
                "latex_fixer": self.quality.latex_fixer.to_dict(),
                "format_checker": self.quality.format_checker.to_dict(),
            },
        }
        if self.base_url:
            d["base_url"] = self.base_url
        if self.api_key:
            d["api_key"] = self.api_key
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "VBAgentConfig":
        """Create from dictionary.
        
        Automatically migrates old flat config to new hierarchical format.
        """
        # Migrate old flat config to hierarchical if needed
        data = _migrate_flat_to_hierarchical(data)
        
        config = cls(
            default_model=data.get("default_model", "gpt-5.2"),
            default_reasoning_effort=data.get("default_reasoning_effort", "high"),
            subject=data.get("subject", "physics"),
            debug=data.get("debug", False),
            log_level=data.get("log_level", "INFO"),
            base_url=data.get("base_url"),
            api_key=data.get("api_key"),
            enable_taxonomy=data.get("enable_taxonomy", True),
            enable_difficulty=data.get("enable_difficulty", True),
            run_metadata_parallel=data.get("run_metadata_parallel", True),
            classifier_confidence_threshold=data.get("classifier_confidence_threshold", 0.7),
            taxonomy_confidence_threshold=data.get("taxonomy_confidence_threshold", 0.8),
        )
        
        # Load hierarchical configs (NEW format)
        if "classification" in data:
            classification_data = data["classification"]
            for agent_name in ["image_classifier", "diagram_analyzer", "difficulty_assessor", "latex_classifier", "taxonomy_classifier"]:
                if agent_name in classification_data:
                    setattr(
                        config.classification,
                        agent_name,
                        AgentModelConfig.from_dict(classification_data[agent_name]),
                    )
        
        if "content_generation" in data:
            content_gen_data = data["content_generation"]
            for agent_name in ["scanner", "solution", "idea", "alternate", "converter"]:
                if agent_name in content_gen_data:
                    setattr(
                        config.content_generation,
                        agent_name,
                        AgentModelConfig.from_dict(content_gen_data[agent_name]),
                    )
        
        if "diagram" in data:
            diagram_data = data["diagram"]
            for agent_name in ["tikz", "fbd", "tikz_checker"]:
                if agent_name in diagram_data:
                    setattr(
                        config.diagram,
                        agent_name,
                        AgentModelConfig.from_dict(diagram_data[agent_name]),
                    )
        
        if "variants" in data:
            variants_data = data["variants"]
            for agent_name in ["variant", "multi_context"]:
                if agent_name in variants_data:
                    setattr(
                        config.variants,
                        agent_name,
                        AgentModelConfig.from_dict(variants_data[agent_name]),
                    )
        
        if "quality" in data:
            quality_data = data["quality"]
            for agent_name in ["reviewer", "solution_checker", "grammar_checker", "clarity_checker", "latex_fixer", "format_checker"]:
                if agent_name in quality_data:
                    setattr(
                        config.quality,
                        agent_name,
                        AgentModelConfig.from_dict(quality_data[agent_name]),
                    )
        
        # Load flat configs for backward compatibility (OLD format)
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
        if other_dict.get("base_url"):
            merged.base_url = other_dict["base_url"]
        if other_dict.get("api_key"):
            merged.api_key = other_dict["api_key"]
        
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


def apply_provider_config() -> None:
    """Apply base_url and api_key from config to the OpenAI client.
    
    Sets environment variables so the openai-agents SDK picks them up.
    Also disables tracing for non-OpenAI providers (traces go to
    platform.openai.com and fail with non-OpenAI keys).
    
    Resolution order for API key:
    1. api_key in config (explicit)
    2. Provider-specific env var (XAI_API_KEY, GOOGLE_API_KEY, etc.)
    3. OPENAI_API_KEY env var (fallback)
    """
    config = get_config()
    
    if config.base_url:
        os.environ["OPENAI_BASE_URL"] = config.base_url
        # Disable tracing for non-OpenAI providers — the SDK sends traces
        # to platform.openai.com which rejects non-OpenAI API keys.
        os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    else:
        # OpenAI provider — tracing works fine
        os.environ.pop("OPENAI_AGENTS_DISABLE_TRACING", None)
        os.environ.pop("OPENAI_BASE_URL", None)
    
    if config.api_key:
        # Explicit key in config takes priority
        os.environ["OPENAI_API_KEY"] = config.api_key
    elif config.base_url:
        # Try to find the matching provider's env var
        for name, info in PROVIDERS.items():
            if info["base_url"] and config.base_url.rstrip("/") == info["base_url"].rstrip("/"):
                env_key = info["env_key"]
                key_value = os.environ.get(env_key)
                if key_value and env_key != "OPENAI_API_KEY":
                    os.environ["OPENAI_API_KEY"] = key_value
                break


def get_provider_name() -> str:
    """Get a friendly name for the current provider."""
    config = get_config()
    if not config.base_url:
        return "OpenAI"
    for name, info in PROVIDERS.items():
        if info["base_url"] and config.base_url.rstrip("/") == info["base_url"].rstrip("/"):
            return name.upper() if name == "xai" else name.title()
    return config.base_url
