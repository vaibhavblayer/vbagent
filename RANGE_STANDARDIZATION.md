# Range Standardization: --from and --to

## Problem

Current implementation uses `-r, --range` with `nargs=2`:
```bash
vbagent process -i image.png --range 1 5
vbagent variant -i problem.tex --range 1 10
```

**Issues:**
- Not intuitive (what does "1 5" mean?)
- Not symmetric
- Harder to remember
- Doesn't match common CLI patterns

## Proposed Solution

Use `--from` and `--to` options (more intuitive and symmetric):

```bash
# New way (clearer)
vbagent process -i image.png --from 1 --to 5
vbagent variant -i problem.tex --from 1 --to 10

# Also support single value
vbagent process -i image.png --from 5  # Process only item 5
```

## Benefits

✅ **Intuitive**: Clear what each number means  
✅ **Symmetric**: Both options have same format  
✅ **Flexible**: Can specify just `--from` or just `--to`  
✅ **Readable**: Self-documenting  
✅ **Standard**: Matches common CLI patterns (git log --since/--until, etc.)  

## Implementation

### Standard Pattern

```python
@click.option(
    "--from", "from_index",
    type=int,
    default=None,
    help="Start index (1-based, inclusive)"
)
@click.option(
    "--to", "to_index",
    type=int,
    default=None,
    help="End index (1-based, inclusive)"
)
```

### Backward Compatibility

Keep `--range` as deprecated alias:

```python
@click.option(
    "-r", "--range", "range_tuple",
    nargs=2,
    type=int,
    default=None,
    help="[DEPRECATED] Use --from and --to instead"
)

# In function body
if range_tuple:
    console.print("[yellow]Note:[/yellow] --range is deprecated, use --from and --to", style="dim")
    from_index, to_index = range_tuple
```

### Usage Logic

```python
# Determine range
if range_tuple:  # Backward compatibility
    from_index, to_index = range_tuple
    
# Validate
if from_index and to_index and from_index > to_index:
    console.print("[red]Error:[/red] --from must be <= --to")
    raise SystemExit(1)

# Apply defaults
if from_index is None:
    from_index = 1  # Start from beginning
if to_index is None:
    to_index = len(items)  # Go to end
```

## Commands to Update

### 1. process.py
```python
# Current
-r, --range INTEGER...  # Range to process (1-based inclusive)

# New
--from INTEGER          # Start index (default: 1)
--to INTEGER            # End index (default: all)
-r, --range INTEGER...  # [DEPRECATED] Use --from and --to

# Examples
vbagent process -i image.png --from 1 --to 5
vbagent process -i image.png --from 10  # Process from 10 to end
vbagent process -i image.png --to 5     # Process first 5
```

### 2. variant.py
```python
# Current
-r, --range INTEGER...

# New
--from INTEGER
--to INTEGER
-r, --range INTEGER...  # [DEPRECATED]

# Examples
vbagent variant -i problem.tex --from 1 --to 10
vbagent variant -i problem.tex --from 5
```

### 3. check.py
```python
# Current
-r, --range INTEGER...

# New
--from INTEGER
--to INTEGER
-r, --range INTEGER...  # [DEPRECATED]

# Examples
vbagent check init --from 1 --to 50
vbagent check init --from 10
```

### 4. ref.py (tikz import)
```python
# Current
-r, --range INTEGER...

# New
--from INTEGER
--to INTEGER
-r, --range INTEGER...  # [DEPRECATED]

# Examples
vbagent ref tikz import problems.tex --from 1 --to 20
```

## Additional Improvements

### Support Both Formats

Allow both formats for maximum flexibility:

```bash
# Explicit (recommended)
vbagent process -i image.png --from 1 --to 5

# Shorthand (also supported)
vbagent process -i image.png --range 1 5  # Deprecated but works

# Single item
vbagent process -i image.png --from 5 --to 5
# Or shorthand
vbagent process -i image.png --item 5
```

### Add --item for Single Item

```python
@click.option(
    "--item",
    type=int,
    help="Process single item (shorthand for --from N --to N)"
)

# In function
if item:
    from_index = to_index = item
```

## Migration Strategy

### Phase 1: Add New Options (Non-Breaking)
1. Add `--from` and `--to` options
2. Keep `--range` working
3. Add deprecation warning for `--range`
4. Update documentation to show new options

### Phase 2: Deprecation Period (6 months)
1. Both old and new work
2. Warnings inform users
3. Update all examples to new format

### Phase 3: Remove Old (Optional)
1. Remove `--range` option
2. Clean up code

## Complete Example

### process.py Updated

```python
@click.option(
    "--from", "from_index",
    type=int,
    default=None,
    help="Start index (1-based, inclusive, default: 1)"
)
@click.option(
    "--to", "to_index",
    type=int,
    default=None,
    help="End index (1-based, inclusive, default: all)"
)
@click.option(
    "--item",
    type=int,
    default=None,
    help="Process single item (shorthand for --from N --to N)"
)
@click.option(
    "-r", "--range", "range_tuple",
    nargs=2,
    type=int,
    default=None,
    help="[DEPRECATED] Use --from and --to instead"
)
def process(
    input_path: str,
    from_index: Optional[int],
    to_index: Optional[int],
    item: Optional[int],
    range_tuple: Optional[tuple[int, int]],
    ...
):
    """Process questions with flexible range selection.
    
    \b
    Examples:
        # Process range
        vbagent process -i image.png --from 1 --to 5
        
        # Process from index to end
        vbagent process -i image.png --from 10
        
        # Process first N items
        vbagent process -i image.png --to 5
        
        # Process single item
        vbagent process -i image.png --item 3
        
        # Old format (deprecated)
        vbagent process -i image.png --range 1 5
    """
    console = _get_console()
    
    # Handle backward compatibility
    if range_tuple:
        console.print("[yellow]Note:[/yellow] --range is deprecated, use --from and --to", style="dim")
        from_index, to_index = range_tuple
    
    # Handle --item shorthand
    if item:
        from_index = to_index = item
    
    # Apply defaults
    if from_index is None:
        from_index = 1
    
    # Validate
    if to_index and from_index > to_index:
        console.print("[red]Error:[/red] --from must be <= --to")
        raise SystemExit(1)
    
    # Use from_index and to_index in processing
    ...
```

## Testing

### Test Cases

```bash
# Test new options
vbagent process -i image.png --from 1 --to 5
vbagent process -i image.png --from 10
vbagent process -i image.png --to 5
vbagent process -i image.png --item 3

# Test backward compatibility
vbagent process -i image.png --range 1 5  # Should work with warning

# Test validation
vbagent process -i image.png --from 10 --to 5  # Should error

# Test conflicts
vbagent process -i image.png --from 1 --to 5 --item 3  # Should error or use --item
```

## Summary

**Current:**
```bash
vbagent process -i image.png -r 1 5  # Not intuitive
```

**Proposed:**
```bash
vbagent process -i image.png --from 1 --to 5  # Clear and intuitive
vbagent process -i image.png --from 10        # From 10 to end
vbagent process -i image.png --to 5           # First 5 items
vbagent process -i image.png --item 3         # Single item
```

**Benefits:**
- ✅ More intuitive
- ✅ Symmetric design
- ✅ Flexible (can omit either)
- ✅ Self-documenting
- ✅ Backward compatible
- ✅ Follows CLI best practices

**Recommendation:** Implement in Phase 1 alongside other option standardization.
