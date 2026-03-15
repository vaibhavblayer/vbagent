"""Common components for physics solution generation prompts.

Shared guidelines, formatting rules, and templates used across
all physics question types for solution generation.
"""

# LaTeX formatting rules for physics solutions (matches format_checker standards)
LATEX_FORMATTING_RULES = r"""
## LaTeX Formatting Rules (CRITICAL - Follow Exactly)

### Solution Structure
- Use \begin{solution}...\end{solution} environment
- Use align* environment DIRECTLY inside solution
- Use \intertext{} for brief text between equation lines
- Multiple align* blocks ONLY when diagram/table interrupts flow
- NO blank lines inside align*
- Keep solution CONCISE - show key steps, omit trivial algebra
- Do NOT use \boxed{} for final answers - just plain result

### Align* Rules (CRITICAL)
- Align equations at = using &
- End lines with \\
- Keep ONE step per line
- Variable repetition rule:
  * First line: variable &= expression
  * Intermediate lines: &= expression (no variable)
  * Last line: can have variable for final answer
  
Example:
```latex
t &= \frac{1}{\sqrt{g}} \int_{0}^{l} x^{-1/2} \, dx \\
  &= \frac{1}{\sqrt{g}} \left[ 2\sqrt{x} \right]_{0}^{l} \\
  &= 2\sqrt{\frac{l}{g}} \\
  &= 2\sqrt{\frac{2.45}{9.8}} \\
  &= 1.0 \ \mathrm{s}
```

### Math Mode
- Use $ ... $ for ALL inline math (variables, numbers with units, equations)
- Math within \intertext{} must use $ ... $
- NO \text{...} inside \intertext{} - use plain prose and wrap only math in $...$

### Physics Notation
- Vectors: \vec{v}, unit vectors: \hat{i}, \hat{j}, \hat{k}
- Fractions: \frac{a}{b} - NEVER \tfrac
- Parentheses: \left( ... \right), \left[ ... \right], \left| ... \right|
- NO \bigl, \bigr, \Bigl, \Bigr sizing commands
- Units: \mathrm{} for units: 10 \ \mathrm{m/s}, 5 \ \mathrm{kg}
- Spacing: spaces around = in equations

### Diagram Placement
- Place diagrams in \begin{center}...\end{center} between align* blocks
- Use \begin{tikzpicture}...\end{tikzpicture} for TikZ diagrams
- Diagrams interrupt the flow, requiring separate align* blocks before and after
"""

