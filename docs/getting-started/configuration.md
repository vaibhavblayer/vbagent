# Configuration

VBAgent uses a hierarchical configuration system for managing models, providers, and agent settings.

## Configuration Files

Configuration is loaded in this order (later overrides earlier):

1. **Global config**: `~/.config/vbagent/models.json`
2. **Workspace config**: `.vbagent.json` in current directory

## Initialize Configuration

```bash
# Interactive setup
vbagent init

# Quick setup (only ask for subject)
vbagent init --quick

# Non-interactive (use defaults)
vbagent init --yes

# Overwrite existing config
vbagent init --force
```

## Configuration Structure

```json
{
  "subject": "physics",
  "classifier": {
    "model": "gpt-4o-mini",
    "reasoning_effort": "low"
  },
  "scanner": {
    "model": "gpt-4o",
    "reasoning_effort": "high"
  },
  "tikz": {
    "model": "gpt-4o",
    "reasoning_effort": "medium"
  },
  "variant": {
    "model": "gpt-4o",
    "reasoning_effort": "medium"
  }
}
```

## Supported Providers

### OpenAI
```bash
export OPENAI_API_KEY="your-key"
```

Models: `gpt-4o`, `gpt-4o-mini`, `o1`, `o1-mini`

### xAI (Grok)
```bash
export XAI_API_KEY="your-key"
```

Models: `grok-2-1212`, `grok-2-vision-1212`, `grok-beta`

### Google (Gemini)
```bash
export GOOGLE_API_KEY="your-key"
```

Models: `gemini-2.0-flash-exp`, `gemini-exp-1206`

## Agent Types

- `classifier` - Question type classification
- `scanner` - LaTeX extraction
- `tikz` - TikZ diagram generation
- `tikz_checker` - TikZ validation
- `idea` - Concept extraction
- `alternate` - Alternate solutions
- `variant` - Problem variants
- `converter` - Format conversion
- `reviewer` - QA review

## Reasoning Levels

- `low` - Fast, basic reasoning
- `medium` - Balanced speed/quality
- `high` - Deep reasoning, slower
- `xhigh` - Maximum reasoning (o1 models only)

## CLI Configuration Commands

### View Current Config
```bash
vbagent config show
```

### Set Agent Configuration
```bash
# Set model
vbagent config set scanner --model gpt-4o

# Set reasoning level
vbagent config set tikz --reasoning high

# Set temperature
vbagent config set variant --temperature 0.7

# Set multiple options
vbagent config set scanner --model gpt-4o --reasoning high
```

### Reset to Defaults
```bash
vbagent config reset
```

### List Available Models
```bash
vbagent config models
```

## Programmatic Configuration

```python
from vbagent import get_config, set_config

# Get current config
config = get_config()

# Modify settings
config.scanner.model = "gpt-4o"
config.scanner.reasoning_effort = "high"
config.tikz.model = "gpt-4o-mini"

# Apply changes
set_config(config)
```

## Subject-Specific Settings

Subjects affect:
- LaTeX preamble packages
- Prompt context
- Reference materials

Available subjects:
- `physics`
- `chemistry`
- `mathematics`
- `biology`

## Performance Tips

1. **Use gpt-4o-mini for classification** - 5-10x faster, same accuracy
2. **Use high reasoning for scanning** - Better LaTeX quality
3. **Use medium reasoning for variants** - Good balance
4. **Set subject correctly** - Loads appropriate packages

## Example Configurations

### Fast Processing
```json
{
  "subject": "physics",
  "classifier": {"model": "gpt-4o-mini", "reasoning_effort": "low"},
  "scanner": {"model": "gpt-4o", "reasoning_effort": "medium"},
  "tikz": {"model": "gpt-4o-mini", "reasoning_effort": "low"}
}
```

### High Quality
```json
{
  "subject": "physics",
  "classifier": {"model": "gpt-4o", "reasoning_effort": "medium"},
  "scanner": {"model": "o1", "reasoning_effort": "high"},
  "tikz": {"model": "gpt-4o", "reasoning_effort": "high"}
}
```

### Budget-Friendly
```json
{
  "subject": "physics",
  "classifier": {"model": "gpt-4o-mini", "reasoning_effort": "low"},
  "scanner": {"model": "gpt-4o-mini", "reasoning_effort": "medium"},
  "tikz": {"model": "gpt-4o-mini", "reasoning_effort": "low"}
}
```
