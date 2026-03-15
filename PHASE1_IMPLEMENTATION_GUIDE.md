# Phase 1: Option Standardization - Implementation Guide

## Status: IN PROGRESS

### Completed ✅
- [x] `classify.py` - Updated with standardized options

### In Progress 🔄
- [ ] Core commands (scan, process, batch)
- [ ] Generation commands (tikz, idea, alternate, variant, convert)
- [ ] Other commands

## Standard Option Patterns

### Primary Options (Use in ALL commands)
```python
@click.option(
    "-i", "--input", "--image", "--tex",  # Accept all for compatibility
    "input_path",  # Parameter name
    required=True,
    type=click.Path(exists=True),
    help="Input file path (image, tex, json)"
)

@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Output file or directory path"
)

@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Verbose output with additional details"
)

@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
    default="table",
    help="Output format"
)
```

### Processing Options (Use where applicable)
```python
@click.option(
    "-c", "--compile",
    is_flag=True,
    help="Compile LaTeX to validate"
)

@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable caching"
)

@click.option(
    "--subject",
    type=click.Choice(["physics", "chemistry", "mathematics"]),
    help="Override subject detection"
)
```

### Selection Options
```python
@click.option(
    "-r", "--range",
    nargs=2,
    type=int,
    help="Range of items (start end, 1-based inclusive)"
)

@click.option(
    "-n", "--count",
    type=int,
    default=1,
    help="Number of items to generate"
)
```

## Deprecation Warning Pattern

Add this at the start of each command function:

```python
def command_name(input_path: str, ...):
    console = _get_console()
    
    # Show deprecation warnings
    import sys
    if '--image' in sys.argv:
        console.print("[yellow]Note:[/yellow] --image is deprecated, use --input or -i", style="dim")
    if '--tex' in sys.argv:
        console.print("[yellow]Note:[/yellow] --tex is deprecated, use --input or -i", style="dim")
    
    # Rest of command logic
    ...
```

## Help Text Template

```python
def command_name(...):
    """<One-line description>
    
    <Detailed description paragraph explaining what the command does>
    
    <Optional: Additional context about subject support, features, etc.>
    
    \b
    Examples:
        # Basic usage
        vbagent command -i input.png
        
        # With output
        vbagent command -i input.png -o output.tex
        
        # Subject-specific examples
        vbagent command -i chemistry/problem.png
        vbagent command -i math/calculus.png
    
    \b
    Supported Subjects:
        - Physics: <examples>
        - Chemistry: <examples>
        - Mathematics: <examples>
    
    \b
    See Also:
        vbagent related-command --help
    """
```

## Files to Update

### Priority 1: Core Commands (Most Used)
1. ✅ `vbagent/cli/core/classify.py`
2. ⚠️ `vbagent/cli/core/scan.py`
3. ⚠️ `vbagent/cli/core/process.py`
4. ⚠️ `vbagent/cli/core/batch.py`

### Priority 2: Generation Commands
5. ⚠️ `vbagent/cli/generation/tikz.py`
6. ⚠️ `vbagent/cli/generation/idea.py`
7. ⚠️ `vbagent/cli/generation/alternate.py`
8. ⚠️ `vbagent/cli/generation/variant.py`
9. ⚠️ `vbagent/cli/generation/convert.py`
10. ⚠️ `vbagent/cli/generation/fbd.py`

### Priority 3: Other Commands
11. ⚠️ `vbagent/cli/quality/check.py`
12. ⚠️ `vbagent/cli/interfaces/chat.py`
13. ⚠️ `vbagent/cli/main.py` - Update main description

## Specific Changes Per Command

### scan.py
```python
# OLD
-i, --image PATH
-t, --tex PATH

# NEW
-i, --input, --image, --tex PATH  # Accept all
--reference PATH  # For secondary tex file
```

### process.py
```python
# OLD
-i, --image PATH
-t, --tex PATH

# NEW
-i, --input, --image, --tex PATH
```

### tikz.py
```python
# OLD
-i, --image PATH
-d, --description TEXT
-t, --tex PATH

# NEW
-i, --input, --image PATH
--description TEXT  # Remove -d short form
--reference PATH  # Instead of -t for reference tex
```

### variant.py
```python
# OLD
-i, --image PATH
-t, --tex PATH
--type TYPE

# NEW
-i, --input, --image, --tex PATH
--variant-type TYPE  # More specific
```

### idea.py, alternate.py
```python
# OLD
-t, --tex PATH

# NEW
-i, --input, --tex PATH
```

## Testing Checklist

After updating each command:
- [ ] `vbagent command --help` shows new options
- [ ] Old options still work (--image, --tex)
- [ ] Deprecation warnings appear when using old options
- [ ] New --input option works
- [ ] Help text mentions subject support
- [ ] Examples show multiple subjects
- [ ] No breaking changes to existing scripts

## Rollout Strategy

1. **Update commands one by one**
2. **Test each command** after update
3. **Document changes** in CHANGELOG.md
4. **Update README** with new examples
5. **Create migration guide** for users

## Success Criteria

- [ ] All commands use standardized options
- [ ] Backward compatibility maintained
- [ ] Deprecation warnings in place
- [ ] Help texts updated with subject info
- [ ] Examples show multi-subject usage
- [ ] No breaking changes
- [ ] Tests pass

## Next Steps After Phase 1

1. Gather user feedback
2. Monitor deprecation warning usage
3. Plan Phase 2 (command grouping)
4. Set deprecation timeline
5. Prepare Phase 2 migration guide