# Guidelines for identifying diagram needs with RICH context
DIAGRAM_IDENTIFICATION = """
## Diagram Requirements with Rich Context (CRITICAL)

When you need a diagram in the solution, provide RICH context using this format:

```
% DIAGRAM_REQUIREMENT: {
%   "id": "diagram_id",
%   "type": "fbd|circuit|graph|optics|organic_structure|...",
%   "description": "Brief description of what to show",
%   "context": "Detailed explanation of what the diagram represents",
%   "values": {"var1": "value1", "var2": "value2"},
%   "labels": ["label1", "label2", "label3"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: diagram_id
\end{tikzpicture}
\end{center}
```

### Example: Free Body Diagram
```latex
% DIAGRAM_REQUIREMENT: {
%   "id": "fbd_1",
%   "type": "fbd",
%   "description": "Free body diagram of block on incline",
%   "context": "Block of mass 2 kg on 30° incline. Forces: weight mg=19.6N vertically downward, normal force N perpendicular to incline surface, friction f parallel to incline pointing up. Block accelerates down the incline with a=4.9 m/s^2",
%   "values": {"m": "2 kg", "theta": "30°", "mg": "19.6 N", "a": "4.9 m/s^2"},
%   "labels": ["mg", "N", "f", "a", "\\theta"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: fbd_1
\end{tikzpicture}
\end{center}
```

### Example: Circuit Diagram
```latex
% DIAGRAM_REQUIREMENT: {
%   "id": "circuit_1",
%   "type": "circuit",
%   "description": "Series circuit with two resistors",
%   "context": "Two resistors R1=10Ω and R2=20Ω connected in series with a 12V battery. Total resistance is 30Ω. Current I=0.4A flows clockwise through the circuit",
%   "values": {"R1": "10 \\Omega", "R2": "20 \\Omega", "V": "12 V", "I": "0.4 A"},
%   "labels": ["R_1", "R_2", "V", "I"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: circuit_1
\end{tikzpicture}
\end{center}
```

### Example: Graph
```latex
% DIAGRAM_REQUIREMENT: {
%   "id": "graph_1",
%   "type": "graph",
%   "description": "Velocity vs time graph",
%   "context": "Graph showing velocity increasing linearly from 0 to 10 m/s over 5 seconds, representing constant acceleration of 2 m/s^2. Straight line passing through origin with positive slope",
%   "values": {"v_initial": "0 m/s", "v_final": "10 m/s", "t": "5 s", "a": "2 m/s^2"},
%   "labels": ["v (m/s)", "t (s)"]
% }

\begin{center}
\begin{tikzpicture}
% PLACEHOLDER: graph_1
\end{tikzpicture}
\end{center}
```

### Why Rich Context Matters

The diagram agent will receive:
1. **Original image** - Visual reference of the problem setup
2. **Your rich context** - Exactly what forces/components/features to show
3. **Values** - Specific numbers to label
4. **Labels** - Which symbols to use

This ensures the diagram accurately represents your solution reasoning.

### Diagram Types by Subject

**Physics:**
- `fbd` - Free body diagrams (forces, mechanics)
- `circuit` - Circuit diagrams (resistors, capacitors, etc.)
- `graph` - Graphs and plots (v-t, x-t, F-x, etc.)
- `optics` - Ray diagrams (lenses, mirrors, refraction)

**Chemistry:**
- `organic_structure` - Molecular structures (chemfig)
- `reaction_mechanism` - Reaction mechanisms with arrows
- `orbital` - Orbital diagrams, electron configurations
- `energy_diagram` - Energy profiles, reaction coordinates
- `chemical_equation` - Chemical equations (mhchem)

**Mathematics:**
- `function_graph` - Function plots, calculus
- `coordinate_geometry` - Lines, circles, conics
- `geometric_figure` - Triangles, polygons
- `number_line` - Number lines, inequalities
- `venn_diagram` - Venn diagrams, set theory
"""

# Solution quality guidelines
SOLUTION_QUALITY = """
## Solution Quality Guidelines

### Clarity
- Start with given information
- State assumptions clearly
- Explain each step before showing calculation
- Connect steps logically

### Rigor
- Use proper physics principles and laws
- Show dimensional analysis when helpful
- Verify answer makes physical sense
- Check limiting cases if applicable

### Completeness
- Address all parts of the question
- Show all significant steps
- Include units in final answer
- State answer clearly

### Pedagogy
- Explain WHY, not just HOW
- Highlight key concepts
- Point out common mistakes to avoid
- Provide physical intuition where possible
"""

# Common physics packages needed
PHYSICS_PACKAGES = r"""
% Common packages for physics solutions
\usepackage{amsmath}      % align*, equation*
\usepackage{siunitx}      % \si{}, \unit{}
\usepackage{tikz}         % diagrams
\usepackage{circuitikz}   % circuit diagrams
\usepackage{pgfplots}     % graphs
"""

# Template for solution with diagram
SOLUTION_WITH_DIAGRAM_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Initial reasoning about the setup}
\sum F &= ma \\
T - mg &= ma
\end{align*}

\begin{center}
\begin{tikzpicture}
% TikZ diagram code here
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{Continue from diagram}
a &= \frac{T - mg}{m} \\
  &= \frac{10 - 2 \times 9.8}{2} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
"""

# Template for simple solution (no diagram)
SOLUTION_SIMPLE_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Brief reasoning about the setup}
F &= ma \\
a &= \frac{F}{m} \\
  &= \frac{10}{2} \\
  &= 5 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
"""

# Template for MCQ solution
SOLUTION_MCQ_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Brief analysis of the problem}
E &= \frac{kQ}{r^2} \\
  &= \frac{9 \times 10^9 \times 2 \times 10^{-6}}{(0.1)^2} \\
  &= 1.8 \times 10^6 \ \mathrm{N/C}
\end{align*}

Therefore, the correct option is (c).
\end{solution}
"""

__all__ = [
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_IDENTIFICATION",
    "SOLUTION_QUALITY",
    "PHYSICS_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
    "SOLUTION_SIMPLE_TEMPLATE",
    "SOLUTION_MCQ_TEMPLATE",
]
