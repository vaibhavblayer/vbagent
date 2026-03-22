# vbagent Configuration Examples

Complete guide to configuring models, providers, and settings for vbagent.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Hierarchy](#configuration-hierarchy)
3. [Model Configuration](#model-configuration)
4. [Provider Configuration](#provider-configuration)
5. [Agent-Specific Models](#agent-specific-models)
6. [Model Groups](#model-groups)
7. [Workspace vs Global Config](#workspace-vs-global-config)
8. [Advanced Examples](#advanced-examples)

---

## Quick Start

### View Current Configuration
```bash
# Show all current settings
vbagent config show

# List available models
vbagent config models

# Check debug status
vbagent config debug status
```

### Initialize Workspace Config
```bash
# Interactive setup (recommended for new projects)
vbagent config init

# Quick setup (only asks for subject)
vbagent config init --quick

# Non-interactive with defaults
vbagent config init --yes
```

---

## Configuration Hierarchy

vbagent uses a two-level configuration system:

1. **Global Config**: `~/.config/vbagent/models.json` (Linux/macOS) or `%APPDATA%\vbagent\models.json` (Windows)
2. **Workspace Config**: `.vbagent.json` in your project directory

Workspace config overrides global config. This allows:
- Global defaults for all projects
- Project-specific overrides (e.g., chemistry project uses different models)

---

## Model Configuration

### Set Default Model (All Agents)
```bash
# Set global default
vbagent config set default --model gpt-5.4-mini

# Set with reasoning level
vbagent config set default --model gpt-5.4-mini --reasoning medium

# Set in workspace config
vbagent config set default --model gpt-5.4 --workspace
```

### Available Models

**OpenAI Models:**
- `gpt-5.4-mini` - Fast, cost-effective (recommended default)
- `gpt-5.4` - More capable, higher quality
- `gpt-5.2` - Previous generation
- `gpt-5.1-codex` - Code-specialized

**xAI Grok Models:**
- `grok-4-1-fast-reasoning` - Fast with reasoning (recommended)
- `grok-4` - Frontier reasoning model
- `grok-3-mini` - Budget option
- `grok-code-fast-1` - Code-specialized

**Google Gemini Models:**
- `gemini-3-flash-preview` - Fast, 1M context
- `gemini-2.5-pro` - High capability
- `gemini-2.5-flash` - Fast and efficient

### Reasoning Effort Levels

Controls how much "thinking" the model does:

- `low` - Fast, basic reasoning (good for classification)
- `medium` - Balanced (good for scanning, general tasks)
- `high` - Deep reasoning (good for complex diagrams, variants)
- `xhigh` - Maximum reasoning (gpt-5.2 only, for hardest problems)

**Note:** Not all models support reasoning effort. Check with `vbagent config models`.

---

## Provider Configuration

### Switch to xAI Grok
```bash
# Set provider (auto-applies xai model group)
vbagent config provider xai

# Set provider with API key
vbagent config provider xai --api-key xai-xxx

# Set provider without changing models
vbagent config provider xai --no-models

# Set in workspace
vbagent config provider xai --workspace
```

### Switch to Google Gemini
```bash
# Set provider
vbagent config provider google

# With API key
vbagent config provider google --api-key your-google-api-key
```

### Custom Provider (Self-Hosted)
```bash
# Use custom OpenAI-compatible endpoint
vbagent config provider --base-url https://your-api.com/v1

# With API key
vbagent config provider --base-url https://your-api.com/v1 --api-key your-key
```

### Environment Variables

Instead of storing API keys in config, use environment variables:

```bash
# OpenAI
export OPENAI_API_KEY=sk-xxx

# xAI
export XAI_API_KEY=xai-xxx

# Google
export GOOGLE_API_KEY=your-key
```

---

## Agent-Specific Models

Override models for specific agent types:

### Classification Agents
```bash
# Use fast model for classification
vbagent config set classifier --model gpt-5.4-mini --reasoning low

# Use specific model for diagram analysis
vbagent config set diagram_analyzer --model gpt-5.4 --reasoning medium
```

### Diagram Generation Agents
```bash
# Use powerful model for TikZ generation
vbagent config set tikz --model gpt-5.4 --reasoning high

# Chemistry diagrams need high quality
vbagent config set organic_structure --model gpt-5.4 --reasoning high

# Physics diagrams
vbagent config set fbd --model gpt-5.4 --reasoning high
vbagent config set circuit --model gpt-5.4 --reasoning high
```

### Content Generation Agents
```bash
# Scanner (LaTeX extraction)
vbagent config set scanner --model gpt-5.4-mini --reasoning medium

# Solution generation
vbagent config set solution --model gpt-5.4 --reasoning high

# Variant generation
vbagent config set variant --model gpt-5.4-mini --reasoning high
```

### Quality Agents
```bash
# LaTeX checker
vbagent config set latex_fixer --model gpt-5.4-mini --reasoning low

# Solution checker
vbagent config set solution_checker --model gpt-5.4-mini --reasoning medium
```

---

## Model Groups

Model groups are pre-configured sets optimized for each provider.

### View Available Groups
```bash
# List all model groups
vbagent config model-group
```

### Apply a Model Group
```bash
# Apply OpenAI group (all agents use OpenAI models)
vbagent config model-group openai

# Apply xAI group (all agents use Grok models)
vbagent config model-group xai

# Apply Google group (all agents use Gemini models)
vbagent config model-group google

# Apply to workspace
vbagent config model-group openai --workspace
```

**When to use model groups:**
- Switching providers → Automatically applied
- Want consistent provider across all agents
- Starting fresh with a provider's recommended models

**When to use individual agent config:**
- Fine-tuning specific agents
- Mixed provider setup (e.g., OpenAI for most, Grok for diagrams)
- Cost optimization (fast models for simple tasks, powerful for complex)

---

## Workspace vs Global Config

### Global Config (Default)
```bash
# Affects all projects
vbagent config set scanner --model gpt-5.4-mini

# Saved to: ~/.config/vbagent/models.json
```

### Workspace Config (Project-Specific)
```bash
# Only affects current project
vbagent config set scanner --model gpt-5.4 --workspace

# Saved to: .vbagent.json (in current directory)
```

### Use Cases

**Global Config:**
- Personal defaults
- API keys and provider settings
- Models you use across all projects

**Workspace Config:**
- Project-specific requirements (e.g., chemistry needs different models)
- Team settings (commit `.vbagent.json` to git)
- Experiment with different models without affecting other projects

### Example: Chemistry Project
```bash
cd my-chemistry-project

# Initialize workspace config
vbagent config init --quick
# Select: chemistry

# Use powerful models for chemistry diagrams
vbagent config set organic_structure --model gpt-5.4 --reasoning high --workspace
vbagent config set reaction_mechanism --model gpt-5.4 --reasoning high --workspace

# Commit to git for team
git add .vbagent.json
git commit -m "Add vbagent config for chemistry project"
```

---

## Advanced Examples

### Cost Optimization Strategy
```bash
# Fast/cheap models for simple tasks
vbagent config set classifier --model gpt-5.4-mini --reasoning low
vbagent config set scanner --model gpt-5.4-mini --reasoning medium

# Powerful models only for complex tasks
vbagent config set tikz --model gpt-5.4 --reasoning high
vbagent config set variant --model gpt-5.4 --reasoning high
vbagent config set solution --model gpt-5.4 --reasoning high
```

### Quality-First Strategy
```bash
# Use best models for everything
vbagent config set default --model gpt-5.4 --reasoning high

# Override only for classification (doesn't need high reasoning)
vbagent config set classifier --model gpt-5.4-mini --reasoning low
```

### Mixed Provider Setup
```bash
# Use OpenAI for most tasks
vbagent config provider openai

# But use Grok for code-heavy tasks
vbagent config set tikz --model grok-code-fast-1
vbagent config set solution --model grok-4-1-fast-reasoning
```

### Debug and Logging
```bash
# Enable debug mode (shows all agent I/O)
vbagent config debug on

# Set detailed logging
vbagent config log-level DEBUG

# Check status
vbagent config debug status
vbagent config log-level status

# Disable when done
vbagent config debug off
vbagent config log-level INFO
```

### Subject-Specific Setup
```bash
# Physics project
vbagent config subject physics
vbagent config set fbd --model gpt-5.4 --reasoning high
vbagent config set circuit --model gpt-5.4 --reasoning high

# Chemistry project
vbagent config subject chemistry
vbagent config set organic_structure --model gpt-5.4 --reasoning high
vbagent config set reaction_mechanism --model gpt-5.4 --reasoning high

# Mathematics project
vbagent config subject mathematics
vbagent config set function_graph --model gpt-5.4 --reasoning high
vbagent config set geometric_figure --model gpt-5.4 --reasoning high
```

### Reset Configuration
```bash
# Reset global config to defaults
vbagent config reset

# Reset workspace config (removes .vbagent.json)
vbagent config reset --workspace

# Start fresh
vbagent config reset
vbagent config init
```

---

## Configuration File Format

### Global Config: `~/.config/vbagent/models.json`
```json
{
  "default_model": "gpt-5.4-mini",
  "default_reasoning_effort": "medium",
  "subject": "physics",
  "debug": true,
  "log_level": "INFO",
  "base_url": null,
  "api_key": null,
  "agents": {
    "classifier": {
      "model": "gpt-5.4-mini",
      "reasoning_effort": "low",
      "max_tokens": null
    },
    "tikz": {
      "model": "gpt-5.4",
      "reasoning_effort": "high",
      "max_tokens": 16000
    }
  }
}
```

### Workspace Config: `.vbagent.json`
```json
{
  "subject": "chemistry",
  "agents": {
    "organic_structure": {
      "model": "gpt-5.4",
      "reasoning_effort": "high"
    },
    "scanner": {
      "model": "gpt-5.4-mini",
      "reasoning_effort": "medium"
    }
  }
}
```

---

## Troubleshooting

### Check Current Configuration
```bash
# See what's actually being used
vbagent config show

# Check which config file is active
# Output shows: "Using workspace config: .vbagent.json"
#           or: "Using global config: ~/.config/vbagent/models.json"
```

### Model Not Found Error
```bash
# List available models
vbagent config models

# Check if model name is correct (case-sensitive)
vbagent config set scanner --model gpt-5.4-mini  # ✓ Correct
vbagent config set scanner --model GPT-5.4-mini  # ✗ Wrong case
```

### API Key Issues
```bash
# Check if API key is set
vbagent config show
# Look for "API Key: sk-xxx...xxx"

# Set API key
vbagent config provider openai --api-key sk-xxx

# Or use environment variable (recommended)
export OPENAI_API_KEY=sk-xxx
```

### Reasoning Effort Not Supported
```bash
# Some models don't support reasoning_effort
# Check model capabilities:
vbagent config models

# If model doesn't support reasoning, omit --reasoning flag
vbagent config set scanner --model grok-4  # No --reasoning flag
```

---

## Best Practices

1. **Use workspace config for projects**: Commit `.vbagent.json` to version control
2. **Use environment variables for API keys**: Don't commit keys to git
3. **Start with model groups**: Use `vbagent config model-group openai` for consistency
4. **Optimize for cost**: Use fast models for simple tasks, powerful for complex
5. **Enable debug for development**: `vbagent config debug on` when testing
6. **Document your config**: Add comments in your project README about model choices

---

## Quick Reference

```bash
# View
vbagent config show                    # Show all settings
vbagent config models                  # List available models
vbagent config model-group             # List model groups

# Set
vbagent config set <agent> -m <model> -r <reasoning>  # Set agent model
vbagent config set default -m <model>                  # Set default
vbagent config provider <provider>                     # Set provider
vbagent config subject <subject>                       # Set subject

# Workspace
vbagent config init                    # Initialize workspace config
vbagent config set <agent> -m <model> -w  # Save to workspace
vbagent config reset -w                # Reset workspace config

# Debug
vbagent config debug on/off            # Toggle debug mode
vbagent config log-level DEBUG         # Set log level
```

---

For more information, see:
- `vbagent config --help`
- `vbagent config <command> --help`
- [vbagent Documentation](https://github.com/yourusername/vbagent)
