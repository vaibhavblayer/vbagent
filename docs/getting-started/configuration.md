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
- `diagram_classifier` - Standalone diagram classification
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

### Agent Logging

```bash
# Verbose JSON input, usage, and output panels (default)
vbagent config log-level INFO

# Add tracebacks and lifecycle diagnostics
vbagent config debug on

# Persist metadata-only lifecycle events at any level
export VBAGENT_LOG_FILE=.vbagent/logs/agent-events.jsonl
```

INFO mode prints every agent input, usage record, and output as structured JSON.
DEBUG mode additionally records full response IDs, queue and request durations,
token usage, selected key names, and completion/failure/cancellation state.
Prompt and model output bodies are not written to JSONL. Quiet parallel workers
suppress terminal rendering while still writing lifecycle events when event
logging is enabled.

### OpenAI prompt caching and profile rotation

Official GPT-5.6 agent calls automatically use an explicit cache breakpoint
after the stable agent instructions and a stable `prompt_cache_key`. This
applies to the existing scan, solve, classify, diagram, review, and syllabus
authoring agents; individual workflows do not need separate cache code.

Configure multiple OpenAI profiles with the key manager:

```bash
vbagent keys add --name project-a --api-key "$OPENAI_PROJECT_A_KEY" \
  --cache-domain openai-org-main:global
vbagent keys add --name project-b --api-key "$OPENAI_PROJECT_B_KEY" \
  --cache-domain openai-org-main:global
vbagent keys list
```

`cache-domain` is a local routing label, not a value discovered or verified by
OpenAI. Give profiles the same label **only** when their keys belong to the same
OpenAI organization and processing region. Prompt caches are scoped by those
provider boundaries. When the option is omitted, VBAgent safely treats the
profile as an isolated cache domain. Restore that default with:

```bash
vbagent keys update project-b --isolated-cache
```

A stable cache group first selects a domain with rendezvous hashing. The
configured `least_used`, `round_robin`, or `random` strategy then rotates only
among profiles inside that domain. A terminal 401, 403, or 429 can fail over to
another managed profile; a `previous_response_id` chain remains pinned to its
original credentials.

Cache routes use four deterministic shards by default so large parallel batches
do not overload one provider cache route. For lower-throughput runs, one shard
maximizes warm-cache reuse. Increase the value only for sustained high request
rates:

```bash
export VBAGENT_PROMPT_CACHE_SHARDS=1   # valid range: 1-64
```

Lifecycle and authoring usage records distinguish token cache reads, cache
writes, and request-level hits. Request hit percentage is shown as `n/a` when
the SDK/provider does not supply per-request usage entries. For GPT-5.6,
`effective_input_multiplier` applies the current ordinary/read/write cache
multipliers to make write-heavy cold runs visible. See the
[OpenAI prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)
for the provider contract and current pricing multipliers.

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
