# VBAgent

A multi-agent CLI tool for processing physics question images. Supports classification, LaTeX extraction, TikZ diagram generation, variant creation, and format conversion.

## Project Structure

```
vbagent/
├── pyproject.toml              # Project config & dependencies
├── poetry.lock                 # Locked dependency versions
├── README.md                   # Documentation
│
├── vbagent/                    # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration handling
│   │
│   ├── cli/                    # CLI commands (Click-based)
│   │   ├── main.py             # Entry point
│   │   ├── common.py           # Shared CLI utilities
│   │   ├── scan.py             # LaTeX extraction command
│   │   ├── classify.py         # Classification command
│   │   ├── tikz.py             # TikZ generation command
│   │   ├── variant.py          # Variant generation command
│   │   ├── alternate.py        # Alternate solutions command
│   │   ├── idea.py             # Concept extraction command
│   │   ├── convert.py          # Format conversion command
│   │   ├── process.py          # Full pipeline command
│   │   ├── batch.py            # Batch processing command
│   │   ├── check.py            # QA review command
│   │   ├── ref.py              # Reference management command
│   │   └── config.py           # Config management command
│   │
│   ├── agents/                 # AI agent implementations
│   │   ├── base.py             # Base agent class
│   │   ├── scanner.py          # LaTeX extraction agent
│   │   ├── classifier.py       # Question type classifier
│   │   ├── tikz.py             # TikZ diagram generator
│   │   ├── variant.py          # Single variant generator
│   │   ├── multi_variant.py    # Multi-context variant generator
│   │   ├── alternate.py        # Alternate solution generator
│   │   ├── idea.py             # Concept extractor
│   │   ├── converter.py        # Format converter
│   │   ├── reviewer.py         # QA reviewer
│   │   ├── selector.py         # Problem selector
│   │   ├── solution_checker.py # Solution correctness checker
│   │   ├── grammar_checker.py  # Grammar checker
│   │   ├── clarity_checker.py  # Clarity checker
│   │   └── tikz_checker.py     # TikZ code checker
│   │
│   ├── prompts/                # LLM prompt templates
│   │   ├── classifier.py       # Classification prompts
│   │   ├── tikz.py             # TikZ generation prompts
│   │   ├── alternate.py        # Alternate solution prompts
│   │   ├── idea.py             # Concept extraction prompts
│   │   ├── converter.py        # Conversion prompts
│   │   ├── reviewer.py         # Review prompts
│   │   ├── solution_checker.py # Solution check prompts
│   │   ├── grammar_checker.py  # Grammar check prompts
│   │   ├── clarity_checker.py  # Clarity check prompts
│   │   ├── tikz_checker.py     # TikZ check prompts
│   │   │
│   │   ├── scanner/            # Question-type-specific scan prompts
│   │   │   ├── common.py       # Shared scanner prompts
│   │   │   ├── mcq_sc.py       # MCQ single correct
│   │   │   ├── mcq_mc.py       # MCQ multiple correct
│   │   │   ├── assertion_reason.py
│   │   │   ├── match.py        # Match the following
│   │   │   ├── passage.py      # Passage/comprehension
│   │   │   └── subjective.py   # Subjective/numerical
│   │   │
│   │   └── variants/           # Variant generation prompts
│   │       ├── numerical.py    # Numerical variant prompts
│   │       ├── context.py      # Context variant prompts
│   │       ├── conceptual.py   # Conceptual variant prompts
│   │       ├── conceptual_calculus.py
│   │       └── multi_context.py
│   │
│   ├── models/                 # Pydantic data models
│   │   ├── batch.py            # Batch processing state
│   │   ├── classification.py   # Question classification
│   │   ├── scan.py             # Scan results
│   │   ├── idea.py             # Extracted concepts
│   │   ├── review.py           # Review results
│   │   ├── diff.py             # Diff utilities
│   │   ├── pipeline.py         # Pipeline state
│   │   └── version_store.py    # Version tracking
│   │
│   ├── references/             # Reference context management
│   │   ├── store.py            # Reference store
│   │   ├── context.py          # Context builder
│   │   └── tikz_store.py       # TikZ reference store
│   │
│   └── templates/              # Output templates
│       └── agentic_context.py  # CONTEXT.md generator
│
├── prompt_kinds/               # Question type definitions
│   ├── mcq_sc_type.py          # MCQ single correct
│   ├── mcq_mc_type.py          # MCQ multiple correct
│   ├── assertion_reason_type.py
│   ├── match_type.py           # Match the following
│   ├── passage_type.py         # Passage/comprehension
│   ├── subjective_type.py      # Subjective/numerical
│   ├── variant_numerical.py    # Numerical variant type
│   ├── variant_context.py      # Context variant type
│   ├── variant_conceptual.py   # Conceptual variant type
│   ├── variant_conceptual_calculus.py
│   └── variant_numerical_context.py
│
└── tests/                      # Test suite
    ├── test_scanner.py
    ├── test_classification.py
    ├── test_tikz.py
    ├── test_variant.py
    ├── test_alternate.py
    ├── test_idea.py
    ├── test_converter.py
    ├── test_batch.py
    ├── test_process.py
    ├── test_review.py
    ├── test_selector.py
    ├── test_context.py
    ├── test_reference_store.py
    ├── test_version_store.py
    └── test_prompt_organization.py
```

