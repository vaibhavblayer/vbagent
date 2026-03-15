# vbagent Quick Reference Card

## New Features (This Session)

### Range Selection (NEW!)
```bash
# Old way (deprecated)
vbagent process -i image.png -r 1 5

# New way (recommended)
vbagent process -i image.png --from 1 --to 5
vbagent process -i image.png --item 3
```

### Compile Command (NEW!)
```bash
# Generate main.tex automatically
vbagent compile -t "Wave Motion" --problems "1,3,5,7,9"
vbagent compile --all-packages -t "Title" --from 1 --to 25
```

### Agent Logging (ENHANCED!)
```
⏳ TikZ running (gpt-5.4, medium reasoning)...
✓ TikZ completed in 39.2s (gpt-5.4, medium reasoning)
```

---

## Complete Workflow

```bash
# 1. Process problems
vbagent process -i images/Problem_1.png --from 1 --to 25

# 2. Generate main.tex
vbagent compile --all-packages -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"

# 3. Compile
pdflatex main.tex
```

---

## Range Options (All Commands)

| Option | Description | Example |
|--------|-------------|---------|
| `--from N` | Start index | `--from 1` |
| `--to N` | End index | `--to 10` |
| `--item N` | Single item | `--item 5` |
| `-r N M` | Old format (deprecated) | `-r 1 10` |

**Works in:** `process`, `variant`, `check init`, `ref tikz import`

---

## Compile Command

### Basic Usage
```bash
vbagent compile                    # All problems, physics
vbagent compile -t "Title"         # Custom title
vbagent compile -s chemistry       # Chemistry packages
vbagent compile --all-packages     # All packages (recommended)
```

### Problem Selection
```bash
vbagent compile --from 1 --to 10                    # Range
vbagent compile --problems "1,3,5,7,9"              # Explicit list
vbagent compile --problems "1,2,3,4,5,6,7,8,9,10"   # Long list
```

### Subject-Specific
```bash
vbagent compile -s physics      # circuitikz, kinematikz
vbagent compile -s chemistry    # chemfig, mhchem
vbagent compile -s mathematics  # tkz-euclide, venndiagram
vbagent compile --all-packages  # All of the above
```

---

## Common Commands

### Process
```bash
vbagent process -i image.png                    # Single image
vbagent process -i image.png --from 1 --to 5   # Range
vbagent process -i image.png --item 3           # Single item
vbagent process -i image.png -v                 # Verbose
```

### Classify
```bash
vbagent classify -i image.png           # Classify image
vbagent classify -i image.png -v        # Verbose
```

### Scan
```bash
vbagent scan -i image.png               # Scan to LaTeX
vbagent scan -i image.png -s chemistry  # Chemistry formatting
```

### Variant
```bash
vbagent variant -i problem.tex --type numerical --from 1 --to 5
vbagent variant -i problem.tex --type context --item 3
```

### Check
```bash
vbagent check init --from 1 --to 50     # Initialize QA
vbagent check run -c 5                  # Review 5 problems
vbagent check continue                  # Continue checking
```

### Compile
```bash
vbagent compile --all-packages -t "Title" --problems "1,2,3,4,5"
```

---

## Options Reference

### Input
- `-i, --input` - Input file (image or tex)
- `--image` - Alias for image input (deprecated)
- `--tex` - Alias for tex input (deprecated)

### Range
- `--from N` - Start index
- `--to N` - End index
- `--item N` - Single item
- `-r N M` - Old range format (deprecated)

### Output
- `-o, --output` - Output directory/file
- `-t, --title` - Document title (compile)

### Subject
- `-s, --subject` - Subject (physics/chemistry/mathematics)
- `--all-packages` - Include all packages (compile)

### Verbosity
- `-v, --verbose` - Verbose output
- `--debug` - Debug mode (in config)

---

## Agent Logging

### What You See
```
⏳ Agent running (model, reasoning)...
✓ Agent completed in X.Xs (model, reasoning)
```

### Reasoning Modes
- `none` - No reasoning (fast, cheap)
- `low` - Basic reasoning
- `medium` - Moderate reasoning (default for complex tasks)
- `high` - Deep reasoning (expensive)

### Example
```
⏳ Scanner-subjective-physics running (gpt-5.4, medium reasoning)...
✓ Scanner-subjective-physics completed in 39.2s (gpt-5.4, medium reasoning)
```

---

## Tips

### 1. Use --all-packages for Mixed Content
```bash
vbagent compile --all-packages -t "Title" --problems "..."
```

### 2. Use --item for Single Items
```bash
vbagent process -i image.png --item 3
```

### 3. Use --from/--to for Ranges
```bash
vbagent process -i image.png --from 1 --to 10
```

### 4. Check Agent Models
Look for the logging output to see which models are being used:
```
⏳ TikZ running (gpt-5.4, medium reasoning)...
```

---

## Help

```bash
vbagent --help              # Main help
vbagent process --help      # Command help
vbagent compile --help      # Compile help
```

---

## Quick Examples

### Process and Compile
```bash
vbagent process -i images/Problem_1.png --from 1 --to 25
vbagent compile --all-packages -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
pdflatex main.tex
```

### Chemistry Problems
```bash
vbagent process -i chemistry/problem.png
vbagent compile -s chemistry -t "Organic Chemistry"
```

### Mathematics Problems
```bash
vbagent process -i math/problem.png
vbagent compile -s mathematics -t "Calculus"
```

---

## Summary

**New in this session:**
- ✅ `--from` and `--to` for intuitive range selection
- ✅ `vbagent compile` for automatic main.tex generation
- ✅ `--all-packages` for mixed subject content
- ✅ Enhanced agent logging with model and reasoning info

**Your workflow:**
```bash
vbagent process -i images/Problem_1.png --from 1 --to 25
vbagent compile --all-packages -t "Title" --problems "..."
pdflatex main.tex
```

Simple, clear, and powerful! 🎉
