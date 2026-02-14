# Problem Generation

**NEW in v0.2.2:** Generate complete physics problems from ideas using natural language!

## Overview

VBAgent can now generate complete problems from scratch using Agent 5 (Idea Generator) with full pipeline integration:

- Problem statement + solution + alternate solution
- TikZ diagrams from description
- Classification metadata
- Difficulty assessment
- Standard output format

## Using Chat Interface

The easiest way to generate problems:

```bash
$ vbagent chat
```

### Example 1: Minimal Input

```
You: "Create a problem on friction"

Agent: "What topic is this for? (e.g., Mechanics, Dynamics)"
You: "Mechanics"

Agent: "What type of question? (mcq_sc, passage, subjective)"
You: "passage"

Agent: "How many questions?"
You: "3"

Agent: "Should I include diagrams?"
You: "yes"

Agent: *generates complete problem*
```

### Example 2: Full Details Upfront

```
You: "Generate a passage problem on double block friction system in 
      Mechanics with 3 questions, medium difficulty, with diagrams"

Agent: *directly generates without asking*
```

## What You Get

Complete problem with:

- ✅ Generated LaTeX (problem + solution + ideas)
- ✅ TikZ diagram (auto-generated from description)
- ✅ Classification metadata (Agent 4)
- ✅ Diagram analysis (Agent 2)
- ✅ Difficulty assessment (Agent 3)
- ✅ All metadata merged into LaTeX

**Output structure:**
```
agentic/
├── generated/
│   ├── problem_1.tex          (with metadata comments)
│   ├── problem_1_solution.tex
│   └── problem_1_idea.tex
├── classifications/problem_1.json
├── diagrams/problem_1.json
├── difficulty/problem_1.json
└── tikz/problem_1.tex
```

Same format as image/tex processing!

## Parameters

When generating problems, you can specify:

- **idea** (required): What the problem is about
  - Example: "double block friction system"
  
- **topic** (required): Physics topic
  - Example: "Mechanics", "Thermodynamics", "Kinematics"
  
- **question_type** (optional): Type of question
  - Options: `mcq_sc`, `mcq_mc`, `passage`, `subjective`, `assertion_reason`, `match`
  - Default: `passage`
  
- **num_questions** (optional): Number of questions (for passage)
  - Range: 1-10
  - Default: 2
  
- **difficulty** (optional): Target difficulty
  - Options: `easy`, `medium`, `hard`
  - Default: `medium`
  
- **with_diagram** (optional): Include diagrams
  - Default: `true`
  
- **concepts** (optional): Specific concepts to cover
  - Example: ["friction", "normal force", "energy conservation"]

## Example Conversations

### Physics Problem

```
You: "I want to create a problem on projectile motion"

Agent: "What topic?"
You: "Kinematics"

Agent: "What type of question?"
You: "mcq_sc"

Agent: "Difficulty level?"
You: "hard"

Agent: "Include diagrams?"
You: "yes"

Agent: *generates MCQ with trajectory diagram*
```

### Chemistry Problem

```
You: "Generate a passage on chemical equilibrium in Physical Chemistry, 
      4 questions, medium difficulty"

Agent: *generates complete passage with reactions and diagrams*
```

### Mathematics Problem

```
You: "Create a calculus problem on integration by parts"

Agent: "What difficulty?"
You: "medium"

Agent: *generates problem with step-by-step solution*
```

## Tips

1. **Be specific about the concept:** "double block friction" is better than just "friction"

2. **Mention key concepts:** Helps generate focused problems
   ```
   "Create a problem on friction covering normal force and energy conservation"
   ```

3. **Specify diagram needs:** If you want specific diagram elements
   ```
   "Generate with free body diagram showing all forces"
   ```

4. **Use natural language:** The agent understands conversational input
   ```
   "I need a tough passage problem on thermodynamics with 3 questions"
   ```

## Workflow

1. **Generate** → Problem created by Agent 5
2. **TikZ** → Diagram generated from description
3. **Classify** → Agent 4 analyzes the problem
4. **Analyze** → Agent 2 analyzes diagram
5. **Assess** → Agent 3 assesses difficulty
6. **Merge** → All metadata added to LaTeX
7. **Save** → Standard format output

## Time Estimates

- Problem generation: ~30-40 seconds
- TikZ generation: ~5-10 minutes (complex diagrams)
- Classification: ~1-2 seconds
- Diagram analysis: ~10 seconds
- Difficulty assessment: ~15-20 seconds

**Total:** ~6-12 minutes for complete problem with diagram

## Next Steps

- [Chat Interface Guide](chat.md)
- [CLI Commands](cli-commands.md)
- [API Reference](../api/agents.md)
