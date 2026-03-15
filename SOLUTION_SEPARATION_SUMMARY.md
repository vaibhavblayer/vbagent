# Solution Separation - Implementation Summary

## What You Proposed

Separate the scanning and solution generation into distinct stages:

1. **Scanner Stage** (GPT-4o-mini/codex-mini)
   - Extract problem statement
   - Extract options (if MCQ)
   - Identify diagram needs in problem
   - Output structured data

2. **Solution Stage** (GPT-4o)
   - Generate step-by-step solution
   - Identify diagram needs in solution
   - Output solution with diagram placeholders

3. **Diagram Stage** (Existing agents)
   - Generate diagrams based on requirements
   - Insert into appropriate locations

## What's Been Implemented

### ✅ Architecture Design
- Complete architecture documented in `SOLUTION_ARCHITECTURE_REDESIGN.md`
- Clear separation of stages with data flow
- Model configuration strategy

### ✅ Prompt Structure
Created subject-organized solution prompts:
```
vbagent/prompts/content_generation/solution/
├── __init__.py                    # Router
├── physics/
│   ├── __init__.py               # Physics router
│   ├── common.py                 # Shared components
│   ├── mcq_sc.py                 # MCQ single correct
│   └── subjective.py             # Subjective questions
├── chemistry/__init__.py          # Placeholder
└── mathematics/__init__.py        # Placeholder
```

### ✅ Solution Agent
Created `vbagent/agents/content_generation/solution.py` with:
- `generate_solution()`: Main generation function
- `extract_diagram_requirements()`: Parse diagram placeholders
- `infer_diagram_type()`: Auto-detect diagram types
- `SolutionResult`: Data class for outputs
- `DiagramRequirement`: Data class for diagram needs

### ✅ Documentation
- `SOLUTION_ARCHITECTURE_REDESIGN.md`: Complete architecture
- `SOLUTION_STAGE_IMPLEMENTATION.md`: Implementation guide
- This summary document

## Key Features

### 1. Subject-Specific Organization
Just like your diagram prompts, solution prompts are organized by subject:
- `physics/` - Physics-specific reasoning and notation
- `chemistry/` - Chemistry-specific (TODO)
- `mathematics/` - Mathematics-specific (TODO)

### 2. Diagram Placeholder System
Solutions use placeholders that get replaced with actual diagrams:
```latex
\placeholder{diagram_id}{description}
```

Example:
```latex
\placeholder{fbd_1}{Free body diagram showing forces on block}
```

The system automatically:
- Extracts all placeholders
- Infers diagram type from ID/description
- Creates `DiagramRequirement` objects
- Routes to appropriate diagram agent

### 3. Cost Optimization
- Scanner: Use GPT-4o-mini (~10x cheaper)
- Solution: Use GPT-4o (better reasoning)
- Diagram: Use existing specialized agents

### 4. Quality Focus
Each stage has focused prompts:
- Scanner: OCR and structure extraction
- Solution: Physics/chemistry/math reasoning
- Diagram: Visual representation

## How It Works

### Example: Physics MCQ

```python
# Stage 1: Scan (GPT-4o-mini)
scan_result = scan(image_path, classification)
# → problem: "\item A block of mass 2 kg..."
# → options: ["A) 10 N", "B) 20 N", ...]

# Stage 2: Generate Solution (GPT-4o)
solution_result = generate_solution(
    problem=scan_result.latex,
    question_type="mcq_sc",
    subject="physics"
)
# → solution_latex: "\begin{solution}...\end{solution}"
# → diagram_requirements: [DiagramRequirement(id="fbd_1", type="fbd", ...)]

# Stage 3: Generate Diagrams (existing)
for req in solution_result.diagram_requirements:
    diagram = generate_diagram(req.diagram_type, req.description)
    # Replace placeholder with actual TikZ
    
# Stage 4: Assemble
final_latex = problem + solution_with_diagrams
```

## What's Next

### Immediate (Complete Physics)
1. Create remaining physics prompts:
   - `mcq_mc.py` (multiple correct)
   - `assertion_reason.py`
   - `passage.py`
   - `match.py`

### Short-term (Other Subjects)
2. Create chemistry solution prompts
3. Create mathematics solution prompts
4. Mirror the structure you have for diagrams

### Medium-term (Integration)
5. Create assembler agent
6. Update CLI commands
7. Add model configuration
8. Update scanner to output structured data

### Long-term (Optimization)
9. Test with GPT-4o-mini for scanning
10. Measure quality improvements
11. Optimize prompts based on results
12. Add caching for expensive operations

## Benefits You'll Get

### 💰 Cost Savings
- Scanner: ~10x cheaper with GPT-4o-mini
- Only use expensive model for reasoning
- Can regenerate solutions without rescanning

### 📈 Better Quality
- Focused prompts per stage
- Better solution reasoning
- More accurate diagram identification

### 🔧 Flexibility
- Swap models per stage
- Regenerate any stage independently
- Easy to experiment with different models

### 🧩 Maintainability
- Clear separation of concerns
- Subject-organized prompts (like diagrams)
- Easy to update and extend

## Current Status

### ✅ Ready to Use
- Physics MCQ (single correct) solution generation
- Physics subjective solution generation
- Diagram requirement extraction
- Diagram type inference

### 🚧 In Progress (TODO)
- Complete physics question types
- Chemistry prompts
- Mathematics prompts
- Assembler agent
- CLI integration

### 📋 Planned
- Model configuration
- Testing suite
- Performance benchmarks
- Documentation updates

## Testing It Out

You can start testing the solution generation now:

```python
from vbagent.agents.content_generation.solution import generate_solution

# Test with a physics MCQ
result = generate_solution(
    problem=r"\item A block of mass 2 kg is on a frictionless surface...",
    question_type="mcq_sc",
    options=["A) 10 N", "B) 20 N", "C) 30 N", "D) 40 N"],
    subject="physics"
)

print(result.solution_latex)
print(f"Diagrams needed: {len(result.diagram_requirements)}")
for req in result.diagram_requirements:
    print(f"  - {req.diagram_type}: {req.description}")
```

## Questions to Consider

1. **Model Selection**: Should we use GPT-4o-mini or codex-mini for scanning?
2. **Diagram Timing**: Should diagrams be generated during solution or after?
3. **Caching**: Should we cache solutions for similar problems?
4. **Validation**: How to validate solution quality automatically?

## Next Session Goals

1. Complete remaining physics prompts
2. Test solution generation with real problems
3. Integrate with existing scanner
4. Create assembler for final document

---

Your idea of separating scanning and solution is solid! This architecture gives you better quality, lower costs, and more flexibility. The structure mirrors your existing diagram organization, making it consistent and maintainable.
