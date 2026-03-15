# Solution Architecture Redesign

## Overview
Separating scanning and solution generation into distinct stages with subject-specific organization.

## Current Architecture
```
Scanner Agent (GPT-4o) → Complete LaTeX (problem + solution + diagrams)
```

## New Architecture
```
Stage 1: Scanner (GPT-4o-mini/codex-mini)
  ↓ Outputs: problem + options + diagram placeholders + metadata
  
Stage 2: Solution Generator (GPT-4o)
  ↓ Outputs: solution + diagram requirements
  
Stage 3: Diagram Generator (Subject-specific agents)
  ↓ Outputs: TikZ code inserted at placeholders
  
Stage 4: Assembly
  → Final LaTeX document
```

## Benefits

### Cost Efficiency
- Scanner uses cheaper model (GPT-4o-mini) for OCR-like tasks
- Solution uses better model only for complex reasoning
- Diagram generation uses specialized agents

### Quality Improvements
- Focused prompts for each stage
- Better solution quality with dedicated reasoning
- Modular diagram generation
- Subject-specific optimization at each stage

### Flexibility
- Can regenerate solutions without rescanning
- Can add/modify diagrams independently
- Easy to swap models per stage

## Directory Structure

```
vbagent/
├── prompts/
│   ├── content_generation/
│   │   ├── scanner/              # Stage 1: Problem extraction
│   │   │   ├── physics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── common.py     # Shared components
│   │   │   │   ├── mcq_sc.py
│   │   │   │   ├── mcq_mc.py
│   │   │   │   ├── subjective.py
│   │   │   │   └── ...
│   │   │   ├── chemistry/
│   │   │   └── mathematics/
│   │   │
│   │   └── solution/             # Stage 2: Solution generation (NEW)
│   │       ├── physics/
│   │       │   ├── __init__.py
│   │       │   ├── common.py
│   │       │   ├── mcq_sc.py
│   │       │   ├── mcq_mc.py
│   │       │   ├── subjective.py
│   │       │   └── ...
│   │       ├── chemistry/
│   │       └── mathematics/
│   │
│   └── diagram/                  # Stage 3: Diagram generation (existing)
│       ├── physics/
│       ├── chemistry/
│       └── mathematics/
│
└── agents/
    ├── content_generation/
    │   ├── scanner.py            # Stage 1 agent
    │   ├── solution.py           # Stage 2 agent (NEW)
    │   └── assembler.py          # Stage 4 agent (NEW)
    │
    └── diagram/                  # Stage 3 agents (existing)
        ├── tikz_router.py
        ├── physics/
        ├── chemistry/
        └── mathematics/
```

## Stage Details

### Stage 1: Scanner (GPT-4o-mini)
**Input:** Question image
**Output:** 
```python
{
    "problem": "\\item LaTeX problem statement",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],  # if MCQ
    "diagram_placeholders": [
        {
            "id": "diagram_1",
            "location": "in_problem",  # or "in_options", "in_solution"
            "description": "circuit with resistors in series",
            "suggested_type": "circuit"
        }
    ],
    "metadata": {
        "question_type": "mcq_sc",
        "subject": "physics",
        "has_numerical": true
    }
}
```

### Stage 2: Solution Generator (GPT-4o)
**Input:** Problem + options + metadata
**Output:**
```python
{
    "solution": "\\begin{solution}...\\end{solution}",
    "diagram_requirements": [
        {
            "id": "diagram_sol_1",
            "type": "fbd",
            "description": "Free body diagram showing forces on block",
            "location": "after_step_2"
        }
    ],
    "answer": "B",  # if MCQ
    "explanation_steps": 3
}
```

### Stage 3: Diagram Generator (Existing)
**Input:** Diagram requirements
**Output:** TikZ code for each diagram

### Stage 4: Assembler
**Input:** All components
**Output:** Final LaTeX document

## Implementation Plan

### Phase 1: Create Solution Prompt Structure
1. Create `vbagent/prompts/content_generation/solution/` directory
2. Mirror scanner structure with subject-specific prompts
3. Focus prompts on solution reasoning, not OCR

### Phase 2: Create Solution Agent
1. Create `vbagent/agents/content_generation/solution.py`
2. Implement solution generation logic
3. Add diagram requirement detection

### Phase 3: Create Assembler
1. Create `vbagent/agents/content_generation/assembler.py`
2. Implement LaTeX assembly logic
3. Handle diagram placeholder replacement

### Phase 4: Update Scanner
1. Modify scanner to output structured data
2. Add diagram placeholder generation
3. Optimize for GPT-4o-mini

### Phase 5: Integration
1. Update CLI commands to use new pipeline
2. Add configuration for model selection per stage
3. Update tests

## Model Configuration

```python
# config.yaml
models:
  scanner: "gpt-4o-mini"  # or "codex-mini"
  solution: "gpt-4o"
  diagram: "gpt-4o"  # or subject-specific models
```

## Example Flow

```python
# 1. Scan problem
scan_result = scanner.scan(image_path)
# → problem, options, diagram_placeholders

# 2. Generate solution
solution_result = solution_generator.generate(
    problem=scan_result.problem,
    options=scan_result.options,
    metadata=scan_result.metadata
)
# → solution, diagram_requirements

# 3. Generate diagrams
diagrams = {}
for req in solution_result.diagram_requirements:
    diagrams[req.id] = diagram_generator.generate(req)

# 4. Assemble final document
final_latex = assembler.assemble(
    problem=scan_result.problem,
    options=scan_result.options,
    solution=solution_result.solution,
    diagrams=diagrams
)
```

## Next Steps

1. Review and approve architecture
2. Start with Phase 1 (solution prompts)
3. Implement incrementally
4. Test with existing questions
5. Measure quality improvements
