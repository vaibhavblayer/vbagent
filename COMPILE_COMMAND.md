# Compile Command - Generate Main LaTeX File

## Overview

The `vbagent compile` command automatically generates a main LaTeX file that compiles all your processed problems with proper preamble, packages, and structure.

## Problem

Previously, you had to manually:
1. Create a main.tex file
2. Add all necessary packages
3. List all problem files to include
4. Update the list when adding/removing problems

## Solution

The `compile` command automates this entire process:

```bash
vbagent compile
```

This generates a `main.tex` file ready to compile all your processed problems.

## Basic Usage

### Generate main.tex for all problems

```bash
vbagent compile
```

This creates `main.tex` that includes all problems from `agentic/scans/`.

### Compile specific range

```bash
# Your example: problems 1-13, 16, 19, 22, 25
vbagent compile --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"

# Or use range for consecutive problems
vbagent compile --from 1 --to 13
```

### Custom title and subject

```bash
# Physics with custom title
vbagent compile -t "Wave Motion" -s physics

# Chemistry problems
vbagent compile -t "Organic Chemistry" -s chemistry

# Mathematics problems
vbagent compile -t "Calculus Problems" -s mathematics
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-d, --dir` | Scans directory | `agentic/scans` |
| `-o, --output` | Output file path | `main.tex` |
| `-t, --title` | Document title | `Problems` |
| `-s, --subject` | Subject (physics/chemistry/mathematics) | `physics` |
| `--from` | Start index (1-based) | All |
| `--to` | End index (1-based) | All |
| `--problems` | Comma-separated problem list | All |
| `--foreach/--explicit` | Use \\foreach loop or explicit \\input | `--foreach` |
| `-v, --verbose` | Verbose output | Off |

## Examples

### Your Exact Use Case

```bash
# Generate main.tex for Wave Motion with specific problems
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

This generates:

```latex
\documentclass{article}
\usepackage{tikz, tasks, geometry, xcolor}
\usetikzlibrary{arrows.meta, patterns, calc, intersections, quotes, angles}
\usepackage{amsmath, amssymb, amsfonts, mathtools}
\setlength{\columnsep}{10pt}
\setlength{\columnseprule}{0.4pt}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\geometry{a4paper, margin=1in}
\usepackage{tzplot, pgfplots, kinematikz}
\usepackage{circuitikz}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75}
\renewcommand{\frac}{\dfrac}
\newcommand{\ans}{\textcolor{blue!20!red}{\textit{\quad Ans.}}}
% \renewcommand{\ans}{}  % Uncomment to hide answers
\newenvironment{solution}{\par\noindent\color{red!95}\textbf{Solution: }\ignorespaces}{\par}
\newenvironment{alternatesolution}{\par\noindent\color{black!15!red!65!yellow}\textbf{Alternate Solution: }\ignorespaces}{\par}
\title{\textsc{Wave Motion}}
\begin{document}
\maketitle
\begin{enumerate}
\foreach \i in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 19, 22, 25} {
  \input{agentic/scans/problem_\i.tex}
}
\end{enumerate}
\end{document}
```

### Range-Based Selection

```bash
# Problems 1-20
vbagent compile --from 1 --to 20

# Problems 10 onwards
vbagent compile --from 10

# First 15 problems
vbagent compile --to 15
```

### Different Subjects

```bash
# Chemistry with chemfig and mhchem packages
vbagent compile -s chemistry -t "Organic Chemistry Reactions"

# Mathematics with pgfplots and tkz-euclide
vbagent compile -s mathematics -t "Calculus Problems"
```

### Custom Output Location

```bash
# Generate in different directory
vbagent compile -d output/scans -o output/main.tex

# Generate with custom name
vbagent compile -o wave_motion.tex
```

### Explicit Input Statements

```bash
# Use explicit \input statements instead of \foreach
vbagent compile --explicit
```

This generates:

```latex
\begin{enumerate}
\input{agentic/scans/problem_1.tex}
\input{agentic/scans/problem_2.tex}
\input{agentic/scans/problem_3.tex}
...
\end{enumerate}
```

## Subject-Specific Packages

### Physics (default)
- `circuitikz` - Circuit diagrams
- `kinematikz` - Kinematics diagrams
- `tzplot` - Function plotting
- `pgfplots` - Advanced plotting

### Chemistry
- `chemfig` - Chemical structures
- `mhchem` - Chemical equations
- `pgfplots` - Energy diagrams, graphs

### Mathematics
- `pgfplots` - Function graphs
- `tkz-euclide` - Geometric constructions
- `venndiagram` - Venn diagrams

## Workflow

### 1. Process Problems

```bash
vbagent process -i images/Problem_1.png --from 1 --to 25
```

This creates:
```
agentic/
├── scans/
│   ├── problem_1.tex
│   ├── problem_2.tex
│   ├── ...
│   └── problem_25.tex
├── classifications/
├── tikz/
└── ...
```

### 2. Generate Main File

```bash
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