## Command Reference

### classify

Classify physics question image type.

```bash
vbagent classify -i <image> [-o <output.json>] [--json]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to physics question image (required) |
| `-o, --output` | Output JSON file path |
| `--json` | Output result as JSON to stdout |

### scan

Extract LaTeX from physics question image.

```bash
vbagent scan -i <image> [-t <tex>] [--type <type>] [-o <output.tex>]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to physics question image |
| `-t, --tex` | Path to existing TeX file (for re-processing) |
| `--type` | Override question type: `mcq_sc`, `mcq_mc`, `subjective`, `assertion_reason`, `passage`, `match` |
| `-o, --output` | Output TeX file path |

### tikz

Generate TikZ/PGF code for diagrams.

```bash
vbagent tikz [-i <image>] [-d <description>] [--ref <dir>...] [-o <output.tex>]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to diagram image |
| `-d, --description` | Text description of diagram to generate |
| `--ref` | Reference directories (can be used multiple times) |
| `-o, --output` | Output TeX file path |

### idea

Extract physics concepts and ideas from problems.

```bash
vbagent idea -t <tex> [-o <output.json>] [--json]
```

| Option | Description |
|--------|-------------|
| `-t, --tex` | Path to TeX file with problem and solution (required) |
| `-o, --output` | Output JSON file path |
| `--json` | Output result as JSON to stdout |

### alternate

Generate alternative solution methods.

```bash
vbagent alternate -t <tex> [--ideas <ideas.json>] [-n <count>] [-o <output.tex>]
```

| Option | Description |
|--------|-------------|
| `-t, --tex` | Path to TeX file with problem and solution (required) |
| `--ideas` | Path to ideas JSON file for context |
| `-n, --count` | Number of alternate solutions (default: 1) |
| `-o, --output` | Output TeX file path |

### variant

Generate problem variants with controlled modifications.

```bash
vbagent variant [-i <image>] [-t <tex>] --type <type> [-r <start> <end>] [-n <count>] [--context <file>...] [--ideas <ideas.json>] [-o <output.tex>]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Image file (will be scanned first) |
| `-t, --tex` | TeX file containing problem(s) |
| `--type` | Variant type: `numerical`, `context`, `conceptual`, `calculus`, `multi` (required) |
| `-r, --range` | Range of items to process (1-based inclusive) |
| `-n, --count` | Number of variants per problem (default: 1) |
| `--context` | Additional context files for multi variant |
| `--ideas` | Path to ideas JSON file |
| `-o, --output` | Output TeX file path |

### convert

Convert physics questions between formats.

