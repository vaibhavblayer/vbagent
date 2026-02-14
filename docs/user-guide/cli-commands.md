# CLI Commands Reference

Complete reference for all VBAgent CLI commands.

## Core Commands

### init
Initialize workspace configuration.

```bash
vbagent init              # Interactive setup
vbagent init --quick      # Only ask for subject
vbagent init --yes        # Use defaults
vbagent init --force      # Overwrite existing
```

### classify
Classify question type from image.

```bash
vbagent classify -i question.png
vbagent classify -i question.png -o result.json
vbagent classify -i question.png --json
```

### scan
Extract LaTeX from question image.

```bash
vbagent scan -i question.png
vbagent scan -i question.png -o output.tex
vbagent scan -i question.png --type mcq_sc
vbagent scan -i question.png -c                    # Compile to validate
vbagent scan -i question.png --assess-difficulty   # Use Agent 3
vbagent scan -i question.png --analyze-diagram     # Use Agent 2
```

### tikz
Generate TikZ diagrams.

```bash
vbagent tikz -i diagram.png
vbagent tikz -d "A free body diagram with forces"
vbagent tikz -i diagram.png --ref ./references
vbagent tikz -i diagram.png -c                     # Compile to validate
```

### process
Full pipeline processing.

```bash
vbagent process -i question.png
vbagent process -i question.png --ideas --alternate
vbagent process -i question.png --variants numerical,context
vbagent process -t problems.tex -r 1 5
vbagent process -i question.png -c                 # Compile all outputs
vbagent process -i question.png --parallel 3       # Use 3 workers
```

## Variant Generation

### variant
Generate problem variants.

```bash
vbagent variant -t problem.tex --type numerical
vbagent variant -t problem.tex --type context -n 3
vbagent variant -t problem.tex --type conceptual
vbagent variant -t problem.tex --type multi --context ref1.tex ref2.tex
```

**Variant Types:**
- `numerical` - Change numbers only
- `context` - Change scenario
- `conceptual` - Change physics concept
- `calculus` - Add calculus elements
- `multi` - Combine multiple problems

### alternate
Generate alternate solutions.

```bash
vbagent alternate -t problem.tex
vbagent alternate -t problem.tex --ideas ideas.json
vbagent alternate -t problem.tex -n 2
```

### idea
Extract physics concepts.

```bash
vbagent idea -t problem.tex
vbagent idea -t problem.tex -o ideas.json
vbagent idea -t problem.tex --json
```

### convert
Convert between question formats.

```bash
vbagent convert -t problem.tex --to subjective
vbagent convert -t problem.tex --to mcq_sc
vbagent convert -i question.png --to integer
```

## Batch Processing

### batch
Process multiple images with resume capability.

```bash
# Initialize batch
vbagent batch init -i ./images -o ./output

# With options
vbagent batch init -i ./images -o ./output --variants numerical,context --alternate

# Continue processing
vbagent batch continue

# Reset failed items
vbagent batch continue --reset-failed

# Check status
vbagent batch status
```

## Quality Assurance

### check
QA review with interactive approval.

```bash
# Start review
vbagent check run
vbagent check run -c 10              # Review 10 problems
vbagent check run -p 42              # Review specific problem

# Initialize tracking
vbagent check init -d ./scans
vbagent check init -r 1 50           # Track problems 1-50

# Continue from last
vbagent check continue

# Check status
vbagent check status
vbagent check status --status pending

# Recheck problems
vbagent check recheck --failed
vbagent check recheck 1 2 3

# Specialized checkers
vbagent check solution
vbagent check grammar
vbagent check clarity
vbagent check alternate
vbagent check idea
vbagent check tikz

# History
vbagent check history -p 42
vbagent check apply <version_id>
vbagent check stats --days 7
```

## Conversational Interface

### chat
Interactive chat with LLM orchestration.

```bash
vbagent chat
```

Access all vbagent functions through natural language.

### mcp
Run as MCP server for external agents.

```bash
vbagent mcp
```

## Question Bank Management

### metadata
Manage question metadata.

