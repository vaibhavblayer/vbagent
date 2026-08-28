"""Common components for mathematics solution generation prompts."""

from vbagent.prompts.latex_style import solution_style_rules

from ...mcq_format import MCQ_ANSWER_FORMAT_RULES

# LaTeX formatting rules for mathematics solutions
LATEX_FORMATTING_RULES = """
## LaTeX Formatting Standards (CRITICAL - Follow Exactly)

### Solution Environment Structure
- Use \\begin{solution}...\\end{solution} for all solutions
- Place align* directly inside solution (no other environments between)
- Use \\intertext{} for explanations within align*
- Multiple align* blocks ONLY when diagram/table interrupts flow
- NO blank lines inside align*
- Keep solution CONCISE - show key steps, omit trivial algebra
- Do NOT use \\boxed{} for final answers - just plain result

### Align Environment Rules (CRITICAL)

**1. One step per line** - show one meaningful mathematical step; omit routine intermediate arithmetic
```latex
% GOOD:
\\begin{align*}
c &= \\sqrt{a^2 + b^2} \\\\
  &= \\sqrt{13}
\\end{align*}

% BAD:
\\begin{align*}
c &= \\sqrt{a^2 + b^2} = \\sqrt{2^2 + 3^2} = \\sqrt{13}
\\end{align*}
```

**2. Variable repetition rule (CRITICAL):**
- First line: variable = expression
- Intermediate lines: &= expression (NO variable)
- Last line: can have variable for final answer

```latex
% GOOD:
\\begin{align*}
f(x) &= x^2 + 2x + 1 \\\\
     &= (x + 1)^2
\\end{align*}

% BAD (repetitive):
\\begin{align*}
f(x) &= x^2 + 2x + 1 \\\\
f(x) &= (x + 1)^2 \\\\
f(x) &= (x + 1)(x + 1)
\\end{align*}
```

**3. NO blank lines** inside align*

**4. Use \\intertext{}** for text between steps
- Math within \\intertext{} uses $...$
- NO \\text{...} inside \\intertext{}

```latex
\\begin{align*}
\\intertext{The triangle is right-angled, so use Pythagoras' theorem with legs $a=2$ and $b=3$.}
c &= \\sqrt{a^2 + b^2} \\\\
  &= \\sqrt{13}
\\end{align*}
```

**5. Alignment at equals sign** using &

### Diagram Decision (IMPORTANT)
- Before finalizing, decide whether a visual would materially simplify the
  reader's understanding of a graph, interval, geometric construction,
  coordinate relationship, or other spatial relationship.
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

### Mathematical Notation
- Fractions: Use `\\dfrac{a}{b}` everywhere, including inline math.
- Parentheses: \\left( ... \\right), \\left[ ... \\right], \\left| ... \\right|
- NO \\bigl, \\bigr, \\Bigl, \\Bigr sizing commands
- Trigonometric functions: \\sin, \\cos, \\tan (with backslash)
- Logarithms: \\log, \\ln
- Limits: \\lim_{x \\to a}
- Integrals: \\int_{a}^{b}
- Summations: \\sum_{i=1}^{n}

### Inline TikZ in Solutions (Encouraged)

For SIMPLE diagrams, write the TikZ code directly in the solution instead of
using DIAGRAM_REQUIREMENT placeholders. This produces better, more contextual results.

**Write TikZ directly when:**
- Simple function sketches (parabola, line, basic curve)
- Number lines for inequalities or intervals
- Quick geometric figures (triangle with labels, circle with tangent)
- Simple coordinate geometry (point, line, distance)
- Venn diagrams with 2 sets

**Use DIAGRAM_REQUIREMENT placeholder when:**
- Complex function graphs needing pgfplots (multiple curves, shading, legends)
- Detailed geometric constructions with many elements
- 3D geometry projections

**Example: Simple parabola sketch inline**
```latex
\\begin{center}
\\begin{tikzpicture}
\\draw[thin, ->] (-2,0) -- (2,0) node[right] {$x$};
\\draw[thin, ->] (0,-0.5) -- (0,3) node[above] {$y$};
\\draw[thick, domain=-1.5:1.5, samples=40] plot (\\x, {\\x*\\x});
\\fill (0,0) circle (2pt) node[below left, font=\\tiny] {$O$};
\\fill (1,1) circle (2pt) node[right, font=\\tiny] {$(1,1)$};
\\end{tikzpicture}
\\end{center}
```

**Example: Number line for inequality inline**
```latex
\\begin{center}
\\begin{tikzpicture}
\\draw[<->] (-3,0) -- (3,0);
\\foreach \\x in {-2,-1,0,1,2}
    \\draw (\\x,0.1) -- (\\x,-0.1) node[below, font=\\tiny] {$\\x$};
\\draw (1,0) circle (2pt);
\\draw[->] (1,0) -- (2.8,0);
\\node[below, font=\\footnotesize] at (0,-0.5) {$x > 1$};
\\end{tikzpicture}
\\end{center}
```

**TikZ style rules for inline diagrams:**
- NO colors — use solid/dashed/dotted line styles
- NO inline `>=latex` or `\\tikzset` — already set globally
- Use `thin, ->` for axes, `thick` for main curves
- Use `font=\\tiny` or `font=\\footnotesize` for labels
- Wrap in `\\begin{center}...\\end{center}`

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

```latex
\\begin{solution}
\\begin{align*}
\\intertext{Brief analysis}
% ... steps ...
\\end{align*}

Therefore, the correct option is (b).
\\end{solution}
```

### Solution Quality
- Show every logically necessary step; omit routine algebra and arithmetic
- Keep solutions CONCISE - key steps only
- One meaningful step per line
- Explain the reasoning, not just the calculation
"""

