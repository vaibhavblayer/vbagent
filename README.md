# VBAgent

A multi-agent library and CLI for processing physics, chemistry, and mathematics question images. Supports classification, LaTeX extraction, TikZ diagram generation, solution generation, variant creation, paper orchestration, and LaTeX compilation.

📚 **[Documentation](https://vaibhavblayer.github.io/vbagent/)** | 🐛 **[Issues](https://github.com/vaibhavblayer/vbagent/issues)** | 💬 **[Discussions](https://github.com/vaibhavblayer/vbagent/discussions)**

## Installation

```bash
pip install -e ".[dev]"
```

## Requirements

- Python 3.12+
- API key for your provider (set as env variable)
- For compilation: `pdflatex` (TeX Live or MacTeX)

### Supported Providers

| Provider | Env Variable | Models |
|----------|-------------|--------|
| OpenAI | `OPENAI_API_KEY` | gpt-5.4, gpt-5.4-mini, gpt-5.2, gpt-5.1, gpt-5.1-codex |
| xAI | `XAI_API_KEY` | grok-4, grok-4-1-fast-reasoning, grok-3, grok-3-mini |
| Google | `GOOGLE_API_KEY` | gemini-2.5-pro, gemini-2.5-flash, gemini-3-flash-preview |

### Default Models (OpenAI)

| Role | Model |
|------|-------|
| Classification, scanning, checking | `gpt-5.4-mini` |
| Generation (idea, variant, alternate, solution, tikz, fbd) | `gpt-5.4` |

Switch provider or model easily:
```bash
vbagent config provider xai              # Switch to xAI
vbagent config provider google           # Switch to Google
vbagent config provider openai           # Back to OpenAI
vbagent config set solution -m gpt-5.2   # Override solution model
vbagent config set tikz -m gpt-5.4       # Override tikz model
vbagent config set default -m gpt-5.4    # Change global default
```

## CLI Usage

### Quick Start

```bash
vbagent init                              # Initialize workspace config
vbagent scan -i question.png -o out.tex   # Extract LaTeX
vbagent classify -i question.png          # Classify question type
vbagent tikz -i diagram.png -o diag.tex   # Generate TikZ
vbagent run -i question.png               # Full pipeline
```

### Commands

| Section | Command | Description |
|---------|---------|-------------|
| Core | `run` | Full pipeline: classify → scan → tikz → solve |
| Core | `scan` | Extract LaTeX from question image |
| Core | `classify` | Classify question type |
| Core | `batch` | Batch process multiple images with resume |
| Generate | `tikz` | Generate TikZ/PGF diagrams |
| Generate | `fbd` | Free body diagram generation |
| Generate | `idea` | Extract physics concepts |
| Generate | `alternate` | Generate alternate solutions |
| Generate | `variant` | Generate problem variants |
| Generate | `convert` | Convert between question formats |
| Quality | `check` | QA review with interactive approval |
| Quality | `compile` | Compile LaTeX to PDF |
| Manage | `init` | Initialize workspace config |
| Manage | `config` | Configure models, providers, settings |
| Manage | `ref` | Manage reference context files |
| Manage | `cache` | Cache management |
| Manage | `db` | SQLite question bank |
| Manage | `metadata` | Question bank metadata |
| Manage | `export` | Export LaTeX (flat, structured, project) |
| Manage | `dpp` | Daily Practice Problem sets |
| Manage | `util` | File utilities (rename, count, clean) |
| Manage | `extans` | Extract answers from LaTeX |
| Manage | `screenshot` | Screenshot utilities |
| Interface | `chat` | Interactive conversational interface |
| Interface | `mcp` | MCP server for external agents |
| Paper | `paper` | Paper orchestration (init, generate, solve, hint, compile, export) |

### Paper Orchestrator

End-to-end paper generation workflow:

```bash
# Initialize a paper project
vbagent paper init physics --title "JEE Advanced 2025" --problems 4

# Generate problems from syllabus topics
vbagent paper generate /path/to/paper/

# Generate solutions for all problems
vbagent paper solve /path/to/paper/

# Generate hints
vbagent paper hint /path/to/paper/

# Compile to main.tex (stitches problems + solutions + hints + ideas + remarks)
vbagent paper compile /path/to/paper/

# Compile only solutions
vbagent paper compile /path/to/paper/ --only solutions

# Compile only hints
vbagent paper compile /path/to/paper/ --only hints

# Export zip for Overleaf
vbagent paper export /path/to/paper/
```

Paper directory structure:
```
paper_dir/
├── manifest.yaml          # Paper config (subject, title, problems)
├── main.tex               # Compiled output
├── scans/                 # Per-problem .tex files (problem + solution + hint + idea + remark)
│   ├── Problem_1.tex
│   ├── Problem_2.tex
│   └── ...
├── solutions/             # Raw solution .tex files
├── hints/                 # Raw hint .tex files
└── paper_export.zip       # Overleaf-ready zip
```

### Configuration

```bash
vbagent config show                       # Show all agent configs
vbagent config models                     # List available models
vbagent config provider                   # Show current provider
vbagent config provider xai               # Switch to xAI (auto-applies model group)
vbagent config provider openai            # Switch back to OpenAI
vbagent config set scanner -m gpt-5.4     # Override scanner model
vbagent config set default -m gpt-5.4     # Change global default
vbagent config model-group                # List all model groups
vbagent config model-group openai         # Apply OpenAI model group
vbagent config subject chemistry          # Set subject
vbagent config debug on                   # Enable debug mode
vbagent config reset                      # Reset to defaults
```

Config hierarchy: global (`~/.config/vbagent/models.json`) → workspace (`.vbagent.json`).

### Supported Question Types

- `mcq_sc` — MCQ Single Correct
- `mcq_mc` — MCQ Multiple Correct
- `assertion_reason` — Assertion-Reason
- `match` — Match the Following (matrix match with codes)
- `passage` — Passage/Comprehension (paragraph MCQ)
- `integer` — Integer type (`\ansint{N}`)
- `subjective` — Subjective/Numerical

## Project Structure

```
vbagent/
├── __init__.py                          # Public API with lazy imports
├── config.py                            # Configuration (models, providers, subjects)
├── compile.py                           # LaTeX compilation, validation, verbose debug
├── cache.py                             # Pipeline cache (solutions, hints, problems)
├── tex.py                               # TeX formatting utilities (format_tex, center_wrap_tikz)
│
├── cli/                                 # CLI commands (Click-based, lazy-loaded)
│   ├── main.py                          # Entry point with SectionedGroup
│   ├── common.py                        # Shared utilities (panels, prompts, formatting)
│   ├── core/
│   │   ├── init.py                      # Workspace initialization
│   │   ├── classify.py                  # Classification command
│   │   ├── scan.py                      # LaTeX extraction command
│   │   ├── process.py                   # Full pipeline command
│   │   └── batch.py                     # Batch processing command
│   ├── generation/
│   │   ├── tikz.py                      # TikZ generation command
│   │   ├── fbd.py                       # FBD generation command
│   │   ├── idea.py                      # Concept extraction command
│   │   ├── alternate.py                 # Alternate solutions command
│   │   ├── variant.py                   # Variant generation command
│   │   └── convert.py                   # Format conversion command
│   ├── quality/
│   │   └── check.py                     # QA review command
│   ├── compilation/
│   │   └── compile_main.py              # LaTeX compile command + preamble
│   ├── management/
│   │   ├── config.py                    # Config management (provider, model-group, set)
│   │   ├── ref.py                       # Reference management
│   │   ├── db.py                        # Database management
│   │   ├── metadata.py                  # Metadata management
│   │   ├── export.py                    # Export command
│   │   ├── dpp.py                       # DPP command
│   │   ├── extans.py                    # Answer extraction
│   │   ├── screenshot.py                # Screenshot utilities
│   │   └── util.py                      # File utilities
│   ├── cache/
│   │   └── cache_commands.py            # Cache management commands
│   ├── interfaces/
│   │   ├── chat.py                      # Chat interface
│   │   ├── mcp.py                       # MCP server
│   │   └── ui.py                        # UI helpers
│   └── paper/
│       └── paper_commands.py            # Paper orchestrator CLI (init, generate, solve, hint, compile, export)
│
├── agents/                              # AI agent implementations
│   ├── base.py                          # Base agent (create, run, encode image)
│   ├── classifier.py                    # Question type classifier (v1)
│   ├── classification/                  # Multi-agent classification system
│   │   ├── unified_classifier.py        # Unified classifier
│   │   ├── image_classifier.py          # Image classification
│   │   ├── diagram_analyzer.py          # Diagram analysis
│   │   ├── difficulty_assessor.py       # Difficulty assessment
│   │   ├── latex_classifier.py          # LaTeX classification
│   │   ├── idea_generator.py            # Idea-to-problem generator
│   │   ├── problem_combiner.py          # Multi-problem combiner
│   │   ├── taxonomy_classifier.py       # Taxonomy classification
│   │   ├── subject_detector.py          # Subject auto-detection
│   │   └── schema_builder.py            # Schema builder
│   ├── content_generation/
│   │   ├── scanner.py                   # LaTeX extraction agent
│   │   ├── alternate.py                 # Alternate solution agent
│   │   ├── converter.py                 # Format converter agent
│   │   ├── idea.py                      # Concept extractor agent
│   │   └── solution/
│   │       └── __init__.py              # Solution agent (routes by subject × question_type)
│   ├── diagram/                         # TikZ diagram agents
│   │   ├── base.py                      # Base diagram agent (600s timeout, style discipline)
│   │   ├── tikz.py                      # Generic TikZ agent
│   │   ├── tikz_router.py              # TikZ agent routing
│   │   ├── tikz_checker.py             # TikZ validation agent
│   │   ├── mcq_option_coordinator.py   # MCQ option diagram coordinator
│   │   ├── physics/
│   │   │   ├── fbd.py                   # Free body diagram
│   │   │   ├── circuit.py               # Circuit diagram
│   │   │   ├── graph.py                 # Physics graph
│   │   │   └── optics.py               # Optics diagram
│   │   ├── chemistry/
│   │   │   ├── organic_structure.py     # Organic structure
│   │   │   ├── organic_orchestrator.py  # Organic multi-step orchestrator
│   │   │   ├── organic_simple.py        # Simple organic
│   │   │   ├── organic_complex.py       # Complex organic
│   │   │   ├── organic_functional.py    # Functional group
│   │   │   ├── organic_mechanism.py     # Reaction mechanism
│   │   │   ├── organic_multistep.py     # Multi-step synthesis
│   │   │   ├── organic_stereo.py        # Stereochemistry
│   │   │   ├── chemical_equation.py     # Chemical equation
│   │   │   ├── energy_diagram.py        # Energy diagram
│   │   │   ├── lewis_structure.py       # Lewis structure
│   │   │   ├── orbital.py              # Orbital diagram
│   │   │   └── reaction_mechanism.py    # Reaction mechanism
│   │   └── mathematics/
│   │       ├── coordinate_geometry.py   # Coordinate geometry
│   │       ├── function_graph.py        # Function graph
│   │       ├── geometric_figure.py      # Geometric figure
│   │       ├── number_line.py           # Number line
│   │       └── venn_diagram.py          # Venn diagram
│   ├── orchestration/
│   │   ├── problem_orchestrator.py      # Problem orchestrator
│   │   └── solution_orchestrator.py     # Solution orchestrator
│   ├── quality/
│   │   ├── base.py                      # Base quality agent
│   │   ├── reviewer.py                  # QA reviewer
│   │   ├── solution_checker.py          # Solution checker
│   │   ├── grammar_checker.py           # Grammar checker
│   │   ├── clarity_checker.py           # Clarity checker
│   │   ├── format_checker.py            # Format checker
│   │   └── latex_fixer.py              # LaTeX fixer
│   ├── variants/
│   │   ├── variant.py                   # Single variant generator
│   │   ├── cross_topic.py              # Cross-topic variant
│   │   └── multi_context_variant.py    # Multi-context variant
│   ├── selection/
│   │   └── selector.py                 # Problem selector
│   └── metadata/
│       └── enricher.py                 # Metadata enricher
│
├── prompts/                             # LLM prompt templates
│   ├── classification/
│   │   ├── classifier.py                # Base classifier prompt
│   │   ├── unified_classifier.py        # Unified classifier prompt
│   │   ├── diagram_analyzer.py          # Diagram analyzer prompt
│   │   ├── idea_generator.py            # Idea generator prompt
│   │   ├── problem_combiner.py          # Problem combiner prompt
│   │   ├── question_types.py            # Question type definitions
│   │   └── taxonomy.py                  # Taxonomy definitions
│   ├── content_generation/
│   │   ├── alternate.py                 # Alternate solution prompt
│   │   ├── converter.py                 # Converter prompt
│   │   ├── idea.py                      # Idea extraction prompt
│   │   ├── scanner/                     # Scanner prompts (per subject × question type)
│   │   │   ├── _shared.py               # Shared scanner rules
│   │   │   ├── physics/
│   │   │   │   ├── common.py            # Physics common rules
│   │   │   │   ├── formatting_rules.py  # Physics formatting
│   │   │   │   ├── mcq_sc.py, mcq_mc.py, subjective.py
│   │   │   │   ├── assertion_reason.py, match.py, passage.py
│   │   │   │   ├── problem_only.py, solution_only.py
│   │   │   │   └── __init__.py          # Router
│   │   │   ├── chemistry/               # (same structure as physics)
│   │   │   └── mathematics/             # (same structure as physics)
│   │   └── solution/                    # Solution prompts (per subject × question type)
│   │       ├── __init__.py              # Top-level router
│   │       ├── physics/
│   │       │   ├── common.py            # Physics solution rules
│   │       │   ├── mcq_sc.py, mcq_mc.py, subjective.py
│   │       │   ├── assertion_reason.py, match.py, passage.py
│   │       │   └── __init__.py          # Router
│   │       ├── chemistry/               # (same structure as physics)
│   │       └── mathematics/             # (same structure as physics)
│   ├── diagram/
│   │   ├── _style_discipline.py         # TikZ style rules (no colors, no inline overrides)
│   │   ├── tikz_checker.py              # TikZ checker prompt
│   │   ├── physics/
│   │   │   ├── fbd.py, circuit.py, graph.py, optics.py, generic.py
│   │   │   └── __init__.py
│   │   ├── chemistry/
│   │   │   ├── organic_structure.py, organic_simple.py, organic_complex.py
│   │   │   ├── organic_functional.py, organic_mechanism.py, organic_multistep.py
│   │   │   ├── organic_stereo.py, chemical_equation.py, energy_diagram.py
│   │   │   ├── lewis_structure.py, orbital.py, reaction_mechanism.py
│   │   │   └── __init__.py
│   │   └── mathematics/
│   │       ├── coordinate_geometry.py, function_graph.py, geometric_figure.py
│   │       ├── number_line.py, venn_diagram.py
│   │       └── __init__.py
│   ├── quality/
│   │   ├── reviewer.py, solution_checker.py, grammar_checker.py
│   │   ├── clarity_checker.py, format_checker.py
│   │   └── __init__.py
│   ├── variants/
│   │   ├── numerical.py, context.py, conceptual.py
│   │   ├── conceptual_calculus.py, cross_topic.py, multi_context.py
│   │   └── __init__.py
│   └── subjects/
│       └── __init__.py                  # Subject-specific context
│
├── models/                              # Pydantic data models
│   ├── classification.py                # Classification models
│   ├── content.py                       # Content models
│   ├── diagram.py                       # Diagram models
│   ├── diff.py                          # Diff models
│   ├── metadata.py                      # Metadata models
│   ├── orchestration.py                 # Orchestration models
│   ├── pipeline.py                      # Pipeline models
│   ├── quality.py                       # Quality models
│   ├── review.py                        # Review models
│   ├── solution.py                      # Solution models
│   ├── version_store.py                 # Version store models
│   └── workflow.py                      # Workflow models
│
├── paper/                               # Paper orchestrator
│   ├── __init__.py
│   ├── models.py                        # Paper data models
│   ├── manifest.py                      # Manifest YAML handling
│   ├── syllabus.py                      # Syllabus topic definitions
│   ├── generator.py                     # Problem generation
│   ├── orchestrator.py                  # Paper orchestrator (compile, export, assemble)
│   └── qa.py                            # Paper QA
│
├── pipeline/                            # Processing pipeline
│   ├── __init__.py
│   ├── io.py                            # Pipeline I/O
│   ├── runner.py                        # Pipeline runner
│   └── stages.py                        # Pipeline stages
│
├── database/                            # SQLite question bank
│   ├── store.py                         # QuestionDatabase
│   ├── extractor.py                     # ContentExtractor
│   ├── reconstructor.py                 # LaTeX reconstruction
│   └── metadata_helper.py              # Agent metadata population
│
├── references/                          # Reference context management
│   ├── store.py                         # Reference store
│   ├── context.py                       # Context builder
│   ├── tikz_store.py                    # TikZ reference store
│   └── samples/                         # Sample references
│       ├── physics/                     # assertion_reason.tex, mcq_mc.tex, mcq_sc.tex, subjective.tex
│       ├── chemistry/                   # mcq_mc.tex, mcq_sc.tex, subjective.tex
│       └── mathematics/                 # mcq_mc.tex, mcq_sc.tex, subjective.tex
│
├── storage/                             # Content storage
│   ├── content_cache.py                 # Content cache
│   └── metadata_manager.py             # Metadata manager
│
├── orchestrator/                        # Chat orchestrator
│   ├── conversation.py                  # Conversation handler
│   ├── tools.py                         # Tool definitions
│   └── tool_wrappers.py               # Tool wrappers
│
├── dpp/
│   └── builder.py                       # DPP builder
│
├── export/
│   └── exporter.py                      # LaTeX exporter
│
├── mcp/
│   └── server.py                        # MCP server
│
├── metadata/
│   └── store.py                         # Metadata store
│
├── templates/
│   └── agentic_context.py              # CONTEXT.md generator
│
├── ui/                                  # Terminal UI
│   ├── components.py                    # UI components
│   ├── logging.py                       # Logging
│   ├── styles.py                        # Styles
│   └── tables.py                        # Tables
│
└── utils/
    ├── formatting.py                    # Formatting utilities
    └── latex.py                         # LaTeX utilities

tests/
├── agents/
│   ├── classification/                  # test_classification.py, test_database.py, test_models.py, test_router.py
│   ├── content_generation/              # test_alternate.py, test_converter.py, test_idea.py, test_scanner.py
│   ├── diagram/                         # test_tikz.py
│   ├── metadata/                        # test_metadata.py
│   ├── orchestration/                   # test_orchestrator.py
│   ├── quality/                         # test_review.py
│   ├── selection/                       # test_selector.py
│   └── variants/                        # test_variant.py
├── cli/
│   ├── core/                            # test_batch.py, test_process.py
│   ├── interfaces/                      # test_chat_cli.py, test_chat_interface.py, test_mcp_server.py
│   └── management/                      # test_config.py, test_export_tools.py, test_export.py
├── integration/                         # test_context.py, test_dpp_builder.py, test_import_performance.py, ...
├── models/                              # test_version_store.py
├── paper/                               # test_cli.py, test_generator.py, test_manifest.py, test_models.py, ...
├── ui/                                  # test_ui_components.py
└── utils/                               # test_formatting.py, test_latex.py, test_tex_parser.py
```

## LaTeX Compilation

The `-c` / `--compile` flag validates generated LaTeX by compiling with `pdflatex`. If compilation fails, the compile-fixer agent automatically attempts to fix errors (up to 2 retries).

### Compile Preamble

- `fourier[upright]` for fonts
- `\everymath{\displaystyle}` for display-style math
- `amsmath`, `amssymb`, `amsthm`, `mathtools`
- `tikz` with libraries: calc, decorations, patterns, arrows.meta, positioning, shapes, intersections, angles, quotes
- `circuitikz` (american style), `pgfplots` (compat=1.18)
- `tasks` (MCQ options), `enumitem`
- `mhchem`, `chemfig` (chemistry only)
- Auto-detected packages from `.tex` file content

### Environment Definitions

| Environment | Color | Symbol |
|-------------|-------|--------|
| `solution` | red | `$\Rightarrow$` |
| `alternatesolution` | blue | `$\Rrightarrow$` |
| `hint` | maroon | `$\looparrowright$` |
| `idea` | violet | `$\diamond$` |
| `remark` | teal | `$\circ$` |

## License

MIT
