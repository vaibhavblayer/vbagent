# Fix: Undefined \ce{} Command

## Problem

You got this error when compiling:
```
! Undefined control sequence.
l.7 \ce{CH4(g) + 3/2 O2(g) -> CO(g) + 2H2O(g)}
```

This means you have chemistry content (`\ce{}` from mhchem package) but generated a physics main.tex (which doesn't include mhchem).

## Solutions

### Option 1: Specify Chemistry Subject (Recommended if all problems are chemistry)

```bash
vbagent compile -s chemistry -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

This includes `\usepackage{chemfig, mhchem}` in the preamble.

### Option 2: Include All Packages (Recommended if mixed subjects)

```bash
vbagent compile --all-packages -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

This includes packages for physics, chemistry, AND mathematics, so all commands work.

### Option 3: Specify Mathematics Subject

```bash
vbagent compile -s mathematics -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

## Quick Fix for Your Case

Since you have chemistry content, run:

```bash
# Delete the incorrect main.tex
rm main.tex

# Regenerate with all packages (safest for mixed content)
vbagent compile --all-packages -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"

# Or if all problems are chemistry
vbagent compile -s chemistry -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"

# Then compile
pdflatex main.tex
```

## What Each Option Includes

### Physics (default: `-s physics`)
```latex
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
```

### Chemistry (`-s chemistry`)
```latex
\usepackage{chemfig, mhchem}  % <-- Includes \ce{} command
\usepackage{pgfplots}
```

### Mathematics (`-s mathematics`)
```latex
\usepackage{pgfplots, tkz-euclide}
\usepackage{venndiagram}
```

### All Packages (`--all-packages`)
```latex
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
\usepackage{chemfig, mhchem}  % <-- Chemistry
\usepackage{tkz-euclide}
\usepackage{venndiagram}
```

## Recommendation

For mixed content (physics + chemistry + math), always use:

```bash
vbagent compile --all-packages -t "Your Title" --problems "..."
```

This ensures all LaTeX commands work regardless of subject.

## Summary

The error happened because:
1. You have chemistry content (`\ce{}` command)
2. But generated a physics main.tex (no mhchem package)

Fix by regenerating with:
- `-s chemistry` (if all chemistry)
- `--all-packages` (if mixed subjects) ← **Recommended**
