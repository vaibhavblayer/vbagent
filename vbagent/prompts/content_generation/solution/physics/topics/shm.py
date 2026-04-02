"""Simple Harmonic Motion (SHM) solution generation for physics.

Covers: Oscillations, springs, pendulums, SHM equations, energy in SHM.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Simple Harmonic Motion

### SHM Basics
- Restoring force: $F = -kx$ (Hooke's law)
- Equation of motion: $\\frac{d^2x}{dt^2} + \\omega^2 x = 0$
- General solution: $x(t) = A\\cos(\\omega t + \\phi)$ or $x(t) = A\\sin(\\omega t + \\phi)$
- Velocity: $v(t) = -A\\omega\\sin(\\omega t + \\phi)$
- Acceleration: $a(t) = -A\\omega^2\\cos(\\omega t + \\phi) = -\\omega^2 x$

### Key Parameters
- Amplitude: $A$ (maximum displacement)
- Angular frequency: $\\omega = \\sqrt{\\frac{k}{m}}$ (spring-mass), $\\omega = \\sqrt{\\frac{g}{L}}$ (simple pendulum)
- Period: $T = \\frac{2\\pi}{\\omega}$
- Frequency: $f = \\frac{1}{T} = \\frac{\\omega}{2\\pi}$
- Phase constant: $\\phi$ (determined by initial conditions)

### Energy in SHM
- Total energy: $E = \\frac{1}{2}kA^2$ (constant)
- Kinetic energy: $KE = \\frac{1}{2}mv^2 = \\frac{1}{2}m\\omega^2(A^2 - x^2)$
- Potential energy: $PE = \\frac{1}{2}kx^2$
- At equilibrium: $KE = E$, $PE = 0$
- At amplitude: $KE = 0$, $PE = E$

### Common SHM Systems
- Spring-mass (horizontal): $T = 2\\pi\\sqrt{\\frac{m}{k}}$
- Spring-mass (vertical): same period, equilibrium shifts by $\\frac{mg}{k}$
- Simple pendulum: $T = 2\\pi\\sqrt{\\frac{L}{g}}$ (small angles)
- Physical pendulum: $T = 2\\pi\\sqrt{\\frac{I}{mgd}}$
- Torsional pendulum: $T = 2\\pi\\sqrt{\\frac{I}{\\kappa}}$

### Problem-Solving Strategy
1. Identify equilibrium position
2. Write restoring force: $F = -kx$ or equivalent
3. Find $\\omega = \\sqrt{k/m}$ or use standard formula
4. Apply initial conditions to find $A$ and $\\phi$
5. Write complete solution $x(t)$
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Finding period/frequency
1. Identify system type (spring-mass, pendulum, etc.)
2. Use appropriate formula for $\\omega$ or $T$
3. For spring: $T = 2\\pi\\sqrt{m/k}$
4. For pendulum: $T = 2\\pi\\sqrt{L/g}$

### Pattern 2: Equation of motion from initial conditions
1. Write general form: $x(t) = A\\cos(\\omega t + \\phi)$
2. Apply $x(0)$ to find relation between $A$ and $\\phi$
3. Apply $v(0)$ to find another relation
4. Solve for $A$ and $\\phi$

### Pattern 3: Energy problems
1. Use conservation of energy: $E = \\frac{1}{2}kA^2$
2. At any position: $\\frac{1}{2}kx^2 + \\frac{1}{2}mv^2 = \\frac{1}{2}kA^2$
3. Use $v = \\omega\\sqrt{A^2 - x^2}$
4. Solve for unknown

### Pattern 4: Maximum velocity/acceleration
1. Maximum velocity at equilibrium: $v_{max} = A\\omega$
2. Maximum acceleration at amplitude: $a_{max} = A\\omega^2$
3. Use $\\omega = \\sqrt{k/m}$ or $\\omega = 2\\pi f$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use MECHANICS diagram for:
- Spring-mass system setup
- Pendulum configuration
- Forces at different positions
- **Place in problem context**

### Use GRAPH for:
- $x$ vs $t$ (displacement-time)
- $v$ vs $t$ (velocity-time)
- $a$ vs $t$ (acceleration-time)
- $KE$ and $PE$ vs $x$ or $t$
- Phase space ($v$ vs $x$)
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For a spring-mass system, the angular frequency is:}
\\omega &= \\sqrt{\\frac{k}{m}} \\\\
       &= \\sqrt{\\frac{100}{2}} \\\\
       &= 7.07 \\ \\mathrm{rad/s}
\\end{align*}

\\begin{align*}
\\intertext{The period is:}
T &= \\frac{2\\pi}{\\omega} \\\\
  &= \\frac{2\\pi}{7.07} \\\\
  &= 0.89 \\ \\mathrm{s}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Confusing amplitude with displacement**
   - Amplitude $A$ is maximum displacement
   - Displacement $x$ varies with time: $-A \\leq x \\leq A$

2. **Wrong formula for pendulum**
   - Simple pendulum: $T = 2\\pi\\sqrt{L/g}$ (small angles only)
   - NOT $T = 2\\pi\\sqrt{m/k}$
   - Length $L$ is to center of mass, not total length

3. **Forgetting initial conditions**
   - Phase constant $\\phi$ depends on initial position and velocity
   - $x(0) = A\\cos\\phi$, $v(0) = -A\\omega\\sin\\phi$
   - Don't assume $\\phi = 0$ unless stated

4. **Energy errors**
   - Total energy is constant: $E = \\frac{1}{2}kA^2$
   - At any point: $KE + PE = E$
   - Maximum KE occurs at equilibrium, not at amplitude

5. **Vertical spring confusion**
   - Period same as horizontal: $T = 2\\pi\\sqrt{m/k}$
   - Equilibrium shifts down by $\\Delta x = mg/k$
   - Measure displacement from new equilibrium

6. **Small angle approximation**
   - $\\sin\\theta \\approx \\theta$ only for small $\\theta$ (in radians)
   - Simple pendulum formula valid only for small amplitudes
   - For large angles, period increases
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving simple harmonic motion problems (oscillations, springs, pendulums, SHM equations, energy).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving SHM MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving SHM MCQ (multiple correct) problems.

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
    """Get SHM prompt for question type."""
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
