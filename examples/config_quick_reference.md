# vbagent Config Quick Reference

One-page reference for the most common configuration commands.

## View Configuration

```bash
vbagent config show          # Show all current settings
vbagent config models        # List available models
vbagent config model-group   # List model groups
```

## Initialize Project

```bash
vbagent config init          # Interactive setup
vbagent config init --quick  # Quick setup (subject only)
vbagent config init --yes    # Non-interactive with defaults
```

## Set Models

```bash
# Set default for all agents
vbagent config set default --model gpt-5.4-mini --reasoning medium

# Set specific agent
vbagent config set scanner --model gpt-5.4-mini --reasoning medium
vbagent config set tikz --model gpt-5.4 --reasoning high

# Save to workspace (.vbagent.json)
vbagent config set scanner --model gpt-5.4 --workspace
```

## Providers

```bash
# Switch provider (auto-applies model group)
vbagent config provider openai
vbagent config provider xai
vbagent config provider google

# With API key
vbagent config provider xai --api-key xai-xxx

# Custom endpoint
vbagent config provider --base-url https://your-api.com/v1

# Don't change models when switching
vbagent config provider xai --no-models
```

## Model Groups

```bash
# Apply pre-configured model group
vbagent config model-group openai
vbagent config model-group xai
vbagent config model-group google
```

## Subject

```bash
vbagent config subject physics
vbagent config subject chemistry
vbagent config subject mathematics
```

## Debug & Logging

```bash
vbagent config debug on/off/status
vbagent config log-level DEBUG/INFO/WARNING/ERROR
```

## Reset

```bash
vbagent config reset           # Reset global config
vbagent config reset --workspace  # Remove workspace config
```

## Common Agent Types

- `classifier` - Image classification
- `scanner` - LaTeX extraction
- `tikz` - TikZ diagram generation
- `organic_structure` - Chemistry structures
- `fbd` - Free body diagrams
- `circuit` - Circuit diagrams
- `solution` - Solution generation
- `variant` - Problem variants

## Reasoning Levels

- `low` - Fast, basic (classification)
- `medium` - Balanced (scanning, general)
- `high` - Deep reasoning (diagrams, complex tasks)
- `xhigh` - Maximum (gpt-5.2 only, hardest problems)

## Model Recommendations

**Fast & Cost-Effective:**
- Default: `gpt-5.4-mini` with `medium` reasoning
- Classification: `gpt-5.4-mini` with `low` reasoning

**High Quality:**
- Diagrams: `gpt-5.4` with `high` reasoning
- Solutions: `gpt-5.4` with `high` reasoning
- Variants: `gpt-5.4` with `high` reasoning

**xAI Grok:**
- General: `grok-4-1-fast-reasoning`
- Code: `grok-code-fast-1`

**Google Gemini:**
- Fast: `gemini-3-flash-preview`
- Quality: `gemini-2.5-pro`

## Configuration Files

- **Global**: `~/.config/vbagent/models.json` (Linux/macOS)
- **Global**: `%APPDATA%\vbagent\models.json` (Windows)
- **Workspace**: `.vbagent.json` (project directory)

Workspace config overrides global config.

## Environment Variables

```bash
export OPENAI_API_KEY=sk-xxx
export XAI_API_KEY=xai-xxx
export GOOGLE_API_KEY=your-key
```

## Example Workflows

### New Chemistry Project
```bash
cd my-chemistry-project
vbagent config init --quick  # Select: chemistry
vbagent config set organic_structure --model gpt-5.4 --reasoning high -w
vbagent config set scanner --model gpt-5.4-mini --reasoning medium -w
```

### Switch to xAI Grok
```bash
vbagent config provider xai --api-key xai-xxx
# Model group auto-applied, all agents now use Grok models
```

### Cost Optimization
```bash
# Fast models for simple tasks
vbagent config set classifier --model gpt-5.4-mini --reasoning low
vbagent config set scanner --model gpt-5.4-mini --reasoning medium

# Powerful models for complex tasks
vbagent config set tikz --model gpt-5.4 --reasoning high
vbagent config set solution --model gpt-5.4 --reasoning high
```

### Debug Mode
```bash
vbagent config debug on
vbagent config log-level DEBUG
# ... test your changes ...
vbagent config debug off
vbagent config log-level INFO
```

## Tips

1. Use `--workspace` (`-w`) to save project-specific settings
2. Commit `.vbagent.json` to git for team consistency
3. Use environment variables for API keys (don't commit)
4. Start with model groups, then fine-tune individual agents
5. Enable debug mode when developing/testing

## Help

```bash
vbagent config --help
vbagent config <command> --help
```