This creates `main.tex` in the current directory.

### 3. Compile

```bash
pdflatex main.tex
# or
latexmk -pdf main.tex
```

## Advanced Usage

### Multiple Subjects

```bash
# Physics problems
vbagent compile -d agentic/scans/physics -o physics_main.tex -s physics -t "Physics Problems"

# Chemistry problems
vbagent compile -d agentic/scans/chemistry -o chemistry_main.tex -s chemistry -t "Chemistry Problems"

# Mathematics problems
vbagent compile -d agentic/scans/mathematics -o mathematics_main.tex -s mathematics -t "Math Problems"
```

### Verbose Mode

```bash
vbagent compile -v
```

Shows:
- Problem discovery
- Range/list being used
- Preview of generated content
- Compilation command

### Integration with Process

```bash
# Process and generate main file in one go
vbagent process -i images/Problem_1.png --from 1 --to 25
vbagent compile -t "Wave Motion" --from 1 --to 25
pdflatex main.tex
```

## Tips

### 1. Use --problems for Non-Consecutive Problems

```bash
# Skip some problems
vbagent compile --problems "1,3,5,7,9,11,13,16,19,22,25"
```

### 2. Use --from/--to for Consecutive Problems

```bash
# All problems 1-20
vbagent compile --from 1 --to 20
```

### 3. Regenerate After Adding Problems

```bash
# Add more problems
vbagent process -i images/Problem_26.png --from 26 --to 30

# Regenerate main.tex with new range
vbagent compile --from 1 --to 30
```

### 4. Different Titles for Different Sets

```bash
# Chapter 1
vbagent compile --from 1 --to 10 -t "Chapter 1: Mechanics" -o chapter1.tex

# Chapter 2
vbagent compile --from 11 --to 20 -t "Chapter 2: Waves" -o chapter2.tex
```

## Comparison

### Before (Manual)

```latex
% main.tex - manually created and maintained
\documentclass{article}
\usepackage{tikz, tasks, tzplot, pgfplots, geometry, xcolor, pgffor}
\usetikzlibrary{arrows.meta, patterns, calc, intersections, quotes, angles}
\usepackage{amsmath, amssymb, amsfonts, mathtools, kinematikz}
\setlength{\columnsep}{10pt}
\setlength{\columnseprule}{0.4pt}
\usepackage[upright]{fourier}
\usepackage{enumitem}
\usepackage{circuitikz}
\usepackage{tzplot}
\usepackage{numerica}
\ctikzset{resistors/scale=0.75,capacitors/scale=0.75,inductors/scale=0.75,}
\renewcommand{\frac}{\dfrac}
\geometry{a4paper, margin=1in}
\newcommand{\ans}{\textcolor{blue!20!red}{\textit{\quad Ans.}}}
% \renewcommand{\ans}{}
\newenvironment{solution}{\par\noindent\color{red!95}\textbf{Solution: }\ignorespaces}{\par}
\newenvironment{alternatesolution}{\par\noindent\color{black!15!red!65!yellow}\textbf{Solution: }\ignorespaces}{\par}
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

### After (Automated)

```bash
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
```

Done! The file is generated automatically with all the right packages.

## Benefits

✅ **Automatic**: No manual file creation  
✅ **Consistent**: Same structure every time  
✅ **Subject-Aware**: Right packages for each subject  
✅ **Flexible**: Range or explicit list  
✅ **Fast**: Regenerate in seconds  
✅ **Error-Free**: No typos or missing packages  

## See Also

- `vbagent process --help` - Process problems
- `vbagent batch --help` - Batch processing
- `vbagent check --help` - Quality checking

## Summary

The `compile` command eliminates manual main.tex file creation and maintenance. Just specify your title, subject, and which problems to include, and it generates a ready-to-compile LaTeX file with all the right packages and structure.

```bash
# Your workflow now:
vbagent process -i images/Problem_1.png --from 1 --to 25
vbagent compile -t "Wave Motion" --problems "1,2,3,4,5,6,7,8,9,10,11,12,13,16,19,22,25"
pdflatex main.tex
```

Simple, fast, and error-free!
