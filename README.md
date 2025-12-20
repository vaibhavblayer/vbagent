# VBAgent

A multi-agent CLI tool for processing physics question images. Supports classification, LaTeX extraction, TikZ diagram generation, variant creation, and format conversion.

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
vbagent process -i question.png -o ./output
```

### Help

```bash
# General help
vbagent --help

# Command-specific help
vbagent scan --help
vbagent variant --help
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
