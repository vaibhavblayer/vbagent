# Tool Wrappers Usage Guide

This document describes how to use the tool wrapper functions that expose core vbagent commands as tools for the conversational orchestrator.

## Overview

The tool wrappers in `vbagent/orchestrator/tool_wrappers.py` provide a unified interface for registering and executing vbagent commands through the ToolRegistry. These tools can be called by:
- The conversational orchestrator (LLM-based)
- MCP servers for external agents
- Direct programmatic access

## Registered Tools

### 1. scan
Extract LaTeX from a physics question image using OCR and AI.

**Parameters:**
- `image` (required): Path to the physics question image file
- `question_type` (optional): Override question type (mcq_sc, mcq_mc, subjective, assertion_reason, passage, match)
- `output` (optional): Output TeX file path for saving results
- `compile` (optional): Whether to compile LaTeX to validate it (default: False)

**Returns:**
```python
{
    "latex": str,              # Extracted LaTeX code
    "has_diagram": bool,       # Whether the question has a diagram
    "diagram_description": str,# Description of the diagram if present
    "question_type": str,      # Detected or provided question type
    "output_path": str         # Path where output was saved (if output specified)
}
```

### 2. classify
Classify a physics question image to extract metadata.

**Parameters:**
- `image` (required): Path to the physics question image file
- `output` (optional): Output JSON file path for saving results

**Returns:**
```python
{
    "question_type": str,      # Type of question (mcq_sc, subjective, etc.)
    "difficulty": str,         # Difficulty level
    "topic": str,              # Main topic
    "subtopic": str,           # Subtopic
    "has_diagram": bool,       # Whether question has a diagram
    "diagram_type": str,       # Type of diagram if present
    "num_options": int,        # Number of options for MCQ
    "requires_calculus": bool, # Whether calculus is required
    "confidence": float,       # Classification confidence (0-1)
    "key_concepts": list[str], # List of key physics concepts
    "output_path": str         # Path where output was saved (if output specified)
}
```

### 3. tikz
Generate TikZ/PGF diagram code for physics diagrams.

**Parameters:**
- `description` (optional): Text description of the diagram to generate
- `image` (optional): Path to a diagram image file
- `tex` (optional): Path to TeX file with problem text
- `output` (optional): Output TeX file path for saving the generated TikZ code
- `compile` (optional): Whether to compile TikZ to validate it (default: False)

**Note:** At least one of `description`, `image`, or `tex` must be provided.

**Returns:**
```python
{
    "tikz_code": str,          # Generated TikZ/PGF code
    "output_path": str         # Path where output was saved (if output specified)
}
```

### 4. variant
Generate problem variants with controlled modifications.

**Parameters:**
- `variant_type` (required): Type of variant (numerical, context, conceptual, calculus, multi)
- `tex` (optional): Path to TeX file containing problem(s)
- `image` (optional): Path to image file (will be scanned first)
- `count` (optional): Number of variants to generate per problem (default: 1)
- `output` (optional): Output TeX file path for saving results
- `compile` (optional): Whether to compile variants to validate them (default: False)

**Note:** Either `tex` or `image` must be provided.

**Returns:**
```python
{
    "variants": list[str],     # List of generated variant LaTeX strings
    "variant_type": str,       # Type of variant generated
    "count": int,              # Number of variants generated
    "output_path": str         # Path where output was saved (if output specified)
}
```

### 5. convert
Convert physics questions between different formats.

**Parameters:**
- `target_format` (required): Target format (mcq_sc, mcq_mc, subjective, integer, match, passage)
- `tex` (optional): Path to TeX file containing the question
- `image` (optional): Path to physics question image (will be scanned first)
- `source_format` (optional): Source format (auto-detected if not specified)
- `output` (optional): Output TeX file path for saving results

**Note:** Either `tex` or `image` must be provided.

**Returns:**
```python
{
    "converted_latex": str,    # Converted LaTeX code
    "source_format": str,      # Source format (detected or provided)
    "target_format": str,      # Target format
    "output_path": str         # Path where output was saved (if output specified)
}
```

## Usage Examples

### Registering Tools

```python
from vbagent.orchestrator import ToolRegistry, register_core_tools

# Create a registry
registry = ToolRegistry()

# Register all core tools
register_core_tools(registry)

# List registered tools
print(registry.list_tools())  # ['scan', 'classify', 'tikz', 'variant', 'convert']
```

### Executing Tools Directly

```python
# Execute a tool directly (for testing)
result = scan_tool(
    image="question.png",
    question_type="mcq_sc",
    output="output.tex"
)
print(result["latex"])
```

### Executing Tools Through Registry

```python
import asyncio
from vbagent.orchestrator import ToolRegistry, register_core_tools

async def main():
    registry = ToolRegistry()
    register_core_tools(registry)
    
    # Execute classify tool
    result = await registry.execute(
        "classify",
        {"image": "question.png"}
    )
    print(f"Question type: {result['question_type']}")
    print(f"Confidence: {result['confidence']}")

asyncio.run(main())
```

### Getting Tool Definitions for LLM APIs

```python
from vbagent.orchestrator import ToolRegistry, register_core_tools

registry = ToolRegistry()
register_core_tools(registry)

# For OpenAI
openai_tools = registry.get_tool_definitions_openai()

# For Anthropic
anthropic_tools = registry.get_tool_definitions_anthropic()

# For MCP
mcp_tools = registry.get_tool_definitions_mcp()

# For Google
google_tools = registry.get_tool_definitions_google()

# For xAI (uses OpenAI format)
xai_tools = registry.get_tool_definitions_xai()
```

## Tool Definition Format

Each tool is registered with:
- **name**: Unique identifier
- **description**: Human-readable description for LLMs
- **parameters**: JSON Schema defining the tool's parameters
- **function**: The actual Python function to execute

Example:
```python
registry.register(
    name="scan",
    description="Extract LaTeX from a physics question image...",
    parameters={
        "type": "object",
        "properties": {
            "image": {
                "type": "string",
                "description": "Path to the physics question image file"
            },
            # ... more properties
        },
        "required": ["image"]
    },
    function=scan_tool
)
```

## Error Handling

All tool functions raise appropriate exceptions:
- `FileNotFoundError`: When specified files don't exist
- `ValueError`: When invalid parameters are provided
- Other exceptions from underlying vbagent functions

The ToolRegistry validates arguments against JSON schemas before execution and wraps execution errors with context about which tool failed.

## Testing

Comprehensive tests are available in:
- `tests/test_tool_wrappers.py`: Unit tests for individual tool wrappers
- `tests/test_tool_integration.py`: Integration tests for tools with the registry
- `tests/test_tool_registry.py`: Tests for the ToolRegistry itself

Run tests with:
```bash
pytest tests/test_tool_wrappers.py -v
pytest tests/test_tool_integration.py -v
```

## Next Steps

These tools are now ready to be used by:
1. The conversational orchestrator (Task 2)
2. The chat interface (Task 3)
3. The MCP server (Task 11)

The tools provide a unified interface that works across all these contexts with consistent behavior and error handling.
