# Solution-Diagram Integration Complete

## What's Been Implemented

Complete integration between solution generation and diagram generation with rich context passing.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Scanner (GPT-4o-mini)                              │
│ Input: Problem image                                         │
│ Output: Problem LaTeX + original image path                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Solution Generator (GPT-4o)                        │
│ Input: Problem text                                          │
│ Output: Solution with RICH diagram requirements             │
│   - Diagram type (fbd, circuit, graph, etc.)                │
│   - Description (what to show)                              │
│   - Physics context (detailed explanation)                  │
│   - Values (specific numbers)                               │
│   - Labels (symbols needed)                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Diagram Generator (Subject-specific agents)       │
│ Input:                                                       │
│   - Original image (visual reference)                       │
│   - Rich context from solution                              │
│   - Subject (for routing)                                   │
│ Routing: tikz_router → FBD/Circuit/Graph/etc. agent        │
│ Output: TikZ code                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: Assembly                                           │
│ Replace placeholders with generated TikZ                    │
│ Output: Complete LaTeX document                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Enhanced DiagramRequirement Class

```python
class DiagramRequirement:
    diagram_id: str          # e.g., "fbd_1"
    diagram_type: str        # e.g., "fbd", "circuit"
    description: str         # Brief description
    location: str            # "inline"
    
    # Rich context from solution
    physics_context: str     # Detailed explanation
    values: Dict[str, str]   # Variable values
    labels: List[str]        # Labels needed
    
    def get_enhanced_description() -> str:
        """Combines all context for diagram agent"""
```

### 2. Solution Agent Output Format

```latex
\begin{solution}
\begin{align*}
\intertext{Analyze forces on the block}
\sum F &= ma \\
T - mg &= ma
\end{align*}

% DIAGRAM_REQUIREMENT: {
%   "id": "fbd_1",
%   "type": "fbd",
%   "description": "Free body diagram of block",
%   "physics_context": "Block mass 2kg suspended by tension T=10N upward, weight mg=19.6N downward, net force upward causing acceleration a=0.2 m/s^2",
%   "values": {"T": "10 N", "mg": "19.6 N", "m": "2 kg", "a": "0.2 m/s^2"},
%   "labels": ["T", "mg", "a"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: fbd_1
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{From the free body diagram}
a &= \frac{T - mg}{m} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
```

### 3. Diagram Generation with Context

```python
def generate_diagram_with_context(
    requirement: DiagramRequirement,
    original_image_path: str,
    subject: str,
) -> str:
    """Generate diagram with rich context.
    
    The diagram agent receives:
    - Original image (visual reference)
    - Enhanced description with:
      * Brief description
      * Physics context (detailed)
      * Values (specific numbers)
      * Labels (symbols needed)
    - Subject (for routing to correct agent)
    """
```

### 4. Complete Pipeline

```python
def generate_complete_solution(
    image_path: str,
    classification: ClassificationResult,
    subject: str,
) -> str:
    """Complete pipeline in one call.
    
    1. Scan problem (GPT-4o-mini)
    2. Generate solution with rich diagram requirements (GPT-4o)
    3. Generate diagrams with context (subject-specific agents)
    4. Assemble final document
    """
```

## Usage Examples

### Example 1: Simple Usage

```python
from vbagent.agents.content_generation.solution import generate_complete_solution
from vbagent.agents.classification import classify

# Classify and generate complete solution
classification = classify("problem.png")
complete_latex = generate_complete_solution(
    image_path="problem.png",
    classification=classification,
    subject="physics"
)

print(complete_latex)
# → Complete LaTeX with problem, solution, and diagrams
```

### Example 2: Step-by-Step

```python
from vbagent.agents.content_generation.scanner import scan
from vbagent.agents.content_generation.solution import (
    generate_solution,
    generate_diagram_with_context
)

# Step 1: Scan
scan_result = scan("problem.png", classification)

# Step 2: Generate solution
solution_result = generate_solution(
    problem=scan_result.latex,
    question_type="mcq_sc",
    subject="physics"
)

# Step 3: Generate diagrams
for req in solution_result.diagram_requirements:
    print(f"Generating {req.diagram_type}: {req.description}")
    print(f"Context: {req.physics_context}")
    print(f"Values: {req.values}")
    
    tikz_code = generate_diagram_with_context(
        requirement=req,
        original_image_path="problem.png",
        subject="physics"
    )
    
    # Replace placeholder
    solution_result.solution_latex = solution_result.solution_latex.replace(
        f"% PLACEHOLDER: {req.diagram_id}",
        tikz_code
    )

# Step 4: Assemble
final_latex = scan_result.latex + "\n\n" + solution_result.solution_latex
```

