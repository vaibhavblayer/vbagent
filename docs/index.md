# VBAgent

**Multi-agent physics question processing system with conversational interface**

[![PyPI version](https://badge.fury.io/py/vbagent.svg)](https://pypi.org/project/vbagent/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What is VBAgent?

VBAgent is a comprehensive multi-agent system for processing physics, chemistry, mathematics, and biology questions. It combines AI-powered agents to handle everything from image scanning to problem generation, with a natural language chat interface.

## Key Features

### 🤖 **7 Specialized Agents**
- **Agent 1:** Image Classification - Fast categorization with gpt-4o-mini
- **Agent 2:** Diagram Analysis - Hierarchical diagram classification
- **Agent 3:** Difficulty Assessment - Detailed difficulty analysis
- **Agent 4:** LaTeX Classification - Batch processing of LaTeX files
- **Agent 5:** Idea Generator - Generate problems from concepts
- **Agent 6:** Problem Combiner - Combine multiple problems
- **Agent 7:** TikZ Checker - Automatic validation and fixing

### 💬 **Conversational Interface**
Generate complete problems from natural language:
```bash
$ vbagent chat
You: "Create a passage problem on double block friction"
Agent: *generates problem with TikZ, metadata, and everything*
```

### 📊 **Complete Pipeline**
- Image → LaTeX extraction
- TikZ diagram generation
- Classification and metadata
- Difficulty assessment
- Variant generation
- Database management

### ⚡ **Fast & Efficient**
- Parallel processing (Scanner + TikZ)
- Optimized model selection
- Smart caching

## Quick Start

```bash
# Install
pip install vbagent

# Initialize
vbagent init

# Process an image
vbagent process -i question.png

# Or use chat interface
vbagent chat
```

## Use Cases

- **Question Bank Creation:** Scan and organize thousands of questions
- **Problem Generation:** Create new problems from ideas
- **Variant Creation:** Generate numerical, contextual, and conceptual variants
- **TikZ Diagrams:** Auto-generate publication-quality diagrams
- **Metadata Extraction:** Rich metadata for searchable question banks
- **DPP Creation:** Smart problem set generation

## Architecture

```
Input (Image/LaTeX/Idea)
         ↓
   Classification (Agent 1 + 2)
         ↓
   ┌─────────────────┐
   │  Scanner + TikZ │  (Parallel)
   └─────────────────┘
         ↓
   Difficulty (Agent 3)
         ↓
   Metadata Merging
         ↓
   Output (LaTeX + JSON)
```

## What's New

### v0.2.2 - Conversational Problem Generation
- ✨ Generate problems from ideas using natural language
- 🤖 Full pipeline integration (TikZ, classification, difficulty)
- 💬 Interactive clarification in chat interface
- 📦 Complete metadata like image/tex processing

[See full changelog →](https://github.com/vaibhavblayer/vbagent/releases)

## Documentation

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quick-start.md)
- [CLI Commands Reference](user-guide/cli-commands.md)
- [Chat Interface Guide](user-guide/chat.md)
- [Problem Generation](user-guide/problem-generation.md)
- [API Reference](api/agents.md)

## Community

- [GitHub Issues](https://github.com/vaibhavblayer/vbagent/issues)
- [Discussions](https://github.com/vaibhavblayer/vbagent/discussions)
- [Contributing Guide](development/contributing.md)

## License

MIT License - see [LICENSE](https://github.com/vaibhavblayer/vbagent/blob/main/LICENSE) for details.
