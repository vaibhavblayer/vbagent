# CLI Quick Reference - New Options

## Range Selection (New!)

All commands that process multiple items now support intuitive range selection:

### New Options

| Option | Description | Example |
|--------|-------------|---------|
| `--from N` | Start from item N | `--from 1` |
| `--to N` | Process up to item N | `--to 10` |
| `--item N` | Process only item N | `--item 5` |

### Examples

```bash
# Process items 1 through 5
vbagent process -i image.png --from 1 --to 5

# Process from item 10 to end
vbagent process -i image.png --from 10

# Process first 5 items
vbagent process -i image.png --to 5

# Process only item 3
vbagent process -i image.png --item 3
```

### Old Format (Still Works)

```bash
# Old way (shows deprecation warning)
vbagent process -i image.png -r 1 5
vbagent process -i image.png --range 1 5
```

## Commands with Range Support

### 1. process - Full Pipeline Processing

```bash
# Process range of images
vbagent process -i images/Problem_1.png --from 1 --to 5

# Process single image
vbagent process -i images/Problem_3.png --item 3

# Process TeX file items
vbagent process -i problems.tex --from 1 --to 10
```

### 2. variant - Generate Problem Variants

```bash
# Generate variants for range
vbagent variant -i problems.tex --type numerical --from 1 --to 5

# Generate variant for single item
vbagent variant -i problems.tex --type context --item 3
```

### 3. check init - Initialize QA Tracking

```bash
# Initialize range for checking
vbagent check init --from 1 --to 50

# Initialize single problem
vbagent check init --item 5
```

### 4. ref tikz import - Import TikZ References

```bash
# Import range of TikZ files
vbagent ref tikz import agentic/scans --from 1 --to 10

# Import single TikZ file
vbagent ref tikz import agentic/scans --item 5
```

## Input Options (Standardized)

All commands now use consistent input options:

| Option | Description | Commands |
|--------|-------------|----------|
| `-i, --input` | Primary input option | All |
| `--image` | Alias for image input | classify, scan, process |
| `--tex` | Alias for TeX input | scan, process |

### Examples

```bash
# All equivalent
vbagent process -i image.png
vbagent process --input image.png
vbagent process --image image.png

# TeX files
vbagent process -i problem.tex
vbagent process --input problem.tex
vbagent process --tex problem.tex
```

## Output Options (Standardized)

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output directory | `agentic` |

```bash
vbagent process -i image.png -o my_output
vbagent process -i image.png --output my_output
```

## Verbosity (Standardized)

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed output |

```bash
vbagent classify -i image.png -v
vbagent scan -i image.png --verbose
vbagent process -i image.png -v
```

## Common Patterns

### Process Multiple Images

```bash
# Images named Problem_1.png, Problem_2.png, ..., Problem_10.png
vbagent process -i images/Problem_1.png --from 1 --to 10
```

### Process TeX File Items

```bash
# Process items 1-5 from a TeX file with \item markers
vbagent process -i problems.tex --from 1 --to 5
```

### Generate Variants for Range

```bash
# Generate numerical variants for items 1-10
vbagent variant -i problems.tex --type numerical --from 1 --to 10
```

### Initialize QA Tracking

```bash
# Initialize problems 1-50 for quality checking
vbagent check init --from 1 --to 50
```

### Import TikZ References

```bash
# Import TikZ from problems 1-20
vbagent ref tikz import agentic/scans --from 1 --to 20
```

## Migration Guide

### Old → New

| Old Format | New Format | Notes |
|------------|------------|-------|
| `-r 1 5` | `--from 1 --to 5` | More intuitive |
| `--range 1 5` | `--from 1 --to 5` | Clearer intent |
| `--image file.png` | `-i file.png` | Shorter, consistent |
| `--tex file.tex` | `-i file.tex` | Auto-detects type |

### Why Change?

**Before:**
```bash
vbagent process --image image.png -r 1 5
# What does "1 5" mean? Start and end? Or something else?
```

**After:**
```bash
vbagent process -i image.png --from 1 --to 5
# Crystal clear: from 1 to 5
```

## Tips

### 1. Use --item for Single Items
```bash
# Instead of
vbagent process -i image.png --from 3 --to 3

# Use
vbagent process -i image.png --item 3
```

### 2. Omit --to to Process to End
```bash
# Process from item 10 to the end
vbagent process -i image.png --from 10
```

### 3. Omit --from to Start from Beginning
```bash
# Process first 5 items
vbagent process -i image.png --to 5
```

### 4. Use -i for All Input Types
```bash
# Works for images
vbagent process -i image.png

# Works for TeX
vbagent process -i problem.tex

# Auto-detects file type
```

## Error Messages

### Invalid Range
```bash
$ vbagent process -i image.png --from 10 --to 5
Error: --from must be <= --to
```

### Deprecation Warning
```bash
$ vbagent process -i image.png -r 1 5
Note: --range is deprecated, use --from and --to
```

## Subject Support

All commands now support multiple subjects:

- **Physics**: Mechanics, electricity, optics, etc.
- **Chemistry**: Organic, inorganic, physical chemistry
- **Mathematics**: Calculus, algebra, geometry

```bash
# Physics problem
vbagent process -i physics/mechanics.png

# Chemistry problem
vbagent process -i chemistry/organic.png

# Mathematics problem
vbagent process -i math/calculus.png
```

## Quick Command Reference

### Most Common Commands

```bash
# Classify an image
vbagent classify -i image.png

# Scan to LaTeX
vbagent scan -i image.png

# Full pipeline
vbagent process -i image.png

# Generate variants
vbagent variant -i problem.tex --type numerical

# Quality check
vbagent check run -c 5

# Import TikZ references
vbagent ref tikz import agentic/scans --from 1 --to 10
```

### With Range Selection

```bash
# Process multiple images
vbagent process -i images/Problem_1.png --from 1 --to 10

# Generate variants for range
vbagent variant -i problems.tex --type numerical --from 1 --to 5

# Initialize QA for range
vbagent check init --from 1 --to 50

# Import TikZ range
vbagent ref tikz import agentic/scans --from 1 --to 20
```

## Help

Get help for any command:

```bash
vbagent --help
vbagent process --help
vbagent variant --help
vbagent check --help
```

## Summary

✅ **Clearer**: `--from` and `--to` instead of `-r 1 5`  
✅ **Flexible**: Can omit either `--from` or `--to`  
✅ **Convenient**: `--item N` for single items  
✅ **Consistent**: Same pattern across all commands  
✅ **Compatible**: Old format still works with warnings  

The new CLI options make vbagent easier to use and more intuitive while maintaining full backward compatibility.
