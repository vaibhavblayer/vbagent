# Quick Start

Get started with VBAgent in 5 minutes!

## 1. Initialize Workspace

```bash
vbagent init
```

This creates `.vbagent.json` with your preferences (subject, models, etc.).

## 2. Process Your First Image

```bash
vbagent process -i question.png
```

This will:
- Classify the question type
- Extract LaTeX
- Generate TikZ diagrams (if present)
- Assess difficulty
- Save everything with metadata

**Output:**
```
agentic/
├── scans/problem_1.tex          (with metadata)
├── classifications/problem_1.json
├── diagrams/problem_1.json
├── difficulty/problem_1.json
└── tikz/problem_1.tex
```

## 3. Author a syllabus-scoped problem

Inspect the plan without making API calls:

```bash
vbagent author preflight \
  --exam jee_main \
  --subject physics \
  --chapter kinematics \
  --topic "Projectile Motion" \
  --type mcq_sc \
  --count 4
```

Then replace `preflight` with `run` and add `--output agentic/authoring`.
Only candidates that pass the independent solution, answer, syllabus,
difficulty, compile, review, and novelty gates are accepted.

## 4. Try the Chat Interface

```bash
vbagent chat
```

**Example conversation:**
```
You: "Generate a JEE Main Physics single-correct MCQ from Laws of Motion on friction"

Agent: *generates complete problem with TikZ and metadata*
```

## 5. Create a DPP Set

```bash
vbagent dpp create -n 10
```

Creates a balanced 10-question practice set from your question bank.

## Common Workflows

### Scan Multiple Images

```bash
vbagent batch init -i ./images -o ./output
vbagent batch continue
```

### Generate Variants

```bash
vbagent variant --parent-spec-id ACCEPTED_SPEC_ID --type numerical --count 3 \
  --output agentic/authoring
```

Variants require an accepted canonical parent and pass the same full acceptance
pipeline as original problems.

### Database Management

```bash
# Initialize database
vbagent db init ./questions

# Query questions
vbagent db query --topic Mechanics --difficulty medium
```

## Next Steps

- [CLI Commands Reference](../user-guide/cli-commands.md)
- [Chat Interface Guide](../user-guide/chat.md)
- [Problem Generation](../user-guide/problem-generation.md)
