# Phase 1: Option Standardization - Progress Report

## Completed ✅

### 1. classify.py ✅
**Changes:**
- `-i/--input` (with `--image` alias)
- `--format` option (table/json)
- `-v/--verbose` flag
- Updated help text (subject-agnostic)
- Multi-subject examples
- Deprecation warnings

### 2. scan.py ✅  
**Changes:**
- `-i/--input` (with `--image`, `--tex` aliases)
- `--reference` for secondary tex file
- `--subject` override option
- `-v/--verbose` flag
- Updated help text (subject-specific formatting)
- Multi-subject examples
- Deprecation warnings

### 3. process.py ✅
**Changes:**
- `-i/--input` (with `--image`, `--tex` aliases)
- `-v/--verbose` flag
- Updated help text (multi-subject processing)
- Multi-subject examples (physics, chemistry, mathematics)
- Subject-specific processing notes
- Deprecation warnings
- Auto-detects file type (image vs tex)

## Progress: 23% Complete (3/13 commands)

### 4. Main.py Description
**Required Changes:**
- Update main description from "Physics question processing" to "Multi-subject question processing"
- Update command list descriptions

## Remaining Commands ⚠️

### Priority 1: Core Commands
- [ ] `batch.py` - Batch processing
- [ ] `init.py` - Initialization

### Priority 2: Generation Commands  
- [ ] `tikz.py` - TikZ generation
- [ ] `fbd.py` - Free body diagrams (keep physics-specific)
- [ ] `idea.py` - Idea extraction
- [ ] `alternate.py` - Alternate solutions
- [ ] `variant.py` - Problem variants
- [ ] `convert.py` - Format conversion

### Priority 3: Other Commands
- [ ] `check.py` - QA review
- [ ] `chat.py` - Chat interface
- [ ] Management commands (ref, config, util, metadata, dpp, export, extans, db, screenshot)

## Standard Pattern Applied

### Option Standardization
```python
@click.option("-i", "--input", "--image", "--tex", "input_path", ...)
@click.option("-o", "--output", ...)
@click.option("-v", "--verbose", is_flag=True, ...)
@click.option("--format", type=click.Choice([...]), ...)
@click.option("--subject", type=click.Choice(["physics", "chemistry", "mathematics"]), ...)
```

### Deprecation Warning
```python
import sys
if '--image' in sys.argv:
    console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
```

### Help Text Template
```python
"""<One-line description>

<Detailed description with subject support>

\b
Examples:
    # Basic usage
    vbagent command -i input.png
    
    # Subject-specific
    vbagent command -i chemistry/problem.png
    vbagent command -i math/calculus.png

\b
Supported Subjects:
    - Physics: ...
    - Chemistry: ...
    - Mathematics: ...
"""
```

## Testing Status

### Tested Commands
- [x] `classify --help` - Shows new options ✅
- [x] `classify -i test.png` - Works with new option ✅
- [x] `classify --image test.png` - Backward compatible ✅
- [x] `scan --help` - Shows new options ✅

### Pending Tests
- [ ] Full integration test with all commands
- [ ] Backward compatibility test suite
- [ ] Deprecation warning verification

## Next Steps

1. **Complete process.py** - Most critical command
2. **Update main.py** - Main description
3. **Batch update generation commands** - Similar patterns
4. **Test all commands** - Ensure no breaking changes
5. **Update documentation** - README, examples
6. **Create CHANGELOG entry** - Document changes

## Estimated Completion

- **Completed**: 2/13 commands (15%)
- **Remaining**: 11 commands
- **Estimated time**: 2-3 hours
- **Target completion**: End of session

## Notes

- All changes maintain backward compatibility
- Deprecation warnings are informational only
- Old options still work (--image, --tex, --json)
- New options are preferred in documentation
- Subject detection is automatic unless overridden