```bash
# Index directory
vbagent metadata index ./questions

# Query questions
vbagent metadata query --topic Kinematics
vbagent metadata query --difficulty medium --type mcq_sc
vbagent metadata query --tags "motion,graphs" --limit 10

# View statistics
vbagent metadata stats
```

### db
SQLite database management.

```bash
# Initialize database
vbagent db init ./questions

# Insert problems
vbagent db insert ./new_questions

# Query
vbagent db query --topic Kinematics
vbagent db query --difficulty medium --format json

# Statistics
vbagent db stats

# Delete
vbagent db delete 42
```

### dpp
Create Daily Practice Problem sets.

```bash
# Create balanced DPP
vbagent dpp create -n 10

# With filters
vbagent dpp create -n 15 -t Mechanics -d medium

# With strategy
vbagent dpp create -n 10 -s topic_coverage
vbagent dpp create -n 10 -s balanced

# Compile to PDF
vbagent dpp create -n 8 --compile
```

**Selection Strategies:**
- `balanced` - 40% easy, 40% medium, 20% hard
- `topic_coverage` - Maximize topic diversity
- `random` - Random with usage fairness

### extans
Extract answers from LaTeX files.

```bash
# Extract from main.tex
vbagent extans

# Specify file
vbagent extans -f problems.tex

# Output formats
vbagent extans --format json -o answers.json
vbagent extans --format yaml -o answers.yaml
vbagent extans --format latex -o answers.tex
```

### export
Export LaTeX in different formats.

```bash
# Flat export
vbagent export run *.tex -o output/ -m flat

# Structured export
vbagent export directory questions/ -o output/ -m structured

# Project export
vbagent export run *.tex -o output/ -m project --title "My DPP"
```

## Reference Management

### ref
Manage reference context files.

```bash
# Add reference
vbagent ref add tikz diagram.tex -n "FBD Example"

# Remove reference
vbagent ref remove tikz "FBD Example"

# List references
vbagent ref list
vbagent ref list -c tikz

# Show reference
vbagent ref show tikz "FBD Example"

# Enable/disable context
vbagent ref enable
vbagent ref disable
vbagent ref status
vbagent ref set-max 10
```

#### TikZ References
```bash
# Import TikZ with metadata
vbagent ref tikz import diagrams.tex
vbagent ref tikz import diagrams.tex -r 1 5

# List TikZ references
vbagent ref tikz list
vbagent ref tikz list --diagram-type circuit
vbagent ref tikz list --topic mechanics

# Remove/show
vbagent ref tikz remove <ref_id>
vbagent ref tikz show <ref_id>
vbagent ref tikz status
```

## Configuration

### config
Manage configuration.

```bash
# Show current config
vbagent config show

# Set agent config
vbagent config set scanner --model gpt-4o
vbagent config set tikz --reasoning high
vbagent config set variant --temperature 0.7

# Reset to defaults
vbagent config reset

# List available models
vbagent config models
```

## Utilities

### util
File management utilities.

```bash
# Rename files
vbagent util rename images/
vbagent util rename . --prefix Q --ext .tex
vbagent util rename . --uppercase --pad 3
vbagent util rename . --shuffle
vbagent util rename . --dry-run

# Count files
vbagent util count images/
vbagent util count . --recursive

# Clean generated files
vbagent util clean              # Remove agentic/
vbagent util clean --config     # Remove .vbagent.json
vbagent util clean --all        # Remove everything

# List files
vbagent util list images/ --ext .png .jpg
```

## Global Options

Available for most commands:

- `-h, --help` - Show help message
- `-v, --verbose` - Verbose output
- `--debug` - Debug mode
- `--no-color` - Disable colored output

## Examples

### Complete Workflow
```bash
# 1. Initialize
vbagent init

# 2. Process image
vbagent process -i question.png --ideas --alternate --variants numerical

# 3. Review output
vbagent check run -d agentic/scans

# 4. Batch process
vbagent batch init -i ./images -o ./output
vbagent batch continue
```

### Quality Pipeline
```bash
# Scan with validation
vbagent scan -i question.png -c --assess-difficulty

# Generate variants with compilation
vbagent variant -t problem.tex --type numerical -c

# Review everything
vbagent check solution
vbagent check grammar
vbagent check tikz
```
