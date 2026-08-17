"""Common components for biology solution generation prompts."""

from ...mcq_format import MCQ_ANSWER_FORMAT_RULES

# LaTeX formatting rules for biology solutions
LATEX_FORMATTING_RULES = """
## LaTeX Formatting Standards for Biology

### Solution Environment Structure
- Use \\begin{solution}...\\end{solution} for all solutions
- Place align* directly inside solution
- Use \\intertext{} for explanations within align*

### Align Environment Rules (CRITICAL)

**1. One step per line**
**2. Variable repetition rule:** First line has variable, subsequent lines use &= only
**3. NO blank lines** inside align*
**4. Use \\intertext{}** for text between steps

```latex
% GOOD:
\\begin{align*}
\\intertext{Cardiac output is the product of heart rate and stroke volume.}
\\text{Cardiac output} &= \\text{Heart rate} \\times \\text{Stroke volume} \\\\
                       &= 72 \\times 70 \\\\
                       &= 5040 \\ \\text{mL/min}
\\end{align*}
```

### Biology-Specific Notation
- Scientific names in italics: \\textit{Homo sapiens}, \\textit{E. coli}
- Key terms in bold: \\textbf{mitosis}, \\textbf{photosynthesis}
- Biological molecules: \\ce{ATP}, \\ce{NADH}, \\ce{CO2}, \\ce{O2}
- Temperature: $37\\,^\\circ\\text{C}$
- Enzyme reactions: $A \\xrightarrow{\\text{enzyme}} B$

### Diagram Decision (IMPORTANT)
- Before finalizing, decide whether a visual would materially simplify the
  reader's understanding of a cell structure, pathway, life cycle, flowchart,
  graph, or other biological relationship.
- When a diagram would clarify the reasoning, include one even if the original
  problem image has no diagram. Prefer a concise, explanatory diagram over
  adding decorative artwork.
- For a simple diagram, write the TikZ directly in `solution_latex`. For a
  complex diagram, use `diagram_requirements` so the specialist can generate
  it.
- Every non-empty item in `diagram_requirements` MUST have the exact matching
  marker `% DIAGRAM PLACEHOLDER: <diagram_id>` in `solution_latex`, at the
  intended location. Use the same `diagram_id` in both places.
- Never request a diagram without its marker. A requirement without a marker
  cannot be positioned reliably in the finished solution.

### Alternate Solution Decision
- Decide whether a genuinely different and useful solution method would help
  the learner. Set `alternate_solution_recommended` to `true` only when it
  would add meaningful pedagogical value; use `false` for routine, direct, or
  one-method problems.
- When it is `true`, set `alternate_solution_hint` to one concise instruction
  naming the preferred alternate method. Do not write the alternate solution
  itself.
- When it is `false`, set `alternate_solution_hint` to `null`.

### MCQ Solutions
Must end with the actual lowercase option letter, for example: "Therefore, the correct option is (a)."

**Example: Conceptual MCQ**
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Identify the key concept: meiosis produces haploid cells.}
\\intertext{Option (a): Incorrect — mitosis produces diploid cells.}
\\intertext{Option (b): Correct — meiosis I separates homologous chromosomes.}
\\intertext{Option (c): Incorrect — DNA replication occurs in S phase, not M phase.}
\\intertext{Option (d): Incorrect — crossing over occurs in prophase I, not metaphase I.}
\\end{align*}

Therefore, the correct option is (b).
\\end{solution}
```

**Example: Calculation MCQ**
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Apply the Hardy-Weinberg equation: $p^2 + 2pq + q^2 = 1$}
q^2 &= 0.09 \\\\
q   &= 0.3 \\\\
p   &= 1 - q = 0.7
\\intertext{Frequency of heterozygotes:}
2pq &= 2 \\times 0.7 \\times 0.3 \\\\
    &= 0.42
\\end{align*}

Therefore, the correct option is (c).
\\end{solution}
```

### Solution Quality
- Explain the biology, not just the answer
- Address each option briefly for MCQs
- Use correct biological terminology
- Show calculations where applicable
"""

LATEX_FORMATTING_RULES += MCQ_ANSWER_FORMAT_RULES

SOLUTION_QUALITY = """
## Solution Quality Standards

### Completeness
- Explain the biological concept being tested
- Address why each option is correct or incorrect
- Use proper biological terminology
- Show calculations where applicable

### Clarity
- Use \\intertext{} for explanations
- One step per line for calculations
- Consistent notation throughout
"""

BIOLOGY_PACKAGES = """
## Required LaTeX Packages

The following packages are available:
- tikz: Diagrams (cell structures, flowcharts, life cycles)
- mhchem: Biological molecules (\\ce{ATP}, \\ce{CO2})
- pgfplots: Graphs and charts
"""

SOLUTION_WITH_DIAGRAM_TEMPLATE = """
\\begin{solution}
\\begin{align*}
\\intertext{Initial analysis}
% ... steps ...
\\end{align*}

\\begin{center}
\\begin{tikzpicture}
% Diagram code here (cell structure, flowchart, etc.)
\\end{tikzpicture}
\\end{center}

\\begin{align*}
\\intertext{Continue solution}
% ... more steps ...
\\end{align*}
\\end{solution}
"""

__all__ = [
    "LATEX_FORMATTING_RULES",
    "SOLUTION_QUALITY",
    "BIOLOGY_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
]
