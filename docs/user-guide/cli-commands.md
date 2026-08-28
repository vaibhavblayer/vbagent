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
vbagent process -t problems.tex --from 1 --to 50 --parallel 3
```

`--parallel` applies to image batches and individual TeX items. Results are
returned in input order, and the command exits non-zero if any selected item
fails; successful items are still saved.

### solve
Generate solutions from an already-scanned TeX project without running the
scanner or classifier.

```bash
vbagent solve -t scanned.tex --subject physics --type mcq_sc -o solved.tex
vbagent solve -t scanned.tex --from 1 --to 50 --exclude 5,7,8
vbagent solve -t biology.tex --subject biology --type mcq_sc --no-diagram
vbagent solve -t scanned.tex --from 1 --to 50 --exclude "5, 7, 8" --no-cache
vbagent solve -t scanned-problems/ -o solved-problems/ --from 1 --to 50 --exclude 5,7,8
vbagent solve -t scanned-problems/ --in-place --no-diagram --from 1 --to 5 --exclude 4,3
```

`--exclude` is repeatable and uses 1-based item numbers. The output preserves
items outside the selected range and excluded items. `--no-diagram` skips
solution diagram agents; inline LaTeX emitted directly by the solution agent
is preserved. With folder input, each top-level `.tex` file is treated as one
problem and copied to the output directory; selected files are replaced with
their solved versions. `--in-place` instead updates selected input files
directly and cannot be combined with `--output`. Files/items that already
contain a complete `solution` environment are skipped automatically.

## Syllabus authoring

### author

Plan a batch without API calls, then execute it durably:

```bash
vbagent author catalogs
vbagent author preflight --exam jee_main --subject physics --chapter kinematics --count 20
vbagent author run --exam jee_main --subject physics --chapter kinematics \
  --topic "Projectile Motion" --type mcq_sc:3 --type integer:1 \
  --difficulty medium:3 --difficulty hard:1 --count 20 \
  --concurrency 4 --output agentic/authoring
```

Resume and inspect by the printed immutable run ID:

```bash
vbagent author status --run-id RUN_ID --output agentic/authoring
vbagent author continue --run-id RUN_ID --output agentic/authoring
vbagent author cancel --run-id RUN_ID --output agentic/authoring
```

See [Syllabus-driven problem authoring](problem-generation.md) for distributions,
custom catalogs, human review, the Python API, and acceptance gates.

## Variant generation

### variant
Create controlled variants from an accepted canonical parent.

```bash
vbagent variant --parent-spec-id SPEC_ID --type numerical --count 3 \
  --output agentic/authoring
vbagent variant --parent-spec-id SPEC_ID --type context --type conceptual \
  --count 8 --output agentic/authoring
```

**Variant Types:**
- `numerical` - Change numbers only
- `context` - Change scenario
- `conceptual` - Change physics concept
- `calculus` - Add calculus elements

Raw TeX and images are not unchecked creation parents. The parent must be
accepted in the same durable ledger; lineage, syllabus identity, fan-out, and
artifact hashes are enforced before child generation.

### alternate
Generate alternate solutions.

When used through the full solution pipeline with `--alternate`, generation is
conditional: the solution agent first recommends whether a distinct method is
worth producing and supplies the method hint. The direct `vbagent alternate`
command remains an explicit manual generation command.

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

## Natural-language MCP interface

### chat

Run the built-in transparent conversational host. It discovers the same FastMCP
tools, renders messages and tool I/O as formatted JSON, mirrors detached agent
I/O, and locally authorizes direct creation intent while keeping plan-only or
ambiguous requests behind `confirm`. A compact toolbar continuously tracks the
latest background generation and its current durable agent stage. On completion
it reports project-root `main.tex`, `answer_key.tex`, and `main.pdf`, with stable
problem paths such as `agentic/generated/problem_1.tex` and a JSON sidecar.
`/results [RUN_ID]` displays full authored LaTeX with validation status. Chat
supports independently selected solution/idea components, deferred component
completion on the same files, and an end-of-run keep/revise/reject decision for
review-pending drafts. See the [authoring guide](problem-generation.md).

```bash
vbagent chat --output agentic/authoring
vbagent chat --message "Plan 20 JEE Main kinematics problems"
vbagent chat --model gpt-5.6-terra
```

### mcp
Run the typed, durable authoring server for an MCP-capable conversational host.

```bash
vbagent mcp --output agentic/authoring
```

The host model handles conversation. The server exposes catalog inspection,
no-model-call planning, intent-or-confirmation-authorized detached execution, status,
pagination, cancellation/resume, review, variants, and accepted/evidence
resources. Use `--transport streamable-http` or `--transport sse` only for a
trusted local client; stdio is the default.

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

### compile

Generate `main.tex` from processed problem files, with subject packages and a
custom title. This command writes the LaTeX document; run `pdflatex main.tex` or
`latexmk -pdf main.tex` to produce the PDF.

```bash
vbagent compile --all-packages -t "DPP: JEE: III: Functions" \
  --solution --alternatesolution

# Hide both solution sections
vbagent compile --all-packages --no-solution --no-alternatesolution

# Ordinary solutions, without alternate solutions
vbagent compile --solution --no-alternatesolution
```

Both solution sections remain visible by default for compatibility. Each flag
independently comments or uncomments its `\excludecomment{...}` line in the
generated preamble. The source problem files are not modified. Hints, ideas,
remarks, and the `finalanswer` answer-key blocks remain hidden.

### extans
Extract MCQ, integer, and subjective answers from LaTeX problem files.
Subjective solutions generated by VBAgent carry a hidden
`finalanswer` environment that is used for the answer key.

```bash
# Extract from main.tex
vbagent extans

# Specify the main file positionally or with the legacy option
vbagent extans path/to/main.tex
vbagent extans -f problems.tex

# Output formats
vbagent extans --format json -o answers.json
vbagent extans --format yaml -o answers.yaml
vbagent extans --format latex -o answer_key.tex

# Generate answer_key.tex and add it to main.tex without prompting
vbagent extans path/to/main.tex --add
```

LaTeX output uses seven columns for compact MCQ/integer keys and two columns
when subjective answers are present. After writing LaTeX output, `extans` asks
whether to insert the following immediately after the final `enumerate` block:

```latex
\vspace*{\fill}
\input{answer_key.tex}
```

The `--add` option performs this insertion directly and is idempotent. When no
output is specified, `--add` writes `answer_key.tex` beside the main file.

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

# Generate accepted-parent variants (compilation is mandatory)
vbagent variant --parent-spec-id SPEC_ID --type numerical --count 3 \
  --output agentic/authoring

# Review everything
vbagent check solution
vbagent check grammar
vbagent check tikz
```
