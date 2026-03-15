# Solution Agent: Structured Output with Diagram Requirements

## Overview

Updated solution agent to output structured JSON with:
1. Solution LaTeX
2. Diagram requirements (type, description, rich context)
3. Reasoning notes (optional)

This enables:
- Better debugging (see exact structure)
- Diagram detection and generation
- Rich context for TikZ agents
- Clean separation of concerns

## Changes Made

### 1. Created Solution Output Model
**File:** `vbagent/models/solution.py`

```python
class DiagramRequirement(BaseModel):
    """Diagram requirement with rich context."""
    diagram_type: str  # fbd, circuit, graph, optics, etc.
    description: str  # Brief description
    location: str = "inline"  # Where to place
    physics_context: Optional[str] = None  # Detailed explanation
    values: Optional[Dict[str, str]] = None  # Variable values
    labels: Optional[List[str]] = None  # Required labels

class SolutionOutput(BaseModel):
    """Structured output from solution agent."""
    solution_latex: str  # Complete solution
    diagram_requirements: List[DiagramRequirement] = []  # Diagrams needed
    reasoning_notes: Optional[str] = None  # Internal notes
```

### 2. Updated Solution Agent Creation
**File:** `vbagent/agents/content_generation/solution.py`

```python
def create_solution_agent(...):
    from vbagent.models.solution import SolutionOutput
    
    return create_agent(
        name=f"Solution-{question_type}-{subject}",
        instructions=prompt,
        agent_type="content_generation.solution",
        output_type=SolutionOutput,  # ← Structured output
    )
```

### 3. Updated Solution Generation
**File:** `vbagent/agents/content_generation/solution.py`

```python
def generate_solution(...):
    # Agent returns SolutionOutput model
    output: SolutionOutput = run_agent_sync(agent, user_message, ...)
    
    # Convert diagram requirements
    diagram_requirements = []
    for req in output.diagram_requirements:
        diagram_requirements.append(DiagramRequirement(...))
    
    return SolutionResult(
        solution_latex=output.solution_latex,
        diagram_requirements=diagram_requirements,
        raw_output=output.model_dump_json(indent=2),
    )
```

### 4. Enhanced Logging for Structured Output
**File:** `vbagent/ui/logging.py`

```python
def _format_pydantic(model):
    model_name = type(model).__name__
    
    # For SolutionOutput, show structure with LaTeX truncated
    if model_name == "SolutionOutput":
        data = model.model_dump()
        # Truncate solution_latex in JSON view
        if "solution_latex" in data:
            latex = data["solution_latex"]
            if len(latex) > 100:
                data["solution_latex"] = latex[:100] + f"... ({len(latex)} chars)"
        return _format_dict(data, _MAX_JSON_LEN)
```

## Expected Output Format

### Console Log (JSON Structure)
```
[OUTPUT] Solution-subjective-mathematics : 18.5s
{
  "solution_latex": "\\begin{solution}\n\\begin{align*}\n\\intertext{Consider intervals...}... (1234 chars)",
  "diagram_requirements": [
    {
      "diagram_type": "number_line",
      "description": "Number line showing solution intervals",
      "location": "inline",
      "physics_context": "Show critical points at x=1 and x=2, with solution regions x≤-1/2 and x≥7/2 highlighted",
      "values": {
        "critical_points": "1, 2",
        "solution_left": "x ≤ -1/2",
        "solution_right": "x ≥ 7/2"
      },
      "labels": ["x=1", "x=2", "x=-1/2", "x=7/2", "Solution regions"]
    }
  ],
  "reasoning_notes": "Used interval analysis for absolute value inequality"
}
```

### Diagram Generation Flow
```
1. Solution agent outputs structured JSON
   ├─> solution_latex: Complete solution
   └─> diagram_requirements: List of diagrams needed

2. For each diagram requirement:
   ├─> Extract type, description, context
   ├─> Route to specialized TikZ agent (number_line, fbd, circuit, etc.)
   ├─> Pass rich context (physics_context, values, labels)
   └─> Generate TikZ code

3. Insert diagrams into solution
   └─> Replace placeholders or insert at specified location

4. Return complete solution with diagrams
```

## Next Steps

