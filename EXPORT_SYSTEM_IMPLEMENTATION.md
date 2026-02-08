# Export System Implementation

## Overview

Successfully implemented the Export System for the Conversational Orchestrator feature (Task 9). The system provides flexible LaTeX file export in three different formats: flat, structured, and project modes.

## Components Implemented

### 1. Core Export Module (`vbagent/export/`)

#### `exporter.py`
- **ExportMode Enum**: Defines three export modes
  - `FLAT`: All files in a single directory
  - `STRUCTURED`: Organized subdirectories by type (questions/, solutions/, diagrams/, etc.)
  - `PROJECT`: main.tex with \input{} references

- **ExportResult Dataclass**: Contains export operation results
  - `output_dir`: Directory where files were exported
  - `file_count`: Number of files exported
  - `mode`: Export mode used
  - `main_tex`: Path to main.tex (for PROJECT mode)
  - `created_at`: Timestamp of export
  - `to_dict()`: Convert to dictionary format

- **Exporter Class**: Main export functionality
  - `export()`: Export files in specified format
  - `_export_flat()`: Flat mode implementation with name conflict handling
  - `_export_structured()`: Structured mode with automatic categorization
  - `_export_project()`: Project mode with main.tex generation
  - `export_with_metadata()`: Export with associated metadata
  - `DEFAULT_TEMPLATE`: Built-in LaTeX template for project mode

### 2. CLI Commands (`vbagent/cli/export.py`)

Implemented three subcommands under `vbagent export`:

- **`export run`**: Export specific files
  - Arguments: List of file paths
  - Options: --output, --mode, --template, --title
  - Example: `vbagent export run file1.tex file2.tex -o output/ -m project`

- **`export directory`**: Export all files from a directory
  - Arguments: Directory path
  - Options: --output, --mode, --pattern, --recursive, --template, --title
  - Example: `vbagent export directory questions/ -o output/ -m structured`

- **`export modes`**: Display information about available export modes
  - Shows table with mode descriptions and use cases
  - Provides usage examples

### 3. Tool Wrappers (`vbagent/orchestrator/tool_wrappers.py`)

Registered two export tools for orchestrator/MCP integration:

- **`export_files`**: Export specific files
  - Parameters: files (array), output (string), mode (enum), template (string), title (string)
  - Validates mode against enum values
  - Returns export result dictionary

- **`export_directory`**: Export directory contents
  - Parameters: directory (string), output (string), mode (enum), pattern (string), recursive (boolean), template (string), title (string)
  - Supports glob patterns and recursive search
  - Returns export result with source directory info

- **`register_export_tools()`**: Registers both tools with ToolRegistry
  - Called from `register_core_tools()`
  - Provides JSON schemas for parameter validation

### 4. Main CLI Integration (`vbagent/cli/main.py`)

- Added "export" to LAZY_SUBCOMMANDS dictionary
- Updated help text to include export command
- Enables lazy loading for fast CLI startup

## Features

### Flat Export Mode
- Copies all files to a single directory
- Handles name conflicts by appending numbers (file_1.tex, file_2.tex)
- Simple and straightforward for quick sharing

### Structured Export Mode
- Automatically categorizes files based on parent directory names
- Creates subdirectories: questions/, solutions/, diagrams/, variants/, scans/, other/
- Pattern matching for intelligent organization
- Handles name conflicts within subdirectories

### Project Export Mode
- Generates compilable LaTeX project
- Creates main.tex with proper document structure
- Includes \input{} commands for all files
- Supports custom templates
- Numbers files sequentially (question_001.tex, question_002.tex, etc.)
- Default template includes common physics packages (amsmath, tikz, tasks, etc.)

### Custom Template Support
- Accepts custom LaTeX templates for project mode
- Template uses Python format strings: {title} and {content}
- Allows full control over document structure

## Testing

### Unit Tests (`tests/test_export.py`)
13 test cases covering:
- All three export modes
- Name conflict handling
- Custom template support
- Error handling (empty files, nonexistent files)
- Directory creation
- ExportResult serialization
- Metadata export

### Integration Tests (`tests/test_export_tools.py`)
9 test cases covering:
- Tool wrapper execution via ToolRegistry
- All export modes through tools
- Parameter validation
- Tool registration verification
- Tool definition schemas
- Recursive directory search
- Error handling

**All 22 tests passing ✓**

## Requirements Validated

This implementation satisfies the following requirements from the spec:

- **Requirement 6.1**: Flat export mode implemented
- **Requirement 6.2**: Structured export mode implemented
- **Requirement 6.3**: Project export mode with main.tex and \input{} references
- **Requirement 6.4**: Custom template support implemented
- **Requirement 6.5**: Export mode selection working correctly

## Usage Examples

### CLI Usage

```bash
# Export files in flat mode
vbagent export run file1.tex file2.tex -o output/ -m flat

# Export directory with structured organization
vbagent export directory questions/ -o output/ -m structured

# Create LaTeX project with custom title
vbagent export run *.tex -o output/ -m project --title "My DPP"

# Use custom template
vbagent export run *.tex -o output/ -m project -t template.tex

# Export with pattern matching
vbagent export directory . -o output/ --pattern "dpp_*.tex"

# Show available modes
vbagent export modes
```

### Python API Usage

```python
from pathlib import Path
from vbagent.export import Exporter, ExportMode

# Create exporter
exporter = Exporter()

# Flat export
result = exporter.export(
    files=[Path("q1.tex"), Path("q2.tex")],
    output_dir=Path("output/"),
    mode=ExportMode.FLAT
)

# Project export with custom title
result = exporter.export(
    files=[Path("q1.tex"), Path("q2.tex")],
    output_dir=Path("output/"),
    mode=ExportMode.PROJECT,
    title="Daily Practice Problem Set"
)

# Access results
print(f"Exported {result.file_count} files")
print(f"Main file: {result.main_tex}")
```

### Tool Registry Usage

```python
from vbagent.orchestrator.tools import ToolRegistry
from vbagent.orchestrator.tool_wrappers import register_export_tools

# Register tools
registry = ToolRegistry()
register_export_tools(registry)

# Execute export via tool
result = await registry.execute(
    "export_files",
    {
        "files": ["q1.tex", "q2.tex"],
        "output": "output/",
        "mode": "project",
        "title": "My DPP"
    }
)
```

## File Structure

```
vbagent/
├── export/
│   ├── __init__.py          # Module exports
│   └── exporter.py          # Core export functionality
├── cli/
│   └── export.py            # CLI commands
└── orchestrator/
    └── tool_wrappers.py     # Tool registration (updated)

tests/
├── test_export.py           # Unit tests
└── test_export_tools.py     # Integration tests
```

## Next Steps

The export system is now fully integrated and ready for use:

1. ✅ Core export functionality implemented
2. ✅ CLI commands working
3. ✅ Tool wrappers registered
4. ✅ All tests passing
5. ✅ No diagnostic issues

The system can now be used:
- Directly via Python API
- Through CLI commands
- Via the orchestrator/chat interface
- Through MCP server (when implemented)

## Notes

- The export system follows the same patterns as other vbagent modules
- Lazy loading is used for CLI to maintain fast startup times
- JSON schema validation ensures type safety for tool parameters
- The system is extensible for future export modes or customizations
- All code follows existing vbagent conventions and style