```bash
vbagent convert [-i <image>] [-t <tex>] [--from <format>] --to <format> [-o <output.tex>]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Path to physics question image |
| `-t, --tex` | Path to TeX file |
| `--from` | Source format (auto-detected if not specified) |
| `--to` | Target format: `mcq_sc`, `mcq_mc`, `subjective`, `integer` (required) |
| `-o, --output` | Output TeX file path |

### process

Full pipeline: Classify → Scan → TikZ → Ideas → Variants.

```bash
vbagent process [-i <image>] [-t <tex>] [-r <start> <end>] [--variants <types>] [--alternate] [--ideas] [--ref <dir>...] [-o <output>] [--context] [-p <workers>]
```

| Option | Description |
|--------|-------------|
| `-i, --image` | Image file to process |
| `-t, --tex` | TeX file containing problems |
| `-r, --range` | Range to process (1-based inclusive) |
| `--variants` | Variant types (comma-separated) |
| `--alternate` | Generate alternate solutions |
| `--ideas` | Extract physics concepts |
| `--ref` | Reference directories for TikZ |
| `-o, --output` | Output directory (default: `agentic`) |
| `--context/--no-context` | Use reference context (default: yes) |
| `-p, --parallel` | Parallel workers (default: 1, max: 10) |

### batch

Batch processing with resume capability.

```bash
# Initialize batch
vbagent batch init [-i <images_dir>] [-o <output>] [--variants <types>] [--alternate] [--context]

# Continue processing
vbagent batch continue [--reset-failed]

# Check status
vbagent batch status
```

| Subcommand | Description |
|------------|-------------|
| `init` | Initialize and start batch processing |
| `continue` | Resume from where you left off |
| `status` | Show current progress |

#### batch init options

| Option | Description |
|--------|-------------|
| `-i, --images-dir` | Directory containing images (default: `./images`) |
| `-o, --output` | Output directory (default: `agentic`) |
| `--variants` | Variant types (default: all) |
| `--alternate/--no-alternate` | Generate alternates (default: yes) |
| `--context/--no-context` | Use reference context (default: yes) |

### check

QA review with interactive approval workflow.

```bash
# Start review session
vbagent check run [-c <count>] [-p <problem_id>] [-d <dir>]

# View history
vbagent check history [-p <problem_id>] [-f <file>] [-n <limit>]

# Apply suggestion
vbagent check apply <version_id> [-e]

# Resume session
vbagent check resume <session_id>
```

| Subcommand | Description |
|------------|-------------|
| `run` | Start a random QA review session |
| `init` | Initialize problem tracking database |
| `continue` | Continue from where you left off |
| `status` | Show check progress |
| `recheck` | Reset problems for rechecking |
| `alternate` | Generate alternate solutions |
| `idea` | Generate idea summaries |
| `solution` | Check solution correctness |
| `grammar` | Check grammar and spelling |
| `clarity` | Check clarity and conciseness |
| `tikz` | Check TikZ diagram code |
| `apply` | Apply a stored suggestion |
| `history` | View suggestion history |
| `resume` | Resume interrupted session |
| `stats` | View review statistics |

### ref

Manage reference context files.

```bash
# Add reference
vbagent ref add <category> <file> [-n <name>] [-d <description>]

# Remove reference
vbagent ref remove <category> <name>

# List references
vbagent ref list [-c <category>]

# Show reference content
vbagent ref show <category> <name>

# Enable/disable context
vbagent ref enable
vbagent ref disable

# Show status
vbagent ref status

# Set max examples
vbagent ref set-max <count>
```

| Subcommand | Description |
|------------|-------------|
| `add` | Add a reference file to a category |
| `remove` | Remove a reference file |
| `list` | List all reference files |
| `show` | Show content of a reference file |
| `enable` | Enable context usage in prompts |
| `disable` | Disable context usage |
| `status` | Show context configuration |
| `set-max` | Set maximum examples per category |

Categories: `tikz`, `latex`, `variants`, `problems`

#### ref tikz (TikZ references with metadata)

```bash
# Import from processed problem
vbagent ref tikz import <path> [-r <start> <end>] [-t <tikz_dir>] [-c <class_dir>]

# List TikZ references
vbagent ref tikz list [--diagram-type <type>] [--topic <topic>]

# Remove TikZ reference
vbagent ref tikz remove <ref_id>

# Show TikZ reference
vbagent ref tikz show <ref_id>

# Show statistics
vbagent ref tikz status
```

### config

Configure models and settings.

```bash
# Show current config
vbagent config show

