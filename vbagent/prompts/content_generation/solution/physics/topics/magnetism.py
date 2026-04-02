"""Magnetism solution generation for physics.

Covers: Magnetic fields, Lorentz force, Biot-Savart law, Ampere's law, magnetic materials.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Magnetism

### Magnetic Force
- Lorentz force: $\\vec{F} = q(\\vec{E} + \\vec{v} \\times \\vec{B})$
- Magnetic force: $\\vec{F} = q\\vec{v} \\times \\vec{B}$, magnitude $F = qvB\\sin\\theta$
- Force on current: $\\vec{F} = I\\vec{L} \\times \\vec{B}$, magnitude $F = ILB\\sin\\theta$
- Direction: right-hand rule
- Work done by magnetic force: zero (force perpendicular to velocity)

### Circular Motion in Magnetic Field
- Radius: $r = \\frac{mv}{qB}$
- Period: $T = \\frac{2\\pi m}{qB}$
- Frequency: $f = \\frac{qB}{2\\pi m}$ (cyclotron frequency)
- Kinetic energy unchanged (magnetic force does no work)

### Biot-Savart Law
- $d\\vec{B} = \\frac{\\mu_0}{4\\pi}\\frac{Id\\vec{l} \\times \\hat{r}}{r^2}$
- Straight wire: $B = \\frac{\\mu_0 I}{2\\pi r}$
- Circular loop (center): $B = \\frac{\\mu_0 I}{2R}$
- Circular loop (axis): $B = \\frac{\\mu_0 IR^2}{2(R^2 + x^2)^{3/2}}$
- Solenoid: $B = \\mu_0 nI$ where $n$ is turns per unit length

### Ampere's Law
- $\\oint \\vec{B} \\cdot d\\vec{l} = \\mu_0 I_{enc}$
- For straight wire: $B \\cdot 2\\pi r = \\mu_0 I$
- For solenoid: $B \\cdot L = \\mu_0 nLI$
- For toroid: $B \\cdot 2\\pi r = \\mu_0 NI$

### Magnetic Dipole
- Torque: $\\vec{\\tau} = \\vec{\\mu} \\times \\vec{B}$, magnitude $\\tau = \\mu B\\sin\\theta$
- Magnetic moment: $\\mu = IA$ (current loop)
- Potential energy: $U = -\\vec{\\mu} \\cdot \\vec{B} = -\\mu B\\cos\\theta$

### Force Between Parallel Wires
- Force per unit length: $\\frac{F}{L} = \\frac{\\mu_0 I_1 I_2}{2\\pi d}$
- Parallel currents: attract
- Antiparallel currents: repel

### Problem-Solving Strategy
1. Identify magnetic field source (wire, loop, solenoid)
2. Calculate field using Biot-Savart or Ampere's law
3. For force: use $\\vec{F} = q\\vec{v} \\times \\vec{B}$ or $\\vec{F} = I\\vec{L} \\times \\vec{B}$
4. Apply right-hand rule for direction
5. For circular motion: use $r = mv/(qB)$
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Charged particle in magnetic field
1. Identify $q$, $v$, $B$, and angle between $\\vec{v}$ and $\\vec{B}$
2. Calculate force: $F = qvB\\sin\\theta$
3. If perpendicular: circular motion with $r = mv/(qB)$
4. Calculate radius, period, or frequency

### Pattern 2: Magnetic field from current
1. Identify geometry (straight wire, loop, solenoid)
2. Use appropriate formula:
   - Straight wire: $B = \\mu_0 I/(2\\pi r)$
   - Loop center: $B = \\mu_0 I/(2R)$
   - Solenoid: $B = \\mu_0 nI$
3. Apply superposition if multiple sources

### Pattern 3: Force on current-carrying wire
1. Identify current $I$, length $L$, and field $B$
2. Calculate force: $F = ILB\\sin\\theta$
3. Use right-hand rule for direction
4. For curved wire: integrate $d\\vec{F} = Id\\vec{l} \\times \\vec{B}$

### Pattern 4: Torque on current loop
1. Calculate magnetic moment: $\\mu = NIA$
2. Find angle between $\\vec{\\mu}$ and $\\vec{B}$
3. Torque: $\\tau = \\mu B\\sin\\theta$
4. Maximum torque when $\\theta = 90°$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GENERIC diagram for:
- Magnetic field lines
- Particle trajectories in magnetic fields
- Current-carrying wires and loops
- Force directions (right-hand rule)
- **Place in problem context**

### Use GRAPH for:
- Magnetic field vs distance plots
- Trajectory plots
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For a charged particle moving perpendicular to a magnetic field:}
F &= qvB \\\\
  &= 1.6 \\times 10^{-19} \\times 10^6 \\times 0.5 \\\\
  &= 8.0 \\times 10^{-14} \\ \\mathrm{N}
\\end{align*}

\\begin{align*}
\\intertext{The radius of circular motion is:}
r &= \\frac{mv}{qB} \\\\
  &= \\frac{9.1 \\times 10^{-31} \\times 10^6}{1.6 \\times 10^{-19} \\times 0.5} \\\\
  &= 1.14 \\times 10^{-5} \\ \\mathrm{m} \\\\
  &= 11.4 \\ \\mu\\mathrm{m}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Right-hand rule errors**
   - For $\\vec{F} = q\\vec{v} \\times \\vec{B}$: fingers along $\\vec{v}$, curl toward $\\vec{B}$, thumb is $\\vec{F}$
   - For negative charge: force opposite to right-hand rule
   - For current: use direction of positive charge flow

2. **Magnetic force does no work**
   - Force always perpendicular to velocity
   - Kinetic energy unchanged
   - Only changes direction, not speed

3. **Circular motion formulas**
   - Radius: $r = mv/(qB)$ (not $qB/(mv)$)
   - Period: $T = 2\\pi m/(qB)$ (independent of $v$ and $r$!)
   - Don't confuse with electric field formulas

4. **Biot-Savart vs Ampere's law**
   - Biot-Savart: works for any geometry, but complex
   - Ampere's law: only for high symmetry, but simple
   - Use Ampere's law when possible

5. **Solenoid field**
   - Inside: $B = \\mu_0 nI$ (uniform)
   - Outside: $B \\approx 0$
   - $n$ is turns per unit length, not total turns

6. **Force between wires**
   - Parallel currents: attract
   - Antiparallel currents: repel
   - Opposite of what intuition might suggest!
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving magnetism problems (magnetic fields, Lorentz force, Biot-Savart, Ampere's law).

""" + TOPIC_CONCEPTS + """

""" + COMMON_PATTERNS + """

""" + DIAGRAM_GUIDANCE + """

""" + TYPICAL_MISTAKES + """

""" + LATEX_FORMATTING_RULES + """

""" + SOLUTION_QUALITY + """

## Output Format

Return a JSON object with:
- `solution`: Complete solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams needed
- `answer_type`: "subjective" or "integer"
- `answer_value`: Final numerical answer if integer type, null otherwise
"""

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving magnetism MCQ problems.

