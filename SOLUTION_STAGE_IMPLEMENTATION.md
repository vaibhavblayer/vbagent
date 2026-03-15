# Solution Stage Implementation Guide

## What's Been Created

### 1. Prompt Structure
```
vbagent/prompts/content_generation/solution/
├── __init__.py                    # Main entry point
├── physics/
│   ├── __init__.py               # Physics prompt router
│   ├── common.py                 # Shared components
│   ├── mcq_sc.py                 # MCQ single correct
│   └── subjective.py             # Subjective questions
├── chemistry/
│   └── __init__.py               # Placeholder (TODO)
└── mathematics/
    └── __init__.py               # Placeholder (TODO)
```

### 2. Solution Agent
```
vbagent/agents/content_generation/solution.py
```

Features:
- `create_solution_agent()`: Creates agent with subject/type-specific prompts
- `generate_solution()`: Main function to generate solutions
- `extract_diagram_requirements()`: Parses `\placeholder{}{}` from solution
- `infer_diagram_type()`: Automatically detects diagram type from description
- `SolutionResult`: Data class for solution output
- `DiagramRequirement`: Data class for diagram needs

## How to Use

### Basic Usage

```python
from vbagent.agents.content_generation.solution import generate_solution

# For MCQ
result = generate_solution(
    problem=r"\item A block of mass 2 kg...",
    question_type="mcq_sc",
    options=["A) 10 N", "B) 20 N", "C) 30 N", "D) 40 N"],
    subject="physics"
)

# For Subjective
result = generate_solution(
    problem=r"\item Derive the equation of motion...",
    question_type="subjective",
    subject="physics"
)

# Access results
print(result.solution_latex)  # LaTeX solution
print(result.diagram_requirements)  # List of diagrams needed
```

### Integration with Scanner

```python
from vbagent.agents.content_generation.scanner import scan
from vbagent.agents.content_generation.solution import generate_solution

# Stage 1: Scan problem
scan_result = scan(image_path, classification)

# Stage 2: Generate solution
solution_result = generate_solution(
    problem=scan_result.latex,  # Problem from scanner
    question_type=classification.question_type,
    subject="physics"
)

# Stage 3: Generate diagrams (existing functionality)
for req in solution_result.diagram_requirements:
    diagram_latex = generate_diagram(req.diagram_type, req.description)
    # Replace placeholder with actual diagram
    solution_result.solution_latex = solution_result.solution_latex.replace(
        f"\\placeholder{{{req.diagram_id}}}{{{req.description}}}",
        diagram_latex
    )
```

## Diagram Placeholder Format

Solutions use placeholders that will be replaced with actual diagrams:

```latex
\placeholder{diagram_id}{description}
```

Examples:
```latex
\placeholder{fbd_1}{Free body diagram showing forces on block on incline}
\placeholder{circuit_1}{Circuit with two resistors in series and one in parallel}
\placeholder{graph_1}{Graph of velocity vs time showing constant acceleration}
```

The `extract_diagram_requirements()` function automatically:
1. Finds all placeholders
2. Extracts ID and description
3. Infers diagram type (fbd, circuit, graph, etc.)
4. Returns list of `DiagramRequirement` objects

## Next Steps

### 1. Complete Physics Prompts
- [ ] Create `mcq_mc.py` (multiple correct)
- [ ] Create `assertion_reason.py`
- [ ] Create `passage.py`
- [ ] Create `match.py`

### 2. Create Chemistry Prompts
- [ ] `chemistry/common.py`
- [ ] `chemistry/mcq_sc.py`
- [ ] `chemistry/subjective.py`
- [ ] etc.

### 3. Create Mathematics Prompts
- [ ] `mathematics/common.py`
- [ ] `mathematics/mcq_sc.py`
- [ ] `mathematics/subjective.py`
- [ ] etc.

### 4. Create Assembler Agent
```python
# vbagent/agents/content_generation/assembler.py

def assemble_document(
    problem: str,
    solution: str,
    diagrams: Dict[str, str],
    metadata: dict
) -> str:
    """Assemble final LaTeX document with all components."""
    pass
```

### 5. Update CLI Commands

Add new command for solution-only generation:
```bash
vbagent generate solution <problem_file> --type mcq_sc --subject physics
```

### 6. Model Configuration

Add model selection to config:
```yaml
# config.yaml
models:
  scanner: "gpt-4o-mini"      # Cheaper for OCR
  solution: "gpt-4o"          # Better for reasoning
  diagram: "gpt-4o"           # For diagram generation
```

### 7. Testing

Create tests for:
- Solution generation with different question types
- Diagram requirement extraction
- Diagram type inference
- Integration with scanner

## Benefits of This Architecture

### Cost Efficiency
- Scanner uses GPT-4o-mini (~10x cheaper)
- Solution uses GPT-4o only for reasoning
- Can regenerate solutions without rescanning

### Quality
- Focused prompts for each stage
- Better solution quality with dedicated reasoning
- Subject-specific optimization

### Flexibility
- Can swap models per stage
- Can regenerate any stage independently
- Easy to add new subjects/question types

### Maintainability
- Clear separation of concerns
- Modular prompt organization
- Easy to update prompts per subject

## Example Workflow

```python
# Complete pipeline
from vbagent.agents.classification import classify
from vbagent.agents.content_generation.scanner import scan
from vbagent.agents.content_generation.solution import generate_solution
from vbagent.agents.diagram.tikz_router import route_and_generate

# 1. Classify (GPT-4o-mini)
classification = classify(image_path)

# 2. Scan problem (GPT-4o-mini)
scan_result = scan(image_path, classification)

# 3. Generate solution (GPT-4o)
solution_result = generate_solution(
    problem=scan_result.latex,
    question_type=classification.question_type
)

# 4. Generate diagrams (GPT-4o, subject-specific)
for req in solution_result.diagram_requirements:
    diagram = route_and_generate(
        diagram_type=req.diagram_type,
        description=req.description
    )
    # Replace placeholder
    solution_result.solution_latex = solution_result.solution_latex.replace(
        f"\\placeholder{{{req.diagram_id}}}{{{req.description}}}",
        diagram
    )

# 5. Assemble final document
final_latex = scan_result.latex + "\n" + solution_result.solution_latex
```

## Configuration Example

```python
# config.yaml
content_generation:
  pipeline:
    stages:
      - name: "classification"
        model: "gpt-4o-mini"
        
      - name: "scanner"
        model: "gpt-4o-mini"
        use_context: true
        
      - name: "solution"
        model: "gpt-4o"
        use_context: true
        
      - name: "diagram"
        model: "gpt-4o"
        router: "tikz_router"
```