### 1. Update Solution Prompts
Need to update prompts to instruct agent to output structured format:

**File:** `vbagent/prompts/content_generation/solution/physics/subjective.py`

Add to prompt:
```
## Output Format

You must output a JSON object with this structure:

{
  "solution_latex": "\\begin{solution}...\\end{solution}",
  "diagram_requirements": [
    {
      "diagram_type": "fbd|circuit|graph|optics|vector|geometry|number_line",
      "description": "Brief description of diagram",
      "location": "inline",
      "physics_context": "Detailed explanation for diagram generation",
      "values": {"key": "value", ...},
      "labels": ["label1", "label2", ...]
    }
  ],
  "reasoning_notes": "Optional internal notes"
}

### When to Include Diagrams

**Always include diagram_requirements for:**
- Forces problems → diagram_type: "fbd"
- Circuit problems → diagram_type: "circuit"
- Graphs/plots → diagram_type: "graph"
- Optics → diagram_type: "optics"
- Inequalities on number line → diagram_type: "number_line"
- Geometric problems → diagram_type: "geometry"

**Example with diagram:**
{
  "solution_latex": "\\begin{solution}\\n\\begin{align*}\\n...",
  "diagram_requirements": [
    {
      "diagram_type": "fbd",
      "description": "Free body diagram of block on incline",
      "location": "inline",
      "physics_context": "Block of mass m on incline at angle θ=30°. Forces: weight mg (downward), normal N (perpendicular to surface), friction f (along surface), acceleration a (down incline).",
      "values": {
        "m": "2 kg",
        "theta": "30°",
        "g": "9.8 m/s²",
        "a": "4.9 m/s²"
      },
      "labels": ["mg", "N", "f", "a", "θ"]
    }
  ]
}

**Example without diagram (pure calculation):**
{
  "solution_latex": "\\begin{solution}\\n\\begin{align*}\\n...",
  "diagram_requirements": []
}
```

### 2. Test with Different Problem Types

**Test cases:**
1. ✅ Mathematics inequality (number line diagram)
2. ⏳ Physics forces (FBD diagram)
3. ⏳ Physics circuit (circuit diagram)
4. ⏳ Physics motion (graph diagram)
5. ⏳ Pure calculation (no diagram)

### 3. Implement Diagram Insertion

Update `generate_complete_solution` to:
1. Get structured output from solution agent
2. For each diagram requirement:
   - Call appropriate TikZ agent with rich context
   - Insert generated TikZ at specified location
3. Return complete solution

## Benefits

### For Debugging
```
[OUTPUT] Solution-subjective-mathematics : 18.5s
{
  "solution_latex": "\\begin{solution}... (1234 chars)",
  "diagram_requirements": [
    {
      "diagram_type": "number_line",
      "description": "...",
      ...
    }
  ]
}
```
- ✅ See exact structure
- ✅ Verify diagram requirements
- ✅ Check rich context
- ✅ LaTeX truncated in JSON but full content available

### For Diagram Generation
- ✅ Automatic diagram detection
- ✅ Rich context for TikZ agents
- ✅ Proper routing to specialized agents
- ✅ Clean separation of concerns

### For Quality
- ✅ Solution agent focuses on physics/math reasoning
- ✅ TikZ agents focus on diagram generation
- ✅ Better quality for both
- ✅ Easier to debug and improve

## Status

✅ Created SolutionOutput model
✅ Updated solution agent to use structured output
✅ Enhanced logging for structured output
⏳ Need to update solution prompts
⏳ Need to test with different problem types
⏳ Need to implement diagram insertion

## Testing

Once prompts are updated, test with:
```bash
vbagent process -i images/problem.png --generate-solution
```

Expected console output:
```
[OUTPUT] Solution-subjective-mathematics : 18.5s
{
  "solution_latex": "\\begin{solution}\\n\\begin{align*}... (1234 chars)",
  "diagram_requirements": [
    {
      "diagram_type": "number_line",
      "description": "Number line showing solution intervals",
      "location": "inline",
      "physics_context": "Show critical points...",
      "values": {"critical_points": "1, 2", ...},
      "labels": ["x=1", "x=2", ...]
    }
  ],
  "reasoning_notes": null
}
```