""" + TOPIC_CONCEPTS + """

""" + COMMON_PATTERNS + """

""" + DIAGRAM_GUIDANCE + """

""" + TYPICAL_MISTAKES + """

""" + LATEX_FORMATTING_RULES + """

## MCQ-Specific Guidelines

- Show key steps that lead to answer
- Eliminate obviously wrong options when helpful
- Verify answer matches one of the given options
- Keep solution concise but complete

## Output Format

Return a JSON object with:
- `solution`: Solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Correct option letter (e.g., "A", "B", "C", "D")
"""

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving magnetism MCQ (multiple correct) problems.

""" + TOPIC_CONCEPTS + """

""" + COMMON_PATTERNS + """

""" + DIAGRAM_GUIDANCE + """

""" + TYPICAL_MISTAKES + """

""" + LATEX_FORMATTING_RULES + """

## MCQ-MC Specific Guidelines

- Check each option independently
- Show reasoning for why each is correct/incorrect
- Multiple options can be correct

## Output Format

Return a JSON object with:
- `solution`: Solution in LaTeX
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Comma-separated correct options (e.g., "A,C" or "B,D")
"""


def get_prompt(question_type: str) -> str:
    """Get magnetism prompt for question type."""
    if question_type in ["subjective", "integer"]:
        return SYSTEM_PROMPT_SUBJECTIVE
    elif question_type == "mcq_sc":
        return SYSTEM_PROMPT_MCQ_SC
    elif question_type == "mcq_mc":
        return SYSTEM_PROMPT_MCQ_MC
    else:
        return SYSTEM_PROMPT_SUBJECTIVE


__all__ = [
    "SYSTEM_PROMPT_SUBJECTIVE",
    "SYSTEM_PROMPT_MCQ_SC",
    "SYSTEM_PROMPT_MCQ_MC",
    "get_prompt",
]
