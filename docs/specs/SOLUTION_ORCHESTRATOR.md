# Solution Orchestrator Implementation

## Overview

The Solution Orchestrator is a new system that coordinates specialized agents to generate complex solutions with diagrams, calculus, and multiple steps.

## Architecture

### Three-Phase Process

1. **Planning Phase** (`SolutionPlanner`)
   - Analyzes solution image
   - Identifies required components (diagrams, calculus, tables, etc.)
   - Creates execution plan with agent calls

2. **Execution Phase** (`SolutionExecutor`)
   - Calls specialist agents as specified in plan
   - Passes focused context to each agent
   - Collects outputs from all agents

3. **Assembly Phase** (`SolutionAssembler`)
   - Combines agent outputs into unified solution
   - Ensures proper LaTeX structure
   - Maintains logical flow

### Specialist Agents

The orchestrator can call these existing agents:
- `fbd` - Free body diagrams
- `circuit` - Circuit diagrams
- `graph` - Graphs and plots
- `ray_diagram` - Ray diagrams for optics
- `optics` - Optical system diagrams
- `calculus` - Calculus-heavy content
- `table` - Data tables
- `tikz` - Generic TikZ diagrams
- `text` - Text-heavy explanations

## File Structure

```
vbagent/
├── agents/
│   ├── solution_orchestrator.py      # Main orchestrator
│   └── orchestration/
│       ├── __init__.py
│       ├── planner.py                # Planning agent
│       ├── executor.py               # Execution coordinator
│       └── assembler.py              # Solution assembler
├── models/
│   └── orchestration.py              # Data models
└── prompts/
    └── solution_orchestrator.py      # Prompts for planner & assembler
```

## Usage

### Library API

```python
from vbagent import create_solution_orchestrator

orchestrator = create_solution_orchestrator()

result = orchestrator.generate_solution(
    image_path="solution.png",
    problem_context="Mechanics problem on friction",
    question_type="subjective",
    verbose=True,
)

print(result.latex)
print(f"Agents used: {[o.agent for o in result.agent_outputs]}")
```

### CLI

```bash
# Use orchestrator for complex solutions
vbagent scan -i solution.png --orchestrate

# With compilation
vbagent scan -i solution.png --orchestrate -c

# With verbose output
vbagent scan -i solution.png --orchestrate --verbose-compile
```

## Data Models

### SolutionPlan
- `structure`: Overall solution structure (multi_step, proof, direct)
- `steps`: High-level steps
- `agent_calls`: List of AgentCall objects
- `assembly_order`: Order to assemble components

### AgentCall
- `agent`: Which specialist agent to call
- `instruction`: Specific instruction for the agent
- `context`: Context about where this fits
- `placement`: Where to place in solution
- `image_focus`: Optional focus area in image

### AgentOutput
- `agent`: Agent that generated this
- `placement`: Where to place this
- `content`: Generated LaTeX content
- `success`: Whether generation succeeded
- `error`: Error message if failed

### SolutionResult
- `latex`: Complete solution LaTeX
- `plan`: Original execution plan
- `agent_outputs`: All agent outputs
- `metadata`: Additional metadata

## Benefits

1. **Modular**: Each agent does one thing well
2. **Reusable**: Leverages existing specialized agents
3. **Flexible**: Can add new specialists without changing orchestrator
4. **Debuggable**: Can inspect plan before execution
5. **Efficient**: Only calls agents actually needed
6. **Better Quality**: Specialized agents produce better output for their domain

## Integration

- Exported in public API: `from vbagent import create_solution_orchestrator`
- Available in CLI: `vbagent scan --orchestrate`
- Works with existing classification and compilation systems
- Compatible with all question types

## Example Output

```
Phase 1: Planning...
  Structure: multi_step
  Steps: 3
  Agent calls: 2
    - fbd at step_1
    - calculus at step_3

Phase 2: Executing specialist agents...
  Completed: 2/2 agents

Phase 3: Assembling solution...
  ✓ Solution assembled
```

## Future Enhancements

- Add more specialist agents (chemistry, biology-specific)
- Parallel execution of independent agents
- Caching of agent outputs
- Interactive plan editing
- Solution quality scoring
