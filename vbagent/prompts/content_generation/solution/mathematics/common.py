"""Common components for mathematics solution generation prompts."""

# LaTeX formatting rules for mathematics solutions
LATEX_FORMATTING_RULES = """
## LaTeX Formatting Standards

### Solution Environment
- Use \\begin{solution}...\\end{solution} for all solutions
- Place align* directly inside solution (no other environments between)
- Use \\intertext{} for explanations within align*

### Mathematical Notation
- Use proper LaTeX commands: \\frac{}{}, \\sqrt{}, \\sin, \\cos, etc.
- Use \\text{} for text within math mode
- Use proper spacing: \\, for thin space, \\quad for larger space
- Use \\left and \\right for auto-sizing delimiters

### Align Environment Rules
1. **One step per line** - don't combine multiple operations
2. **Variable repetition rule**: 
   - First line: variable = expression
   - Subsequent lines: &= expression (no variable)
3. **NO blank lines** inside align*
4. **Use \\intertext{}** for text between steps
5. **Math in intertext** uses $...$

### Example
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Given: $a = 2$, $b = 3$. Find $c$}
c &= \\sqrt{a^2 + b^2} \\\\
  &= \\sqrt{2^2 + 3^2} \\\\
  &= \\sqrt{4 + 9} \\\\
  &= \\sqrt{13}
\\end{align*}
\\end{solution}
```
"""

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
- Show ALL steps, even "obvious" ones
- Explain the reasoning, not just the calculation
- State assumptions explicitly
- Define notation used

### Clarity
- Use \\intertext{} for explanations
- One operation per line
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
