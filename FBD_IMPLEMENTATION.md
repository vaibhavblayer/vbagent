# FBD Agent Implementation Summary

## What Was Added

A specialized Free Body Diagram (FBD) agent for generating physics FBD TikZ code.

## Files Created

1. **`vbagent/agents/fbd.py`** (195 lines)
   - `generate_fbd()` - Main function to generate FBD TikZ code
   - `create_fbd_agent()` - Agent factory with context support
   - `validate_fbd_output()` - FBD-specific validation
   - `search_fbd_reference` - Tool for searching FBD examples

2. **`vbagent/prompts/fbd.py`** (95 lines)
   - `SYSTEM_PROMPT` - FBD-specific instructions and conventions
   - `USER_TEMPLATE` - Template for description-based generation
   - `USER_TEMPLATE_FROM_PROBLEM` - Template for problem-based generation

3. **`vbagent/cli/fbd.py`** (145 lines)
   - CLI command: `vbagent fbd`
   - Supports image, description, or problem text input
   - Compilation and validation support

## Files Modified

1. **`vbagent/agents/__init__.py`**
   - Added FBD imports to TYPE_CHECKING
   - Added to __all__ exports
   - Added lazy loading in __getattr__

2. **`vbagent/__init__.py`**
   - Added FBD to public API exports
   - Added to lazy loading system

3. **`vbagent/config.py`**
   - Added "fbd" to AGENT_TYPES
   - Added FBD to MODEL_GROUPS for all providers
   - Added `fbd` field to VBAgentConfig dataclass

4. **`vbagent/cli/main.py`**
   - Added "fbd" to LAZY_SUBCOMMANDS
   - Added to CLI help text

## Usage

### Library API
```python
from vbagent import generate_fbd

# From description
fbd_code = generate_fbd(description="Block on inclined plane at 30 degrees")

# From image
fbd_code = generate_fbd(image_path="scenario.png")

# From problem text
fbd_code = generate_fbd(problem_text=latex_problem)
```

### CLI
```bash
# From description
vbagent fbd -d "Block on inclined plane at 30 degrees"

# From image
vbagent fbd -i scenario.png -o fbd.tex

# From problem with compilation
vbagent fbd -t problem.tex -c

# With reference examples
vbagent fbd -d "Pulley system" --ref ./fbd_examples/ -o output.tex
```

### Configuration
```bash
# View FBD agent config
vbagent config show

# Configure FBD agent
vbagent config set fbd --model grok-4 --reasoning high
```

## Key Features

1. **Specialized Prompts**: FBD-specific physics conventions (force directions, labels, coordinate systems)
2. **Reference Integration**: Can search FBD examples from reference store
3. **Validation**: Checks for arrows, coordinate systems, and proper structure
4. **Multi-input**: Supports description, image, or problem text
5. **Compilation**: Built-in LaTeX compilation with auto-fix on errors
6. **Configurable**: Per-agent model and reasoning settings

## Architecture Pattern

Follows the existing TikZ agent pattern:
- Agent creation with context support
- Reference tool for searching examples
- Clean LaTeX output (removes markdown artifacts)
- Lazy loading for fast CLI startup
- Integration with compile system

## Total Code Added

- **~435 lines** of focused, minimal code
- Fully integrated with existing infrastructure
- No breaking changes to existing functionality

## Next Steps

1. Add curated FBD examples to reference store with metadata:
   ```latex
   % diagram_type: free_body
   % topic: Kinematics
   % tags: inclined_plane, friction
   ```

2. Test with real physics problems and iterate on prompts

3. Consider adding FBD-specific checkers (force balance validation, etc.)

4. Optionally integrate into `process` pipeline for auto-detection