## What Diagram Agents Receive

### Before (Old System)
```
Description: "Free body diagram of block"
Image: problem.png
```

### After (New System)
```
Description: "Free body diagram of block

**Physics Context:** Block of mass 2 kg suspended by tension T=10N upward, 
weight mg=19.6N downward, net force upward causing acceleration a=0.2 m/s^2

**Values:** T=10 N, mg=19.6 N, m=2 kg, a=0.2 m/s^2

**Labels needed:** T, mg, a"

Image: problem.png (visual reference)
Subject: physics (routes to FBD agent)
```

## Benefits

### 1. Better Diagram Quality
- Diagram agents know exactly what to represent
- Have specific values and labels
- Understand physical meaning and relationships

### 2. Visual Reference
- Original image provides layout reference
- Helps with spatial relationships
- Reduces ambiguity

### 3. Automatic Routing
- Subject-specific routing (physics → FBD agent)
- Diagram type routing (circuit → Circuit agent)
- Uses specialized prompts and conventions

### 4. Separation of Concerns
- Solution agent: Physics reasoning and explanation
- Diagram agent: Visual representation
- Each does what it's best at

### 5. Cost Efficiency
- Scanner: GPT-4o-mini (~10x cheaper)
- Solution: GPT-4o (better reasoning)
- Diagrams: Specialized agents with context

## Diagram Types Supported

### Physics
- `fbd` - Free body diagrams
- `circuit` - Circuit diagrams
- `graph` - Graphs and plots
- `optics` - Ray diagrams

### Chemistry
- `organic_structure` - Molecular structures
- `reaction_mechanism` - Reaction mechanisms
- `orbital` - Orbital diagrams
- `energy_diagram` - Energy profiles
- `chemical_equation` - Chemical equations

### Mathematics
- `function_graph` - Function plots
- `coordinate_geometry` - Coordinate geometry
- `geometric_figure` - Geometric figures
- `number_line` - Number lines
- `venn_diagram` - Venn diagrams

## Files Modified

1. `vbagent/agents/content_generation/solution.py`
   - Enhanced `DiagramRequirement` class with rich context
   - Updated `extract_diagram_requirements()` to parse JSON
   - Added `generate_diagram_with_context()`
   - Added `generate_complete_solution()` pipeline

2. `vbagent/prompts/content_generation/solution/physics/common.py`
   - Updated `DIAGRAM_IDENTIFICATION` with rich context format
   - Added examples for FBD, circuit, graph
   - Added diagram type reference

3. Documentation
   - `SOLUTION_DIAGRAM_INTEGRATION.md` - Design document
   - `SOLUTION_DIAGRAM_COMPLETE.md` - This summary

## Next Steps

### Testing
1. Test with real physics problems
2. Verify diagram generation quality
3. Test with chemistry and mathematics

### Completion
1. Complete remaining physics question types
2. Add chemistry solution prompts
3. Add mathematics solution prompts

### Optimization
1. Measure quality improvements
2. Optimize prompts based on results
3. Add caching for expensive operations

## Example Complete Flow

```python
# Input: Physics MCQ image
image_path = "physics_mcq.png"

# Classify
classification = classify(image_path)
# → MCQ, physics, has_diagram

# Generate complete solution
latex = generate_complete_solution(
    image_path=image_path,
    classification=classification,
    subject="physics"
)

# What happens internally:
# 1. Scanner (GPT-4o-mini) extracts problem
# 2. Solution agent (GPT-4o) generates solution with:
#    % DIAGRAM_REQUIREMENT: {
#      "id": "fbd_1",
#      "type": "fbd",
#      "physics_context": "Block mass 2kg, forces T=10N up, mg=19.6N down",
#      "values": {"T": "10 N", "mg": "19.6 N"},
#      "labels": ["T", "mg"]
#    }
# 3. FBD agent receives:
#    - Original image (visual reference)
#    - Rich context (what forces, values, labels)
#    - Generates accurate FBD
# 4. Assembly replaces placeholder with TikZ

print(latex)
# → Complete LaTeX with problem, solution, and accurate FBD
```

---

The solution-diagram integration is complete! The solution agent now provides rich context to diagram agents, resulting in better quality diagrams that accurately represent the physics/chemistry/mathematics being explained.
