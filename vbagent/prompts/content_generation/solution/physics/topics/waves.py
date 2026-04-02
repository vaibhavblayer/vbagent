"""Wave Mechanics solution generation for physics.

Covers: Wave motion, superposition, standing waves, Doppler effect, sound waves, wave properties.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Wave Mechanics

### Wave Basics
- Wave equation: $y(x,t) = A\\sin(kx - \\omega t + \\phi)$ or $y(x,t) = A\\cos(kx - \\omega t + \\phi)$
- Amplitude: $A$ (maximum displacement)
- Wave number: $k = \\frac{2\\pi}{\\lambda}$
- Angular frequency: $\\omega = 2\\pi f$
- Wave speed: $v = f\\lambda = \\frac{\\omega}{k}$
- Phase: $\\phi_0 = kx - \\omega t + \\phi$

### Wave Properties
- Wavelength: $\\lambda$ (distance between consecutive crests)
- Frequency: $f$ (oscillations per second)
- Period: $T = \\frac{1}{f}$
- Speed on string: $v = \\sqrt{\\frac{T}{\\mu}}$ where $T$ is tension, $\\mu$ is linear mass density
- Speed of sound: $v = \\sqrt{\\frac{\\gamma RT}{M}}$ or $v \\approx 343$ m/s in air at 20°C

### Superposition and Interference
- Principle of superposition: $y_{total} = y_1 + y_2 + ...$
- Constructive interference: waves in phase, amplitude adds
- Destructive interference: waves out of phase, amplitude cancels
- Path difference for constructive: $\\Delta x = n\\lambda$ ($n = 0, 1, 2, ...$)
- Path difference for destructive: $\\Delta x = (n + \\frac{1}{2})\\lambda$

### Standing Waves
- Standing wave: $y(x,t) = 2A\\sin(kx)\\cos(\\omega t)$
- Nodes: points of zero amplitude, $x = n\\frac{\\lambda}{2}$
- Antinodes: points of maximum amplitude, $x = (n + \\frac{1}{2})\\frac{\\lambda}{2}$
- String fixed at both ends: $\\lambda_n = \\frac{2L}{n}$, $f_n = n\\frac{v}{2L}$ ($n = 1, 2, 3, ...$)
- Pipe open at both ends: same as string
- Pipe closed at one end: $\\lambda_n = \\frac{4L}{n}$, $f_n = n\\frac{v}{4L}$ ($n = 1, 3, 5, ...$)

### Doppler Effect
- Source moving: $f' = f\\frac{v}{v \\mp v_s}$ (− approaching, + receding)
- Observer moving: $f' = f\\frac{v \\pm v_o}{v}$ (+ approaching, − receding)
- Both moving: $f' = f\\frac{v \\pm v_o}{v \\mp v_s}$

### Problem-Solving Strategy
1. Identify wave parameters: $A$, $\\lambda$, $f$, $v$
2. Write wave equation if needed
3. Apply superposition for interference
4. Use boundary conditions for standing waves
5. Apply Doppler formula with correct signs
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Wave equation from parameters
1. Given: amplitude, wavelength, frequency, direction
2. Calculate $k = 2\\pi/\\lambda$ and $\\omega = 2\\pi f$
3. Write $y(x,t) = A\\sin(kx \\mp \\omega t)$ (− for +x direction, + for −x direction)
4. Apply initial conditions if given

### Pattern 2: Interference problems
1. Find path difference: $\\Delta x = |x_1 - x_2|$
2. Express in terms of wavelength: $\\Delta x = n\\lambda$ or $(n + \\frac{1}{2})\\lambda$
3. Determine constructive or destructive interference
4. Calculate resultant amplitude

### Pattern 3: Standing waves on string
1. Identify boundary conditions (fixed/free ends)
2. Use $\\lambda_n = \\frac{2L}{n}$ for both ends fixed
3. Calculate frequency: $f_n = n\\frac{v}{2L}$ where $v = \\sqrt{T/\\mu}$
4. Fundamental: $n = 1$, harmonics: $n = 2, 3, 4, ...$

### Pattern 4: Doppler effect
1. Identify source and observer velocities
2. Determine directions (toward or away)
3. Apply $f' = f\\frac{v \\pm v_o}{v \\mp v_s}$ with correct signs
4. Calculate frequency shift
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use WAVE diagram for:
- Wave propagation showing wavelength and amplitude
- Reflection and transmission at boundaries
- Standing wave patterns with nodes and antinodes
- Superposition of two waves
- **Place in problem context**

### Use GRAPH for:
- $y$ vs $x$ at fixed time (snapshot)
- $y$ vs $t$ at fixed position (oscillation)
- Amplitude vs position for standing waves
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For a wave traveling in the +x direction with given parameters:}
k &= \\frac{2\\pi}{\\lambda} = \\frac{2\\pi}{0.5} = 4\\pi \\ \\mathrm{rad/m} \\\\
\\omega &= 2\\pi f = 2\\pi \\times 10 = 20\\pi \\ \\mathrm{rad/s}
\\end{align*}

\\begin{align*}
\\intertext{The wave equation is:}
y(x,t) &= A\\sin(kx - \\omega t) \\\\
       &= 0.1\\sin(4\\pi x - 20\\pi t) \\ \\mathrm{m}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Wrong sign in wave equation**
   - Wave traveling in +x: $y = A\\sin(kx - \\omega t)$
   - Wave traveling in −x: $y = A\\sin(kx + \\omega t)$
   - Don't confuse the signs

2. **Confusing wavelength and period**
   - Wavelength $\\lambda$ is spatial (meters)
   - Period $T$ is temporal (seconds)
   - Related by $v = \\lambda/T = \\lambda f$

3. **Standing wave boundary conditions**
   - Both ends fixed: $\\lambda_n = 2L/n$ ($n = 1, 2, 3, ...$)
   - One end closed: $\\lambda_n = 4L/n$ ($n = 1, 3, 5, ...$, odd only)
   - Don't use wrong formula

4. **Doppler sign errors**
   - Approaching: frequencies increase
   - Receding: frequencies decrease
   - Source approaching: denominator has minus
   - Observer approaching: numerator has plus

5. **Interference path difference**
   - Constructive: $\\Delta x = n\\lambda$ (integer multiples)
   - Destructive: $\\Delta x = (n + \\frac{1}{2})\\lambda$ (half-integer multiples)
   - Don't confuse the conditions

6. **Wave speed on string**
   - $v = \\sqrt{T/\\mu}$ where $T$ is tension (not period)
   - $\\mu$ is linear mass density (kg/m), not total mass
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving wave mechanics problems (wave motion, superposition, standing waves, Doppler effect, sound).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving wave mechanics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving wave mechanics MCQ (multiple correct) problems.

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
    """Get wave mechanics prompt for question type."""
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
