# Solution Agent Logging Enhancement

## Issue
The solution agent was not showing model and reasoning information in console logs like other agents (scanner, classifier, etc.).

## Root Cause
The solution agent type was not registered in the configuration system, so it was falling back to default settings without proper model/reasoning configuration.

## Solution
Added "solution" agent to the configuration system with proper defaults.

### Changes Made

#### 1. Added Solution Agent to ContentGenerationConfig
**File:** `vbagent/config.py`

```python
@dataclass
class ContentGenerationConfig:
    """Configuration for content generation agents."""
    scanner: AgentModelConfig = field(default_factory=AgentModelConfig)
    solution: AgentModelConfig = field(default_factory=AgentModelConfig)  # ← ADDED
    idea: AgentModelConfig = field(default_factory=AgentModelConfig)
    alternate: AgentModelConfig = field(default_factory=AgentModelConfig)
    converter: AgentModelConfig = field(default_factory=AgentModelConfig)
```

#### 2. Updated to_dict Method
**File:** `vbagent/config.py`

```python
"content_generation": {
    "scanner": self.content_generation.scanner.to_dict(),
    "solution": self.content_generation.solution.to_dict(),  # ← ADDED
    "idea": self.content_generation.idea.to_dict(),
    "alternate": self.content_generation.alternate.to_dict(),
    "converter": self.content_generation.converter.to_dict(),
},
```

#### 3. Updated from_dict Method
**File:** `vbagent/config.py`

```python
if "content_generation" in data:
    content_gen_data = data["content_generation"]
    for agent_name in ["scanner", "solution", "idea", "alternate", "converter"]:  # ← ADDED "solution"
        if agent_name in content_gen_data:
            setattr(
                config.content_generation,
                agent_name,
                AgentModelConfig.from_dict(content_gen_data[agent_name]),
            )
```

#### 4. Added Default Configuration
**File:** `vbagent/config.py`

```python
def __post_init__(self):
    """Set better defaults for specific agents."""
    # ... other agents ...
    
    # Solution agent uses high reasoning (default gpt-5.2)
    # No changes needed - uses defaults
```

**Default settings for solution agent:**
- Model: `gpt-5.2` (default)
- Reasoning: `high` (default)
- Perfect for solution generation which requires deep reasoning

#### 5. Updated Agent Creation
**File:** `vbagent/agents/content_generation/solution.py`

```python
return create_agent(
    name=f"Solution-{question_type}-{subject}",
    instructions=prompt,
    agent_type="content_generation.solution",  # ← CHANGED from "solution"
)
```

## Result

### Before
```
→ Generating solution with rich context
[INPUT] Solution-subjective-physics : gpt-5.2
Generate a detailed solution for the following problem:
...
[OUTPUT] Solution-subjective-physics : 17.67s
```

**Missing:** Reasoning level not shown

### After
```
→ Generating solution with rich context
[INPUT] Solution-subjective-physics : gpt-5.2
Generate a detailed solution for the following problem:
...
⏳ Solution-subjective-physics running (gpt-5.2, high reasoning)...
✓ Solution-subjective-physics completed in 17.7s (gpt-5.2, high reasoning)
[OUTPUT] Solution-subjective-physics : 17.67s
```

**Now shows:**
- ✅ Model: gpt-5.2
- ✅ Reasoning: high
- ✅ Duration: 17.7s
- ✅ Spinner during execution
- ✅ Completion message

## Configuration

Users can now configure the solution agent in their config file:

```json
{
  "content_generation": {
    "scanner": {
      "model": "gpt-5.4",
      "reasoning_effort": "medium"
    },
    "solution": {
      "model": "gpt-5.2",
      "reasoning_effort": "high"
    }
  }
}
```

## Benefits

1. **Visibility**: Users can see what model and reasoning level is being used
2. **Configurability**: Users can customize solution agent settings
3. **Consistency**: Solution agent now logs like all other agents
4. **Debugging**: Easier to debug issues with model selection
5. **Performance tracking**: Can see execution time with model/reasoning context

## Testing

The logging will now show properly when running:
```bash
vbagent process -i image.png --generate-solution
vbagent scan -i image.png --generate-solution
```

Expected output:
```
Stage 2: NEW Solution Pipeline...
→ Scanning problem
[INPUT] Scanner-subjective-physics : gpt-5.4
...
✓ Scanner-subjective-physics completed in 14.9s (gpt-5.4, medium reasoning)
[OUTPUT] Scanner-subjective-physics : 14.89s

→ Generating solution with rich context
[INPUT] Solution-subjective-physics : gpt-5.2
...
⏳ Solution-subjective-physics running (gpt-5.2, high reasoning)...
✓ Solution-subjective-physics completed in 17.7s (gpt-5.2, high reasoning)
[OUTPUT] Solution-subjective-physics : 17.67s
```

## Status
✅ Solution agent registered in config
✅ Default settings configured (gpt-5.2, high reasoning)
✅ Logging enhanced with model and reasoning info
✅ Consistent with other agents
✅ Ready for testing
