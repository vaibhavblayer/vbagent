# Quick Start: Compile Command

## Your Exact Use Case

You have processed problems and want to generate a main.tex file like this:

```latex
\documentclass{article}
% ... packages ...
\title{\textsc{Wave Motion}}
\begin{document}
\maketitle
\begin{enumerate}
\foreach \i in {1,...,13, 16, 19, 22, 25}{
  \input{agentic/scans/problem_\i.tex}
}
\end{enumerate}
\end{document}
```

## Solution

### One Command

```bash
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

This generates `main.tex` ready to compile!

### Then Compile

```bash
pdflatex main.tex
```

## Complete Workflow

```bash
# 1. Process your problems
vbagent process -i images/Problem_1.png --from 1 --to 25

# 2. Generate main.tex (NEW!)
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"

# 3. Compile to PDF
pdflatex main.tex
```

## Common Patterns

### All Problems in Range

```bash
vbagent compile -t "Wave Motion" --from 1 --to 13
```

### Specific Problems (Your Case)

```bash
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

### Chemistry Problems

```bash
vbagent compile -s chemistry -t "Organic Chemistry"
```

### Mathematics Problems

```bash
vbagent compile -s mathematics -t "Calculus"
```

## Options

| Option | Example | Description |
|--------|---------|-------------|
| `-t` | `-t "Wave Motion"` | Document title |
| `-s` | `-s chemistry` | Subject (physics/chemistry/mathematics) |
| `--problems` | `--problems "1,3,5,7"` | Specific problem list |
| `--from` | `--from 1` | Start index |
| `--to` | `--to 13` | End index |
| `-o` | `-o output.tex` | Output filename |
| `-d` | `-d output/scans` | Scans directory |

## What It Does

1. **Discovers** all problem files in `agentic/scans/`
2. **Generates** proper LaTeX preamble with subject-specific packages
3. **Includes** specified problems using `\foreach` or explicit `\input`
4. **Writes** to `main.tex` (or your specified output)

## Benefits

✅ No manual file creation  
✅ No typos or missing packages  
✅ Subject-specific packages automatically included  
✅ Easy to regenerate when adding problems  
✅ Consistent structure every time  

## Help

```bash
vbagent compile --help
```

## That's It!

Your workflow is now:
```bash
vbagent process -i images/Problem_1.png --from 1 --to 25
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
pdflatex main.tex
```

Simple and automated! 🎉
