# Installation

## Requirements

- Python 3.12 or higher
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)
- For compilation: `pdflatex` (TeX Live or MacTeX)

## Install from PyPI

```bash
pip install vbagent
```

That's it! All dependencies are included.

## Install from Source

```bash
git clone https://github.com/vaibhavblayer/vbagent.git
cd vbagent
pip install -e .
```

## Verify Installation

```bash
vbagent --version
```

## Set Up API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Add to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## Optional: LaTeX Compilation

For PDF generation and validation:

### macOS
```bash
brew install --cask mactex
```

### Ubuntu/Debian
```bash
sudo apt-get install texlive-full
```

### Windows
Download and install [MiKTeX](https://miktex.org/download)

## Next Steps

- [Quick Start Tutorial](quick-start.md)
- [Configuration Guide](configuration.md)
