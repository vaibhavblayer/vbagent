"""Common components for chemistry solution generation prompts."""

# LaTeX formatting rules for chemistry solutions
LATEX_FORMATTING_RULES = """
## LaTeX Formatting Standards

### Solution Environment
- Use \\begin{solution}...\\end{solution} for all solutions
- Place align* directly inside solution (no other environments between)
- Use \\intertext{} for explanations within align*

### Chemical Notation
- Use \\ce{} for chemical formulas: \\ce{H2O}, \\ce{CH3COOH}
- Use \\ce{->} for reactions: \\ce{A + B -> C}
- Use proper subscripts and superscripts
- Use \\Delta for heat, \\rightleftharpoons for equilibrium

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
\\intertext{Calculate moles of \\ce{NaCl}}
n &= \\frac{m}{M} \\\\
  &= \\frac{5.85}{58.5} \\\\
  &= 0.1 \\ \\text{mol}
\\end{align*}
\\end{solution}
```
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
