# VBAgent

A multi-agent library and CLI for processing physics, chemistry, mathematics, and biology question images. Supports classification, LaTeX extraction, TikZ diagram generation, variant creation, format conversion, LaTeX compilation with auto-fix, and QA review.

📚 **[Documentation](https://vaibhavblayer.github.io/vbagent/)** | 🐛 **[Issues](https://github.com/vaibhavblayer/vbagent/issues)** | 💬 **[Discussions](https://github.com/vaibhavblayer/vbagent/discussions)**

## Installation

### From PyPI

```bash
# Full installation (library + CLI)
pip install vbagent[all]

# Library only (no CLI dependencies)
pip install vbagent

# CLI only
pip install vbagent[cli]
```

### From Source

```bash
git clone https://github.com/vaibhavblayer/vbagent.git
cd vbagent

# Install with pip
pip install -e ".[dev]"

# Or using Poetry
poetry install
```

## Requirements

- Python 3.12+
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- For compilation: `pdflatex` (TeX Live or MacTeX)

### Supported Providers

| Provider | Env Variable | Models |
|----------|-------------|--------|
| OpenAI | `OPENAI_API_KEY` | gpt-5.2, gpt-5.1, gpt-5-mini, gpt-5.1-codex |
| xAI | `XAI_API_KEY` | grok-4, grok-4-fast-reasoning, grok-3, grok-3-mini |
| Google | `GOOGLE_API_KEY` | gemini-2.5-pro, gemini-2.5-flash, gemini-3-flash-preview |

## Library Usage

### Quick Start

```python
from vbagent import classify, scan, generate_variant, generate_tikz

# Classify an image
classification = classify("question.png")
print(f"Type: {classification.question_type}, Topic: {classification.topic}")

# Scan with classification
scan_result = scan("question.png", classification)
print(scan_result.latex)

# Generate a variant
variant = generate_variant(scan_result.latex, "numerical")

# Generate TikZ diagram
tikz = generate_tikz("A free body diagram showing forces on a block")
```

### Solution Orchestrator (NEW)

For complex solutions with diagrams, calculus, and multiple steps, use the solution orchestrator to automatically coordinate specialist agents:

```python
from vbagent import create_solution_orchestrator

# Create orchestrator
orchestrator = create_solution_orchestrator()

# Generate solution with automatic agent coordination
result = orchestrator.generate_solution(
    image_path="solution.png",
    problem_context="Mechanics problem on friction",
    question_type="subjective",
    verbose=True,
)

print(result.latex)  # Complete unified solution
print(f"Agents used: {[o.agent for o in result.agent_outputs]}")
```

**How it works:**
1. **Planning Phase**: Analyzes solution and identifies needed components (FBD, calculus, graphs, etc.)
2. **Execution Phase**: Calls specialist agents (FBD, circuit, tikz, calculus) as needed
3. **Assembly Phase**: Combines outputs into unified, well-formatted solution

**Benefits:**
- Automatically routes to specialized agents (FBD, circuit, graph, etc.)
- Better quality for complex solutions with multiple components
- Reuses existing specialized agents
- Handles diagrams, calculus, tables, and multi-step solutions

### Multi-Agent Classification System (v2.0)

VBAgent includes a comprehensive 7-agent classification pipeline for advanced metadata extraction:

Subject inference now runs automatically before classification, so the pipeline picks the appropriate subject (physics, chemistry, mathematics, biology) from the image/LaTeX input instead of depending on manual config overrides. The prompts also include richer question-type cues so mcq_sc, mcq_mc, subjective, assertion_reason, passage, and match formats are detected with better evidence.

```python
from vbagent.agents.classification import (
    get_pipeline,
    classify_from_image,
    analyze_diagram,
    assess_difficulty,
    validate_tikz,
)

# Agent 1: Image Classification
primary = classify_from_image("question.png")
print(f"Topic: {primary.topic}, Concepts: {primary.key_concepts}")

# Agent 2: Diagram Analysis (if has_diagram)
if primary.has_diagram:
    diagram = analyze_diagram("question.png", primary)
    print(f"Diagram: {diagram.diagram_type}, Agent: {diagram.suggested_tikz_agent}")

# Agent 3: Difficulty Assessment (after scanning)
difficulty = assess_difficulty(latex_content, primary, diagram)
print(f"Difficulty: {difficulty.difficulty} ({difficulty.difficulty_score}/10)")
print(f"Reasoning: {difficulty.difficulty_reasoning}")
print(f"Prerequisites: {difficulty.prerequisite_concepts}")
print(f"Common Mistakes: {difficulty.common_mistakes}")

# Agent 7: TikZ Validation
validation = validate_tikz(tikz_code, auto_fix=True, compile_test=True)
if validation.is_valid:
    print("TikZ code is valid!")
```

**7 Specialized Agents:**
1. **Image Classifier** - Classifies from images without difficulty
2. **Diagram Analyzer** - Hierarchical diagram categorization, TikZ routing
3. **Difficulty Assessor** - Post-scan difficulty with 5 metadata types
4. **LaTeX Classifier** - Batch processing of LaTeX files
5. **Idea Generator** - Generate problems from concepts
6. **Problem Combiner** - Combine multiple problems (cross-subject support)
7. **TikZ Checker** - Automatic validation and fixing

**Key Features:**
- Multiple input modalities (image, latex, idea, multi_problem)
- Detailed difficulty assessment (reasoning, time, prerequisites, mistakes, exam relevance)
- Hierarchical diagram classification (mechanics, circuits, optics, etc.)
- Automatic TikZ validation with error fixing
- Specialized TikZ agent routing (fbd, circuit, graph, optics)
- Bloom's taxonomy cognitive levels
- Cross-subject problem combination

See `examples/multi_agent_pipeline.py` for complete usage examples.

### Configuration

```python
from vbagent import get_config, set_config

config = get_config()
config.scanner.model = "gpt-5.2"
config.scanner.reasoning_effort = "high"
set_config(config)
```

Configuration hierarchy (later overrides earlier):
1. Global config: `~/.config/vbagent/models.json`
2. Workspace config: `.vbagent.json` in current directory

### Available Functions

```python
# Classification
from vbagent import classify
result = classify("image.png")  # Returns ClassificationResult

# Scanning
from vbagent import scan, scan_with_type
result = scan("image.png", classification)
result = scan_with_type("image.png", "mcq_sc")  # Skip classification

# Variants
from vbagent import generate_variant, generate_numerical_variant
variant = generate_variant(latex, "numerical")

# TikZ
from vbagent import generate_tikz, validate_tikz_output
tikz = generate_tikz("description", image_path="ref.png")

# Ideas
from vbagent import extract_ideas
ideas = extract_ideas(problem_latex, solution_latex)  # Returns IdeaResult

# Alternates
from vbagent import generate_alternate
alternate = generate_alternate(problem, solution)

# QA Checkers
from vbagent import check_solution, check_grammar, check_clarity, check_tikz
passed, summary, corrected = check_solution(content)

# Review
from vbagent import review_problem_sync, ProblemContext
context = ProblemContext(...)
result = review_problem_sync(context)  # Returns ReviewResult

# Compilation
from vbagent.compile import compile_latex, compile_and_retry, CompileResult
result = compile_latex(latex_snippet, subject="physics")
result = compile_latex(latex_snippet, verbose=True)  # Stream pdflatex output live
```

### Models

```python
from vbagent.models import (
    ClassificationResult, ScanResult, IdeaResult,
    PipelineResult, ReviewResult, Suggestion, ReviewIssueType,
)

# Classification fields
classification.question_type  # mcq_sc, mcq_mc, subjective, assertion_reason, passage, match
classification.difficulty     # easy, medium, hard
classification.topic          # kinematics, thermodynamics, etc.
classification.has_diagram    # bool
classification.diagram_type   # graph, circuit, free_body, etc.
```

### References

```python
from vbagent.references import ReferenceStore, TikZStore, get_context_prompt_section

store = ReferenceStore.get_instance()
results = store.search("query")

tikz_store = TikZStore.get_instance()
context = tikz_store.get_context_for_classification(classification)
```

### Low-Level Agent Access

```python
from vbagent.agents import create_agent, run_agent_sync, create_image_message

agent = create_agent(
    name="MyAgent",
    instructions="Your system prompt",
    agent_type="scanner",
)
result = run_agent_sync(agent, "Your input")

# With image
message = create_image_message("image.png", "Analyze this")
result = run_agent_sync(agent, message)
```

## CLI Usage

### Quick Start

```bash
# Initialize workspace config
vbagent init

# Scan a physics question image to LaTeX
vbagent scan -i question.png -o output.tex

# Classify a question type
vbagent classify -i question.png

# Generate TikZ diagram from image
vbagent tikz -i diagram.png -o diagram.tex

# Full pipeline
vbagent process -i question.png --ideas --alternate --variants numerical,context

# Compile-validate generated LaTeX
vbagent process -i question.png -c

# Verbose compile (see full LaTeX + pdflatex output, interactive prompt)
vbagent process -i question.png -c --verbose-compile
```

### Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize workspace config interactively |
| `chat` | Interactive conversational interface with LLM orchestration |
| `mcp` | Start MCP server for external agents (Kiro, Cursor, etc.) |
| `metadata` | Manage question bank metadata (index, query, stats) |
| `dpp` | Create Daily Practice Problem sets with smart selection |
| `export` | Export LaTeX files in different formats (flat, structured, project) |
| `extans` | Extract answers from LaTeX problem files |
| `db` | Database management for question bank with full content storage |
| `classify` | Classify physics question image type |
| `scan` | Extract LaTeX from question image |
| `tikz` | Generate TikZ/PGF code for diagrams |
| `idea` | Extract physics concepts and ideas |
| `alternate` | Generate alternative solutions |
| `variant` | Generate problem variants |
| `convert` | Convert between question formats |
| `process` | Run full processing pipeline |
| `batch` | Batch process multiple images with resume |
| `check` | QA review with interactive approval |
| `ref` | Manage reference context files |
| `config` | Configure models and settings |
| `util` | File utilities (rename, count, clean) |

---

## Conversational Orchestrator

VBAgent includes a conversational interface that allows natural language interaction with all vbagent functions through LLM orchestration.

### Chat Interface

Start an interactive chat session:

```bash
vbagent chat
```

The chat interface provides:
- Natural language commands (e.g., "create a 10 question DPP from mechanics")
- Access to all vbagent tools through conversation
- Multi-turn context and conversation history
- Rich terminal formatting with progress indicators

### Question Bank Metadata

Index and query your question bank with searchable metadata:

```bash
# Index a directory of LaTeX questions
vbagent metadata index ./questions

# Query questions by filters
vbagent metadata query --topic Kinematics --difficulty medium
vbagent metadata query --tags "motion,graphs" --limit 10

# View statistics
vbagent metadata stats
```

Metadata can be specified in LaTeX file comments:
```latex
% chapter: Mechanics
% topic: Kinematics
% difficulty: medium
% type: mcq_sc
% tags: motion, velocity, acceleration

\item A car moves with constant acceleration...
```

### Daily Practice Problem (DPP) Sets

Create curated problem sets with smart selection strategies:

```bash
# Create a balanced DPP
vbagent dpp create -n 10

# Create with topic filter and topic coverage strategy
vbagent dpp create -n 15 -s topic_coverage -t Mechanics

# Create and compile to PDF
vbagent dpp create -n 8 -d medium --compile
```

Selection strategies:
- `balanced`: 40% easy, 40% medium, 20% hard distribution
- `topic_coverage`: Maximize topic diversity
- `random`: Random selection with usage fairness

### Answer Extraction (extans)

Extract answers from LaTeX problem files:

```bash
# Extract from main.tex
vbagent extans

# Specify file and format
vbagent extans -f main.tex --format json
vbagent extans -o answers.yaml --format yaml
vbagent extans --format latex -o answers.tex
```

Features:
- Parses `\foreach` loops and `\input{}` statements
- Handles nested folders (physics/, chemistry/, etc.)
- Recursive parsing of intermediate files
- Supports MCQ (`\ans` marker) and integer (`\ansint{}`) answers
- Multiple correct answers (A,C format)
- Output formats: text, json, yaml, latex

### Database Management (db)

Complete SQLite-based question bank with full content storage:

```bash
# Initialize database
vbagent db init ./questions

# Check existing database
vbagent db init

# Insert new problems
vbagent db insert ./new_questions

# Query questions
vbagent db query --topic Kinematics --difficulty medium
vbagent db query --type passage --format json

# Show statistics
vbagent db stats

# Delete question
vbagent db delete 42
```

Features:
- Stores full LaTeX content (problem, solution, alternate, idea, TikZ)
- Context-aware TikZ storage (tracks which section each diagram belongs to)
- Parent-child relationship for passage/comprehension questions
- JSON storage for lists (tags, key_concepts)
- Metadata extraction from inline comments
- Accurate question counting (effective vs total entries)
- Children never exported/queried separately

### Export System

Export LaTeX files in different formats:

```bash
# Flat export (all files in one directory)
vbagent export run *.tex -o output/ -m flat

# Structured export (organized subdirectories)
vbagent export directory questions/ -o output/ -m structured

# Project export (main.tex with \input{} references)
vbagent export run *.tex -o output/ -m project --title "My DPP"
```

### MCP Server Mode

Run vbagent as an MCP (Model Context Protocol) server for integration with external agents:

```bash
vbagent mcp
```

Configure in your MCP client (e.g., Kiro's `mcp.json`):
```json
{
  "mcpServers": {
    "vbagent": {
      "command": "vbagent",
      "args": ["mcp"],
      "env": {}
    }
  }
}
```

This exposes all vbagent tools to external agents like Kiro, Cursor, and Claude Desktop.

---

## Command Reference

### init

Initialize workspace config interactively. Creates `.vbagent.json` in the current directory.

```bash
vbagent init              # Interactive setup
vbagent init --quick      # Only ask for subject
vbagent init --yes        # Use all defaults (non-interactive)
vbagent init --force      # Overwrite existing config
```

Subjects: `physics`, `chemistry`, `mathematics`, `biology`

### classify

```bash
vbagent classify -i <image> [-o <output.json>] [--json]
```

### scan

```bash
vbagent scan -i <image> [--type <type>] [-o <output.tex>] [-c] [--verbose-compile] [--assess-difficulty] [--analyze-diagram] [--orchestrate]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to physics question image |
| `-t, --tex` | Path to existing TeX file (for re-processing) |
| `--type` | Override question type: `mcq_sc`, `mcq_mc`, `subjective`, `assertion_reason`, `passage`, `match` |
| `-o, --output` | Output TeX file path |
| `-c, --compile` | Compile LaTeX to validate; retry with agent on failure |
| `--verbose-compile` | Show full LaTeX document + live pdflatex output before each compile, prompt to continue/skip/quit |
| `--assess-difficulty` | **NEW:** Assess difficulty after scanning (uses Agent 3) |
| `--analyze-diagram` | **NEW:** Analyze diagram in detail (uses Agent 2) |
| `--orchestrate` | **NEW:** Use solution orchestrator for complex solutions with automatic specialist agent coordination |

### tikz

```bash
vbagent tikz [-i <image>] [-d <description>] [--ref <dir>...] [-o <output.tex>] [-c] [--verbose-compile]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to diagram image |
| `-d, --description` | Text description of diagram to generate |
| `--ref` | Reference directories (can be used multiple times) |
| `-o, --output` | Output TeX file path |
| `-c, --compile` | Compile TikZ to validate; retry with agent on failure |
| `--verbose-compile` | Show full document + live pdflatex output, interactive prompt |

### idea

```bash
vbagent idea -t <tex> [-o <output.json>] [--json]
```

### alternate

```bash
vbagent alternate -t <tex> [--ideas <ideas.json>] [-n <count>] [-o <output.tex>]
```

### variant

```bash
vbagent variant [-i <image>] [-t <tex>] --type <type> [-r <start> <end>] [-n <count>] [-o <output.tex>] [-c] [--verbose-compile]
```

| Option | Description |
|--------|-------------|
| `--type` | `numerical`, `context`, `conceptual`, `calculus`, `cross_topic`, `multi` (required) |
| `-r, --range` | Range of items to process (1-based inclusive) |
| `-n, --count` | Number of variants per problem (default: 1) |
| `--context` | Additional context files for multi variant |
| `--ideas` | Path to ideas JSON file |
| `-c, --compile` | Compile variants to validate; retry with agent on failure |
| `--verbose-compile` | Show full document + live pdflatex output, interactive prompt |

#### Variant Types

| Type | Description |
|------|-------------|
| `numerical` | Change only numbers, keep context |
| `context` | Change scenario, keep numbers |
| `conceptual` | Change physics concept |
| `calculus` | Add calculus elements |
| `cross_topic` | Integrate a complementary physics topic (multi-stage) |
| `multi` | Combine multiple problems |

### convert

```bash
vbagent convert [-i <image>] [-t <tex>] [--from <format>] --to <format> [-o <output.tex>]
```

Target formats: `mcq_sc`, `mcq_mc`, `subjective`, `integer`

### process

Full pipeline: Classify → Scan → TikZ → Ideas → Variants.

```bash
vbagent process [-i <image>] [-t <tex>] [-r <start> <end>] [--variants <types>] [--alternate] [--ideas] [-o <output>] [-p <workers>] [-c] [--verbose-compile] [--assess-difficulty] [--analyze-diagram] [--validate-tikz] [--orchestrate]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Image file to process |
| `-t, --tex` | TeX file containing problems |
| `-r, --range` | Range to process (1-based inclusive) |
| `--variants` | Variant types (comma-separated: numerical,context,conceptual,calculus,cross_topic) |
| `--alternate` | Generate alternate solutions |
| `--ideas` | Extract physics concepts |
| `--ref` | Reference directories for TikZ |
| `-o, --output` | Output directory (default: `agentic`) |
| `--context/--no-context` | Use reference context (default: yes) |
| `-p, --parallel` | Parallel workers (default: 1, max: 10) |
| `-c, --compile` | Compile generated LaTeX to validate; retry with agent on failure |
| `--verbose-compile` | Show full LaTeX document + preamble + live pdflatex output before each compile, prompt to continue/skip/quit |
| `--assess-difficulty` | **NEW:** Assess difficulty after scanning (uses Agent 3) |
| `--analyze-diagram` | **NEW:** Analyze diagram in detail (uses Agent 2) |
| `--validate-tikz` | **NEW:** Validate and fix TikZ code (uses Agent 7) |
| `--orchestrate` | **NEW:** Use solution orchestrator for complex solutions with automatic specialist agent coordination |

#### Examples

```bash
# Basic processing
vbagent process -i question.png

# With solution orchestrator for complex solutions
vbagent process -i question.png --orchestrate

# Full pipeline with new agents
vbagent process -i question.png --ideas --alternate --variants numerical,context \
  --assess-difficulty --analyze-diagram --validate-tikz

# Cross-topic variant (integrates complementary physics topics)
vbagent process -i question.png --variants cross_topic

# Orchestrator with compilation
vbagent process -i question.png --orchestrate -c

# Process range with parallel workers
vbagent process -i images/Problem_1.png -r 1 10 --parallel 3

# With compile validation
vbagent process -i question.png -c

# With verbose compile (see exactly what pdflatex receives)
vbagent process -i question.png -c --verbose-compile

# Process TeX file
vbagent process -t problems.tex --range 1 5 --alternate --ideas
```

#### Output Structure

```
agentic/
├── scans/problem_1.tex
├── classifications/problem_1.json
├── tikz/problem_1.tex
├── ideas/problem_1.json          (if --ideas)
├── alternates/problem_1.tex      (if --alternate)
├── variants/
│   ├── numerical/problem_1.tex
│   ├── context/problem_1.tex
│   ├── conceptual/problem_1.tex
│   └── cross_topic/problem_1.tex
└── CONTEXT.md
```

### batch

Batch processing with resume capability.

```bash
vbagent batch init -i ./images -o ./output [--variants <types>] [--alternate] [--context]
vbagent batch continue [--reset-failed]
vbagent batch status
```

### check

QA review with interactive approval workflow.

```bash
# Start review session
vbagent check run [-c <count>] [-p <problem_id>] [-d <dir>]

# Initialize problem tracking
vbagent check init [-d <dir>] [-r <start> <end>] [--reset]

# Continue from where you left off
vbagent check continue [-c <count>] [-d <dir>]

# Check status
vbagent check status [-d <dir>] [--status <pending|done|failed>]

# Reset problems for rechecking
vbagent check recheck [-d <dir>] [--failed] [<problem_ids>...]

# Specialized checkers
vbagent check solution [-d <dir>] [-c <count>]
vbagent check grammar [-d <dir>] [-c <count>]
vbagent check clarity [-d <dir>] [-c <count>]
vbagent check alternate [-d <dir>] [-c <count>]
vbagent check idea [-d <dir>] [-c <count>]

# TikZ check/generation
vbagent check tikz [-d <dir>] [-c <count>] [--patch] [--ref-type <type>] [--reset]

# History and apply
vbagent check history [-p <problem_id>] [-n <limit>]
vbagent check apply <version_id> [-e]
vbagent check resume [<session_id>]
vbagent check stats [--days <n>]
```

#### check tikz

Two modes:
1. Reviews existing TikZ code for errors and best practices
2. Generates TikZ from `\input{diagram}` placeholder using the corresponding image

```bash
vbagent check tikz                        # Check/generate in default directory
vbagent check tikz -d ./scans/            # Specific directory
vbagent check tikz -c 10 --patch          # Use apply_patch mode
vbagent check tikz --ref-type circuit     # Filter by diagram type
vbagent check tikz --reset                # Re-check all files
```

Images are auto-discovered from `images/` sibling directory. Diagram type is auto-detected from classification metadata.

### ref

Manage reference context files.

```bash
# Add/remove references
vbagent ref add <category> <file> [-n <name>] [-d <description>]
vbagent ref remove <category> <name>
vbagent ref list [-c <category>]
vbagent ref show <category> <name>

# Enable/disable context
vbagent ref enable
vbagent ref disable
vbagent ref status
vbagent ref set-max <count>
```

Categories: `tikz`, `latex`, `variants`, `problems`

#### ref tikz (TikZ references with metadata)

```bash
vbagent ref tikz import <path> [-r <start> <end>]
vbagent ref tikz list [--diagram-type <type>] [--topic <topic>]
vbagent ref tikz remove <ref_id>
vbagent ref tikz show <ref_id>
vbagent ref tikz status
```

### config

```bash
vbagent config show
vbagent config set <agent_type> [--model <model>] [--reasoning <level>] [--temperature <temp>]
vbagent config reset
vbagent config models
```

Agent types: `classifier`, `scanner`, `tikz`, `tikz_checker`, `idea`, `alternate`, `variant`, `converter`, `reviewer`

Reasoning levels: `low`, `medium`, `high`, `xhigh`

### util

File management utilities.

```bash
# Rename files to serialized format
vbagent util rename images/                     # → problem_1.png, problem_2.png, ...
vbagent util rename . --prefix Q --ext .tex     # → q_1.tex, q_2.tex, ...
vbagent util rename . --uppercase --pad 3       # → Problem_001.png, ...
vbagent util rename . --shuffle                 # Randomize order
vbagent util rename . --dry-run                 # Preview only

# Count files
vbagent util count images/
vbagent util count . --recursive

# Clean generated files
vbagent util clean                # Remove agentic/ output
vbagent util clean --config      # Remove .vbagent.json
vbagent util clean --all         # Remove everything

# List files
vbagent util list images/ --ext .png .jpg
```

---

## LaTeX Compilation

The `-c` / `--compile` flag validates generated LaTeX by compiling with `pdflatex`. If compilation fails, the compile-fixer agent automatically attempts to fix errors and retries (up to 2 retries).

The `--verbose-compile` flag (used with `-c`) enables a debug mode that:
1. Prints the full preamble/packages going into the document
2. Prints your LaTeX snippet
3. Prints the complete document that `pdflatex` will receive
4. Streams `pdflatex` output live to the terminal (like running it manually)
5. Prompts you to **(c)** continue compiling, **(s)** skip compilation, or **(q)** quit

### Compile Preamble Packages

The compilation preamble includes:
- `amsmath`, `amssymb`, `amsthm`, `mathtools`
- `tikz` with libraries: calc, decorations, patterns, arrows.meta, positioning, shapes, intersections, angles, quotes
- `circuitikz` (american style)
- `pgfplots` (compat=1.18)
- `tasks` (MCQ options)
- `enumitem`
- `kinematikz`, `tzplot` (loaded if available)
- `mhchem`, `chemfig` (chemistry subject only)

## Supported Question Types

- MCQ Single Correct (`mcq_sc`)
- MCQ Multiple Correct (`mcq_mc`)
- Assertion-Reason (`assertion_reason`)
- Match the Following (`match`)
- Passage/Comprehension (`passage`)
- Subjective/Numerical (`subjective`)

## Project Structure

```
vbagent/
├── __init__.py                 # Public API with lazy imports
├── config.py                   # Configuration (models, providers, subjects)
├── compile.py                  # LaTeX compilation, validation, verbose debug
│
├── cli/                        # CLI commands (Click-based, lazy-loaded)
│   ├── main.py                 # Entry point with LazyGroup
│   ├── common.py               # Shared utilities (panels, prompts, formatting)
│   ├── init.py                 # Workspace initialization
│   ├── classify.py             # Classification command
│   ├── scan.py                 # LaTeX extraction command (with Agent 2 & 3)
│   ├── tikz.py                 # TikZ generation command
│   ├── variant.py              # Variant generation command
│   ├── alternate.py            # Alternate solutions command
│   ├── idea.py                 # Concept extraction command
│   ├── convert.py              # Format conversion command
│   ├── process.py              # Full pipeline command (with all agents)
│   ├── batch.py                # Batch processing command
│   ├── check.py                # QA review command
│   ├── ref.py                  # Reference management command
│   ├── config.py               # Config management command
│   ├── db.py                   # Database management command
│   ├── extans.py               # Answer extraction command
│   └── util.py                 # File utilities (rename, count, clean, list)
│
├── agents/                     # AI agent implementations
│   ├── base.py                 # Base agent (create, run, encode image)
│   ├── classifier.py           # Question type classifier (v1)
│   ├── classification/         # Multi-agent classification system (v2)
│   │   ├── __init__.py         # Pipeline exports
│   │   ├── pipeline.py         # Orchestrator with lazy loading
│   │   ├── image_classifier.py # Agent 1: Image classification
│   │   ├── diagram_analyzer.py # Agent 2: Diagram analysis
│   │   ├── difficulty_assessor.py # Agent 3: Difficulty assessment
│   │   ├── latex_classifier.py # Agent 4: LaTeX classification
│   │   ├── idea_generator.py   # Agent 5: Idea-to-problem generator
│   │   ├── problem_combiner.py # Agent 6: Multi-problem combiner
│   │   └── tikz_checker.py     # Agent 7: TikZ validation
│   ├── tikz_router.py          # TikZ agent routing system
│   ├── scanner.py              # LaTeX extraction
│   ├── tikz.py                 # TikZ diagram generator (generic)
│   ├── fbd.py                  # Free body diagram generator (specialized)
│   ├── variant.py              # Single variant generator
│   ├── multi_variant.py        # Multi-context variant generator
│   ├── alternate.py            # Alternate solution generator
│   ├── idea.py                 # Concept extractor
│   ├── converter.py            # Format converter
│   ├── compile_fixer.py        # LaTeX compile error fixer
│   ├── reviewer.py             # QA reviewer
│   ├── selector.py             # Problem selector
│   ├── solution_checker.py     # Solution correctness checker
│   ├── grammar_checker.py      # Grammar checker
│   ├── clarity_checker.py      # Clarity checker
│   └── tikz_checker.py         # TikZ code checker (v1)
│
├── prompts/                    # LLM prompt templates
│   ├── classifier.py
│   ├── tikz.py
│   ├── alternate.py
│   ├── idea.py
│   ├── converter.py
│   ├── reviewer.py
│   ├── solution_checker.py
│   ├── grammar_checker.py
│   ├── clarity_checker.py
│   ├── tikz_checker.py
│   ├── scanner/                # Question-type-specific scan prompts
│   │   ├── common.py
│   │   ├── mcq_sc.py
│   │   ├── mcq_mc.py
│   │   ├── assertion_reason.py
│   │   ├── match.py
│   │   ├── passage.py
│   │   └── subjective.py
│   ├── variants/               # Variant generation prompts
│   │   ├── numerical.py
│   │   ├── context.py
│   │   ├── conceptual.py
│   │   ├── conceptual_calculus.py
│   │   └── multi_context.py
│   └── subjects/               # Subject-specific prompt context
│       └── __init__.py
│
├── models/                     # Pydantic data models
│   ├── classification.py       # v1 models
│   ├── classification_v2.py    # v2 models (multi-agent)
│   ├── scan.py
│   ├── idea.py
│   ├── review.py
│   ├── diff.py
│   ├── pipeline.py
│   ├── batch.py
│   └── version_store.py
│
├── database/                   # SQLite question bank
│   ├── __init__.py
│   ├── store.py                # QuestionDatabase with extended schema
│   ├── extractor.py            # ContentExtractor
│   ├── reconstructor.py        # LaTeX reconstruction
│   └── metadata_helper.py      # Agent metadata population
│
├── parsers/                    # LaTeX parsing
│   ├── __init__.py
│   └── tex_parser.py           # Answer extraction
│
├── references/                 # Reference context management
│   ├── store.py                # Reference store (.tex, .sty, .pdf)
│   ├── context.py              # Context builder
│   └── tikz_store.py           # TikZ reference store with metadata
│
├── templates/
│   └── agentic_context.py      # CONTEXT.md generator
│
├── tests/                      # Test suite
│   └── agents/
│       └── classification/     # Multi-agent tests
│           ├── test_models.py  # Model tests (7 tests)
│           ├── test_router.py  # Router tests (8 tests)
│           └── test_database.py # Database tests (6 tests)
│
├── examples/
│   └── multi_agent_pipeline.py # Usage examples
│
└── docs/
    └── specs/
        ├── IMPLEMENTATION_STATUS.md # Complete status
        └── PERFORMANCE.md           # Performance guide
```
│   ├── batch.py
│   └── version_store.py
│
├── references/                 # Reference context management
│   ├── store.py                # Reference store (.tex, .sty, .pdf)
│   ├── context.py              # Context builder
│   └── tikz_store.py           # TikZ reference store with metadata
│
└── templates/
    └── agentic_context.py      # CONTEXT.md generator
```

## Development

```bash
pip install -e ".[dev]"
pytest
pytest tests/test_scanner.py -v
```

## Platform Support

Works on macOS, Windows, and Linux.

## License

MIT