# Set agent config
vbagent config set <agent_type> [--model <model>] [--reasoning <level>] [--temperature <temp>] [--max-tokens <tokens>]

# Reset to defaults
vbagent config reset

# List available models
vbagent config models
```

| Subcommand | Description |
|------------|-------------|
| `show` | Show current model configuration |
| `set` | Set model configuration for an agent |
| `reset` | Reset all configurations to defaults |
| `models` | List available models |

Agent types: `classifier`, `scanner`, `tikz`, `idea`, `alternate`, `variant`, `converter`, `default`

Reasoning levels: `low`, `medium`, `high`, `xhigh`

## Installation

### From PyPI

```bash
pip install vbagent
```

### From Source

```bash
# Clone the repository
git clone https://github.com/vaibhavblayer/vbagent.git
cd vbagent

# Install with pip
pip install .

# Or install in development mode
pip install -e .

# Or using Poetry
poetry install
```

## Requirements

- Python 3.12+
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key"
```

Or configure via the CLI:

```bash
vbagent config set api-key YOUR_API_KEY
```

## Usage

### Quick Start

```bash
# Scan a physics question image to LaTeX
vbagent scan -i question.png -o output.tex

# Classify a question type
vbagent classify -i question.png

# Generate TikZ diagram from image
vbagent tikz -i diagram.png -o diagram.tex

# Generate problem variants
vbagent variant -t problem.tex -o variants.tex
```

### Commands

| Command | Description |
|---------|-------------|
| `classify` | Classify physics question image type |
| `scan` | Extract LaTeX from question image |
| `tikz` | Generate TikZ/PGF code for diagrams |
| `idea` | Extract physics concepts and ideas |
| `alternate` | Generate alternative solutions |
| `variant` | Generate problem variants (numerical, conceptual, context) |
| `convert` | Convert between question formats |
| `process` | Run full processing pipeline |
| `batch` | Batch process multiple images with resume capability |
| `ref` | Manage reference context files |
| `config` | Configure models and settings |
| `check` | QA review with interactive approval |

### Batch Processing

Process multiple images with automatic resume on interruption:

```bash
# Initialize batch processing
vbagent batch init -i ./images -o ./output

# Continue processing (resumes from where it left off)
vbagent batch continue

# Check status
vbagent batch status
```

### Full Pipeline

Process a single image through the complete pipeline:

```bash
# Basic processing (classify + scan + tikz)
vbagent process -i question.png

# With ideas extraction
vbagent process -i question.png --ideas

# With alternate solutions
vbagent process -i question.png --alternate

# With variant generation
vbagent process -i question.png --variants numerical,context

# Full pipeline with all features
vbagent process -i question.png --ideas --alternate --variants numerical,context,conceptual
```

Process a range of images:

```bash
# Process Problem_1.png through Problem_5.png
vbagent process -i images/Problem_1.png -r 1 5

# Process range with parallel workers (faster)
vbagent process -i images/Problem_1.png -r 1 10 --parallel 3

# Process range with all features
vbagent process -i images/Problem_1.png -r 1 5 --ideas --alternate --variants numerical
```

Process TeX file with multiple items:

```bash
# Process items 1-5 from a TeX file
vbagent process -t problems.tex --range 1 5

# With alternate solutions and ideas
vbagent process -t problems.tex --range 1 5 --alternate --ideas
```

Custom output directory:

```bash
vbagent process -i question.png -o ./my_output
```

#### Process Command Options

| Option | Description |
|--------|-------------|
| `-i, --image` | Image file to process |
| `-t, --tex` | TeX file containing problems |
| `-r, --range` | Range of items to process (1-based, inclusive) |
| `--variants` | Variant types (comma-separated: numerical,context,conceptual,calculus) |
| `--alternate` | Generate alternate solutions |
| `--ideas` | Extract physics concepts |
| `--ref` | Reference directories for TikZ |
| `-o, --output` | Output directory (default: agentic) |
| `--context` | Use reference context (default: yes) |
| `-p, --parallel` | Parallel workers for batch (default: 1, max: 10) |

#### Output Structure

