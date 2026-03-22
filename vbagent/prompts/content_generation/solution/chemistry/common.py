"""Common components for chemistry solution generation prompts."""

# LaTeX formatting rules for chemistry solutions
LATEX_FORMATTING_RULES = """
## LaTeX Formatting Standards

### Solution Environment Structure
- Use \\begin{solution}...\\end{solution} for all solutions
- Place align* directly inside solution (no other environments between)
- Use \\intertext{} for explanations within align*
- Multiple align* blocks ONLY when diagram/table interrupts flow

### Align Environment Rules (CRITICAL)

**1. One step per line** - don't combine multiple operations
```latex
% GOOD:
\\begin{align*}
n &= \\frac{m}{M} \\\\
  &= \\frac{5.85}{58.5} \\\\
  &= 0.1 \\ \\text{mol}
\\end{align*}

% BAD:
\\begin{align*}
n &= \\frac{m}{M} = \\frac{5.85}{58.5} = 0.1 \\ \\text{mol}
\\end{align*}
```

**2. Variable repetition rule (CRITICAL):**
- First line: variable = expression
- Intermediate lines: &= expression (NO variable)
- Last line: can have variable for final answer

```latex
% GOOD:
\\begin{align*}
K_{\\text{eq}} &= \\frac{[\\ce{C}][\\ce{D}]}{[\\ce{A}][\\ce{B}]} \\\\
              &= \\frac{(0.5)(0.5)}{(0.2)(0.3)} \\\\
              &= 4.17
\\end{align*}

% BAD (repetitive):
\\begin{align*}
K_{\\text{eq}} &= \\frac{[\\ce{C}][\\ce{D}]}{[\\ce{A}][\\ce{B}]} \\\\
K_{\\text{eq}} &= \\frac{(0.5)(0.5)}{(0.2)(0.3)} \\\\
K_{\\text{eq}} &= 4.17
\\end{align*}
```

**3. NO blank lines** inside align*

**4. Use \\intertext{}** for text between steps
- Math within \\intertext{} uses $...$
- NO \\text{...} inside \\intertext{}

```latex
\\begin{align*}
\\intertext{Calculate moles of \\ce{NaCl}}
n &= \\frac{m}{M} \\\\
  &= \\frac{5.85}{58.5} \\\\
  &= 0.1 \\ \\text{mol}
\\intertext{Now find concentration using $V = 100$ mL}
C &= \\frac{n}{V} \\\\
  &= \\frac{0.1}{0.1} \\\\
  &= 1.0 \\ \\text{M}
\\end{align*}
```

**5. Alignment at equals sign** using &

### Chemical Notation
- Use \\ce{} for chemical formulas: \\ce{H2O}, \\ce{CH3COOH}
- Use \\ce{->} for reactions: \\ce{A + B -> C}
- Use proper subscripts and superscripts
- Use \\Delta for heat, \\rightleftharpoons for equilibrium

### Inline TikZ in Solutions (Encouraged)

For SIMPLE diagrams, write the TikZ code directly in the solution instead of
using DIAGRAM_REQUIREMENT placeholders. This produces better, more contextual results.

**Write TikZ directly when:**
- Simple energy level diagrams (2-3 levels with arrows)
- Quick reaction coordinate sketches (activation energy, ΔH)
- Simple phase diagrams or P-V graphs
- Basic orbital filling diagrams

**Use DIAGRAM_REQUIREMENT placeholder when:**
- Complex organic structures (use chemfig specialist)
- Detailed reaction mechanisms with curved arrows
- Complex molecular orbital diagrams
- Multi-step synthesis schemes

**Example: Simple energy diagram inline**
```latex
\\begin{center}
\\begin{tikzpicture}
\\draw[thin, ->] (0,0) -- (0,3) node[above] {Energy};
\\draw[thin, ->] (0,0) -- (5,0) node[right] {Reaction coordinate};
\\draw[thick] (0.5,0.5) -- (1.5,0.5) node[left, font=\\tiny, pos=0] {reactants};
\\draw[thick] (3.5,1.5) -- (4.5,1.5) node[right, font=\\tiny] {products};
\\draw[thick, dashed] (1.5,0.5) .. controls (2.5,2.8) .. (3.5,1.5);
\\fill (2.5,2.5) circle (1.5pt);
\\node[above, font=\\tiny] at (2.5,2.5) {$E_a$};
\\draw[<->, thin] (4.7,0.5) -- (4.7,1.5) node[midway, right, font=\\tiny] {$\\Delta H$};
\\end{tikzpicture}
\\end{center}
```

**TikZ style rules for inline diagrams:**
- NO colors — use solid/dashed/dotted line styles
- NO inline `>=latex` or `\\tikzset` — already set globally
- Use `thin, ->` for axes, `thick` for main curves
- Use `font=\\tiny` or `font=\\footnotesize` for labels
- Wrap in `\\begin{center}...\\end{center}`

### MCQ Solutions
Must end with: "Therefore, the correct option is (X)."

```latex
\\begin{solution}
\\begin{align*}
\\intertext{Brief analysis}
% ... steps ...
\\end{align*}

Therefore, the correct option is (c).
\\end{solution}
```

### Solution Quality
- Show ALL steps, even "obvious" ones
- Keep solutions CONCISE - key steps only
- One operation per line
- NO \\boxed{} for final answers
- Explain the chemistry, not just the math
"""

# Diagram identification guidelines
DIAGRAM_IDENTIFICATION = """
## Diagram Identification

Identify when diagrams would enhance understanding:

### Common Chemistry Diagrams
- **organic_structure**: Organic molecules, functional groups, stereochemistry
- **chemical_equation**: Reaction mechanisms, electron flow
- **energy_diagram**: Reaction coordinate diagrams, potential energy
- **orbital**: Molecular orbitals, hybridization, bonding
- **apparatus**: Lab setup, experimental apparatus

### When to Include Diagrams
- Organic chemistry → organic_structure
- Reaction mechanisms → chemical_equation
- Thermodynamics/kinetics → energy_diagram
- Bonding/structure → orbital
- Experimental setup → apparatus

### When NOT to Include
- Simple stoichiometry calculations
- Pure numerical problems
- Conceptual questions without visual component
"""

# Solution quality guidelines
SOLUTION_QUALITY = """
## Solution Quality Standards

### Completeness
- Show ALL steps, even "obvious" ones
- Explain the chemistry, not just the math
- State assumptions explicitly
- Define notation used

### Clarity
- Use \\intertext{} for explanations
- One operation per line
- Consistent notation throughout
- Clear logical flow

### Correctness
- Balance chemical equations
- Check units and significant figures
- Verify answer makes chemical sense
- Consider limiting reagents, yields, etc.
"""

# Chemistry packages (for reference)
CHEMISTRY_PACKAGES = """
## Required LaTeX Packages

The following packages are available:
- chemfig: Organic structure drawing
- mhchem: Chemical equations and formulas (\\ce{})
- tikz: Diagrams and graphics
- siunitx: Units and numbers
"""

# Template for solution with diagram
SOLUTION_WITH_DIAGRAM_TEMPLATE = """
\\begin{solution}
\\begin{align*}
\\intertext{Initial analysis and setup}
% ... chemical/mathematical steps ...
\\end{align*}

\\begin{center}
\\begin{tikzpicture}
% Diagram code here (structure, mechanism, energy diagram)
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
% ... chemical/mathematical steps ...
\\end{align*}
\\end{solution}
"""

__all__ = [
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_IDENTIFICATION",
    "SOLUTION_QUALITY",
    "CHEMISTRY_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
    "SOLUTION_SIMPLE_TEMPLATE",
]
