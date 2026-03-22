# vbagent Configuration Examples

This directory contains example configuration files for different use cases.

## How to Use

1. **Copy an example** that matches your needs
2. **Customize** the settings for your project
3. **Save as** `.vbagent.json` in your project root
4. **Commit to git** for team consistency (but don't commit API keys!)

## Available Examples

### 📚 Subject-Specific Configs

- **`chemistry_project.json`** - Optimized for chemistry problems
  - High-quality models for organic structures, mechanisms, equations
  - Balanced models for scanning and classification
  - Use: `cp chemistry_project.json .vbagent.json`

- **`physics_project.json`** - Optimized for physics problems
  - High-quality models for FBDs, circuits, graphs, optics
  - Precise diagram generation
  - Use: `cp physics_project.json .vbagent.json`

### 💰 Cost vs Quality Strategies

- **`cost_optimized.json`** - Minimize costs while maintaining quality
  - Fast models (gpt-5.4-mini) for simple tasks
  - Powerful models (gpt-5.4) only for diagrams
  - **Estimated savings: 60-70%** vs using gpt-5.4 everywhere
  - Use when: Processing large volumes, budget-conscious

- **`quality_first.json`** - Maximum quality, cost secondary
  - Best models (gpt-5.4) for everything
  - High reasoning for all agents
  - Use when: Research papers, textbooks, high-stakes work

### 🔌 Provider-Specific Configs

- **`xai_grok.json`** - xAI Grok models
  - Uses Grok models for all agents
  - Code-specialized models for diagrams
  - Frontier model for solutions
  - Requires: `XAI_API_KEY` environment variable

## Quick Start

### Chemistry Project
```bash
cd my-chemistry-project
cp examples/example_configs/chemistry_project.json .vbagent.json
# Edit .vbagent.json if needed
vbagent config show  # Verify settings
```

### Physics Project
```bash
cd my-physics-project
cp examples/example_configs/physics_project.json .vbagent.json
vbagent config show
```

### Cost-Optimized Setup
```bash
cp examples/example_configs/cost_optimized.json .vbagent.json
# Great for processing large volumes of problems
```

### xAI Grok Setup
```bash
export XAI_API_KEY=xai-xxx
cp examples/example_configs/xai_grok.json .vbagent.json
vbagent config show
```

## Customization Tips

### 1. Start with an Example
Pick the example closest to your needs, then customize.

### 2. Adjust Individual Agents
```bash
# After copying an example, fine-tune specific agents
vbagent config set tikz --model gpt-5.4 --reasoning high --workspace
vbagent config set scanner --model gpt-5.4-mini --reasoning medium --workspace
```

### 3. Test and Iterate
```bash
# Enable debug to see what's happening
vbagent config debug on --workspace

# Process a test image
vbagent process -i test.png

# Adjust models based on results
vbagent config set <agent> --model <model> --workspace

# Disable debug when done
vbagent config debug off --workspace
```

## Configuration Structure

All example configs follow this structure:

```json
{
  "subject": "physics|chemistry|mathematics",
  "debug": false,
  "log_level": "INFO",
  
  "default_model": "gpt-5.4-mini",
  "default_reasoning_effort": "medium",
  
  "agents": {
    "agent_name": {
      "model": "model-name",
      "reasoning_effort": "low|medium|high|xhigh",
      "max_tokens": 16000  // optional
    }
  }
}
```

## Agent Types Reference

### Classification Agents
- `classifier` - Main image classifier
- `image_classifier` - Image-specific classification
- `diagram_analyzer` - Diagram analysis
- `taxonomy_classifier` - Taxonomy classification
- `difficulty_assessor` - Difficulty assessment

**Recommendation:** Use fast models with low reasoning

### Content Generation Agents
- `scanner` - LaTeX extraction from images
- `solution` - Solution generation
- `converter` - Format conversion

**Recommendation:** Balanced models with medium reasoning

### Diagram Generation Agents

**Physics:**
- `fbd` - Free body diagrams
- `circuit` - Circuit diagrams (circuitikz)
- `graph` - Graphs and plots
- `optics` - Ray diagrams and optical systems
- `tikz` - Generic TikZ diagrams

**Chemistry:**
- `organic_structure` - Organic chemistry structures
- `reaction_mechanism` - Reaction mechanisms
- `chemical_equation` - Chemical equations
- `energy_diagram` - Energy diagrams
- `orbital` - Orbital diagrams
- `lewis_structure` - Lewis structures

**Mathematics:**
- `function_graph` - Function graphs
- `geometric_figure` - Geometric diagrams
- `number_line` - Number lines
- `venn_diagram` - Venn diagrams
- `coordinate_geometry` - Coordinate geometry

**Recommendation:** Use powerful models with high reasoning

### Variant & Quality Agents
- `variant` - Problem variant generation
- `alternate` - Alternate solution generation
- `idea` - Concept extraction
- `latex_fixer` - LaTeX error fixing
- `solution_checker` - Solution validation
- `format_checker` - Format checking

**Recommendation:** Varies by agent (see examples)

## Model Selection Guide

### OpenAI Models

**gpt-5.4-mini** - Fast & Cost-Effective
- Best for: Classification, scanning, quality checking
- Reasoning: low, medium, high
- Cost: Low
- Speed: Fast

**gpt-5.4** - High Quality
- Best for: Diagrams, solutions, variants
- Reasoning: low, medium, high, xhigh
- Cost: Medium
- Speed: Medium

**gpt-5.2** - Previous Generation
- Best for: Legacy compatibility
- Reasoning: low, medium, high, xhigh
- Cost: Medium
- Speed: Medium

### xAI Grok Models

**grok-4-1-fast-reasoning** - Recommended Default
- Best for: General tasks, agentic reasoning
- Context: 2M tokens
- Cost: $0.20/$0.50 per 1M tokens

**grok-code-fast-1** - Code Specialist
- Best for: TikZ, chemfig, code generation
- Context: 256k tokens
- Cost: $0.20/$1.50 per 1M tokens

**grok-4** - Frontier Reasoning
- Best for: Complex solutions, hard problems
- Context: 256k tokens
- Cost: $3/$15 per 1M tokens

### Google Gemini Models

**gemini-3-flash-preview** - Fast & Capable
- Best for: General tasks, thinking model
- Context: 1M tokens
- Reasoning: low, medium, high

**gemini-2.5-pro** - High Capability
- Best for: Complex tasks
- Reasoning: none, low, medium, high

## Reasoning Effort Guide

- **low** - Fast, basic reasoning
  - Use for: Classification, simple analysis
  - Speed: Fastest
  - Cost: Lowest

- **medium** - Balanced reasoning
  - Use for: Scanning, general tasks
  - Speed: Fast
  - Cost: Low

- **high** - Deep reasoning
  - Use for: Diagrams, solutions, variants
  - Speed: Medium
  - Cost: Medium

- **xhigh** - Maximum reasoning (gpt-5.2 only)
  - Use for: Hardest problems only
  - Speed: Slow
  - Cost: High

**Note:** Not all models support reasoning effort. Check with `vbagent config models`.

## Environment Variables

Instead of storing API keys in config files:

```bash
# OpenAI
export OPENAI_API_KEY=sk-xxx

# xAI
export XAI_API_KEY=xai-xxx

# Google
export GOOGLE_API_KEY=your-key
```

Add to your `~/.bashrc` or `~/.zshrc` for persistence.

## Best Practices

1. **Start with an example** - Don't create from scratch
2. **Use workspace config** - Commit `.vbagent.json` to git
3. **Environment variables for keys** - Never commit API keys
4. **Test with debug mode** - Enable debug when testing new configs
5. **Document your choices** - Add comments explaining model selections
6. **Optimize iteratively** - Start balanced, then optimize based on results

## Troubleshooting

### Config Not Loading
```bash
# Check which config is active
vbagent config show
# Should show: "Using workspace config: .vbagent.json"
```

### Invalid Model Name
```bash
# List available models
vbagent config models

# Check spelling (case-sensitive!)
```

### Reasoning Effort Not Supported
```bash
# Some models don't support reasoning_effort
# Remove the reasoning_effort field for those models
```

### API Key Issues
```bash
# Use environment variables instead of config file
export OPENAI_API_KEY=sk-xxx

# Or set in config
vbagent config provider openai --api-key sk-xxx
```

## More Information

- [Configuration Guide](../config_examples.md) - Comprehensive guide
- [Quick Reference](../config_quick_reference.md) - One-page reference
- `vbagent config --help` - CLI help
- `vbagent config <command> --help` - Command-specific help
