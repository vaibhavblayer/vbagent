# API Key Management

Multi-key rotation and usage tracking for OpenAI API keys.

## Overview

The key manager allows you to:
- Use multiple OpenAI API keys with automatic rotation
- Set daily token limits per key (separate for standard and mini models)
- Track usage in real-time
- Automatically switch keys when limits are reached

## Configuration

Configuration file: `~/.config/vbagent/api_keys.json`

### Initialize

```bash
vbagent keys init
```

This creates an example configuration file. Edit it to add your actual API keys.

### Configuration Format

```json
{
  "keys": [
    {
      "name": "key1",
      "api_key": "sk-...",
      "limits": {
        "standard": {
          "daily_limit": 1000000,
          "used_today": 0
        },
        "mini": {
          "daily_limit": 2000000,
          "used_today": 0
        }
      },
      "enabled": true
    }
  ],
  "rotation_strategy": "least_used",
  "model_categories": {
    "standard": ["gpt-5.4", "gpt-4o", "gpt-4-turbo"],
    "mini": ["gpt-5.4-mini", "gpt-4o-mini", "gpt-3.5-turbo"]
  }
}
```

## Usage

### List Keys and Usage

```bash
vbagent keys list
```

Shows all keys with current usage, limits, and remaining tokens.

### Add a Key

```bash
vbagent keys add --name mykey --api-key sk-... --standard-limit 1000000 --mini-limit 2000000
```

### Update Limits

```bash
vbagent keys update mykey --standard-limit 2000000
```

### Enable/Disable Keys

```bash
vbagent keys disable mykey
vbagent keys enable mykey
```

### Reset Daily Counters

```bash
vbagent keys reset
```

Manually reset all daily usage counters (normally resets automatically at midnight).

### Remove a Key

```bash
vbagent keys remove mykey
```

## Rotation Strategies

- `least_used`: Select the key with lowest usage in the category (default)
- `round_robin`: Rotate through keys in order
- `random`: Random selection

Edit `rotation_strategy` in the config file to change.

## Model Categories

Keys track usage separately for two categories:

- **standard**: High-capability models (gpt-5.4, gpt-4o, etc.)
- **mini**: Efficient models (gpt-5.4-mini, gpt-4o-mini, etc.)

This allows you to set different limits for different model tiers.

## How It Works

1. When key manager is enabled (config file exists), it automatically:
   - Selects an appropriate key based on the model being used
   - Tracks token usage after each API call
   - Rotates to another key if the current one hits its limit

2. If key manager is not enabled or all keys are exhausted:
   - Falls back to `OPENAI_API_KEY` environment variable

3. Usage counters reset automatically at midnight (local time)

## Backward Compatibility

- If `~/.config/vbagent/api_keys.json` doesn't exist, the system uses `OPENAI_API_KEY` env var (current behavior)
- No changes needed to existing workflows
- Enable by creating the config file, disable by removing/renaming it

## Getting API Keys

Generate separate API keys from [OpenAI Platform](https://platform.openai.com/api-keys) for better organization and tracking.

## Example Workflow

```bash
# Initialize configuration
vbagent keys init

# Edit ~/.config/vbagent/api_keys.json and add your keys

# Verify setup
vbagent keys list

# Run your pipeline - keys are used automatically
vbagent run -i question.png

# Check usage
vbagent keys list
```
