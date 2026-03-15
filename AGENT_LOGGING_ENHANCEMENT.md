# Agent Logging Enhancement

## Problem

Agent execution only showed model name in debug mode. In normal mode, you couldn't see which model or reasoning mode was being used for each agent call.

**Before (normal mode):**
```
⏳ TikZ running...
✓ TikZ completed in 39.2s
```

**Before (debug mode only):**
```
[INPUT] TikZ : gpt-5.4
⏳ TikZ running (gpt-5.4)...
[OUTPUT] TikZ : 39.24s
```

## Solution

Enhanced logging to always show model and reasoning mode, even in normal (non-debug) mode.

**After (normal mode):**
```
⏳ TikZ running (gpt-5.4, medium reasoning)...
✓ TikZ completed in 39.2s (gpt-5.4, medium reasoning)
```

**After (with spinner):**
```
⠋ TikZ │ gpt-5.4 │ medium reasoning
✓ TikZ completed in 39.2s (gpt-5.4, medium reasoning)
```

## Changes Made

### File Modified
- `vbagent/agents/base.py` - Enhanced `run_agent_sync()` function

### What Changed

1. **Running Message** - Now includes reasoning mode:
   ```python
   # Before
   console.print(f"⏳ {agent.name} running ({model})...")
   
   # After
   console.print(f"⏳ {agent.name} running ({model}, {reasoning} reasoning)...")
   ```

2. **Completion Message** - Now includes model and reasoning:
   ```python
   # Before
   console.print(f"✓ {agent.name} completed in {duration:.1f}s")
   
   # After
   console.print(f"✓ {agent.name} completed in {duration:.1f}s ({model}, {reasoning} reasoning)")
   ```

3. **Spinner Display** - Already showed model and reasoning (no change needed)

## Benefits

✅ **Transparency**: Always see which model is being used  
✅ **Debugging**: Easier to identify which agent used which model  
✅ **Cost Tracking**: Know which expensive models are being called  
✅ **Reasoning Visibility**: See which reasoning mode (low/medium/high) is active  
✅ **Consistency**: Same information in debug and normal modes  

## Example Output

### Normal Processing

```bash
$ vbagent process -i image.png

Stage 1: Classifying image...
⏳ Classifier running (gpt-4o, none reasoning)...
✓ Classifier completed in 2.3s (gpt-4o, none reasoning)

Stage 2+3: Scanning & TikZ (parallel)...
⏳ Scanner-subjective-physics running (gpt-5.4, medium reasoning)...
⏳ TikZ running (gpt-5.4, medium reasoning)...
✓ Scanner-subjective-physics completed in 39.2s (gpt-5.4, medium reasoning)
✓ TikZ completed in 45.1s (gpt-5.4, medium reasoning)
```

### With Spinner (Default)

```bash
$ vbagent process -i image.png

Stage 1: Classifying image...
⠋ Classifier │ gpt-4o │ none reasoning
✓ Classifier completed in 2.3s (gpt-4o, none reasoning)

Stage 2+3: Scanning & TikZ (parallel)...
⠋ Scanner-subjective-physics │ gpt-5.4 │ medium reasoning
⠋ TikZ │ gpt-5.4 │ medium reasoning
✓ Scanner-subjective-physics completed in 39.2s (gpt-5.4, medium reasoning)
✓ TikZ completed in 45.1s (gpt-5.4, medium reasoning)
```

### Debug Mode (Most Verbose)

```bash
$ vbagent process -i image.png  # with debug=true in config

[INPUT] Classifier : gpt-4o
📷 image/png base64 ~97.7 KB
Classify this question image...

⏳ Classifier running (gpt-4o, none reasoning)...

[OUTPUT] Classifier : 2.34s
{
  "subject": "physics",
  "question_type": "subjective",
  ...
}
✓ Classifier completed in 2.3s (gpt-4o, none reasoning)
```

## Reasoning Modes

The logging now shows which reasoning mode is active:

| Mode | Description | Use Case |
|------|-------------|----------|
| `none` | No reasoning | Fast classification, simple tasks |
| `low` | Basic reasoning | Standard processing |
| `medium` | Moderate reasoning | Complex problems, TikZ generation |
| `high` | Deep reasoning | Very complex problems, variants |

## Configuration

Reasoning modes are configured per agent in `.vbagent.json`:

```json
{
  "agents": {
    "classifier": {
      "model": "gpt-4o",
      "reasoning_effort": "none"
    },
    "content_generation.scanner": {
      "model": "gpt-5.4",
      "reasoning_effort": "medium"
    },
    "diagram.tikz": {
      "model": "gpt-5.4",
      "reasoning_effort": "medium"
    }
  }
}
```

## Cost Implications

Now you can easily see which agents are using expensive models:

```
⏳ Scanner running (gpt-5.4, medium reasoning)...  ← Expensive!
⏳ Classifier running (gpt-4o, none reasoning)...  ← Cheaper
```

This helps you:
- Identify cost-heavy operations
- Optimize model selection
- Adjust reasoning modes for cost/quality tradeoff

## Testing

The enhancement works in all modes:

```bash
# Normal mode (spinner)
vbagent process -i image.png

# Verbose mode (no spinner, shows messages)
vbagent process -i image.png -v

# Debug mode (full logging)
# Set debug: true in .vbagent.json
vbagent process -i image.png
```

## Summary

Agent execution now always shows:
1. **Model name** (e.g., gpt-5.4, gpt-4o)
2. **Reasoning mode** (none, low, medium, high)
3. **Duration** (in seconds)

This provides full transparency into which models and reasoning modes are being used for each agent call, helping with debugging, cost tracking, and optimization.