```
agentic/
├── scans/problem_1.tex           # Extracted LaTeX
├── classifications/problem_1.json # Question metadata
├── tikz/problem_1.tex            # Generated TikZ diagrams
├── ideas/problem_1.json          # Physics concepts (if --ideas)
├── alternates/problem_1.tex      # Alternate solutions (if --alternate)
├── variants/
│   ├── numerical/problem_1.tex   # Numerical variants
│   ├── context/problem_1.tex     # Context variants
│   └── conceptual/problem_1.tex  # Conceptual variants
└── CONTEXT.md                    # Documentation for AI agents
```

### Help

```bash
# General help
vbagent --help

# Command-specific help
vbagent scan --help
vbagent variant --help
```

### Scan Command

Extract LaTeX from physics question images:

```bash
# Basic scan with auto-classification
vbagent scan -i question.png

# Save output to file
vbagent scan -i question.png -o output.tex

# Override question type (skip classification)
vbagent scan -i question.png --type mcq_sc
```

### Variant Command

Generate problem variants with controlled modifications:

```bash
# Numerical variant (change numbers only)
vbagent variant -t problem.tex --type numerical

# Context variant (change scenario)
vbagent variant -t problem.tex --type context

# Generate multiple variants
vbagent variant -t problem.tex --type numerical --count 3

# Process range of items
vbagent variant -t problems.tex --type numerical -r 1 5

# Multi-context variant (combine problems)
vbagent variant --type multi --context p1.tex --context p2.tex -o combined.tex

# From image (scans first)
vbagent variant -i image.png --type numerical -o variant.tex
```

#### Variant Types

| Type | Description |
|------|-------------|
| `numerical` | Change only numbers, keep context |
| `context` | Change scenario, keep numbers |
| `conceptual` | Change physics concept |
| `calculus` | Add calculus elements |
| `multi` | Combine multiple problems |

### Alternate Command

Generate alternative solution methods:

```bash
# Generate one alternate solution
vbagent alternate -t problem.tex

# Generate multiple alternates
vbagent alternate -t problem.tex -n 3

# With ideas context
vbagent alternate -t problem.tex --ideas ideas.json

# Save to file
vbagent alternate -t problem.tex -n 2 -o alternates.tex
```

### Check Command (QA Review)

AI-powered quality review with interactive approval workflow:

```bash
# Start a review session (random 5 problems)
vbagent check run

# Review more problems
vbagent check run -c 10

# Review specific problem
vbagent check run -p Problem_42

# Review from specific directory
vbagent check run -d ./my_output

# View suggestion history
vbagent check history

# Apply a stored suggestion
vbagent check apply 42

# Resume interrupted session
vbagent check resume abc123
```

#### Check Subcommands

| Subcommand | Description |
|------------|-------------|
| `run` | Start a random QA review session |
| `history` | View suggestion history |
| `apply` | Apply a stored suggestion by ID |
| `resume` | Resume an interrupted session |
| `solution` | Check solution correctness |
| `grammar` | Check grammar and spelling |
| `clarity` | Check clarity and conciseness |
| `tikz` | Check TikZ diagram code |

### TikZ Command

Generate TikZ/PGF code for diagrams:

```bash
# From image
vbagent tikz -i diagram.png

# With description
vbagent tikz -d "A block on an inclined plane with friction"

# Save to file
vbagent tikz -i diagram.png -o diagram.tex

# With reference directories
vbagent tikz -i diagram.png --ref ./tikz_examples/
```

### Idea Command

Extract physics concepts and ideas from problems:

```bash
# From TeX file
vbagent idea -t problem.tex

# Save to JSON
vbagent idea -t problem.tex -o ideas.json
```

## Supported Question Types

- MCQ Single Correct
- MCQ Multiple Correct
- Assertion-Reason
- Match the Following
- Passage/Comprehension
- Subjective/Numerical

## Variant Types

- **Numerical**: Change numerical values while preserving physics
- **Conceptual**: Modify the underlying concept
- **Context**: Change the real-world scenario

## Platform Support

Works on macOS, Windows, and Linux. Sleep prevention during batch processing is supported on all platforms.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test
pytest tests/test_scanner.py -v
```

## License

MIT