LATEX_FORMATTING_RULES += MCQ_ANSWER_FORMAT_RULES + solution_style_rules("mathematics")

# Diagram identification guidelines
DIAGRAM_IDENTIFICATION = """
## Diagram Identification

Identify when diagrams would enhance understanding:

### Common Mathematics Diagrams
- **number_line**: Inequalities, intervals, absolute values
- **function_graph**: Function plots, intersections, transformations
- **geometry**: Triangles, circles, polygons, constructions
- **venn_diagram**: Set operations, logic
- **coordinate_plane**: Points, lines, regions
- **tree_diagram**: Probability, combinatorics

### When to Include Diagrams
- Geometric problems → geometry diagram
- Inequalities → number line
- Functions → function graph
- Sets → Venn diagram
- Probability → tree diagram
- Coordinate geometry → coordinate plane

### When NOT to Include
- Pure algebraic manipulations
- Simple numerical calculations
- Abstract proofs without geometric content
"""

# Solution quality guidelines
SOLUTION_QUALITY = """
## Solution Quality Standards

### Completeness
- Show every logically necessary step; omit routine algebra and arithmetic
- Explain the reasoning, not just the calculation
- State assumptions explicitly
- Define notation used

### Clarity
- Use \\intertext{} for explanations
- One meaningful step per line
- Consistent notation throughout
- Clear logical flow

### Correctness
- Verify answer makes sense
- Check domain/range restrictions
- Verify units/dimensions if applicable
- Test edge cases when relevant
"""

# Mathematics packages (for reference)
MATHEMATICS_PACKAGES = """
## Required LaTeX Packages

The following packages are available:
- amsmath, amssymb: Mathematical symbols and environments
- tikz: Diagrams and graphics
- pgfplots: Function plots and graphs
"""

# Template for solution with diagram
SOLUTION_WITH_DIAGRAM_TEMPLATE = """
\\begin{solution}
\\begin{align*}
\\intertext{Initial analysis and setup}
% ... mathematical steps ...
\\end{align*}

\\begin{center}
\\begin{tikzpicture}
% Diagram code here
\\end{tikzpicture}
\\end{center}

\\begin{align*}
\\intertext{Continue solution using diagram}
% ... more steps ...
\\end{align*}
\\end{solution}
"""

# Template for simple solution
SOLUTION_SIMPLE_TEMPLATE = """
\\begin{solution}
\\begin{align*}
\\intertext{Problem analysis}
% ... mathematical steps ...
\\end{align*}
\\end{solution}
"""

__all__ = [
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_IDENTIFICATION",
    "SOLUTION_QUALITY",
    "MATHEMATICS_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
    "SOLUTION_SIMPLE_TEMPLATE",
]
