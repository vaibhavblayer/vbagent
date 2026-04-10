"""Wave Optics solution generation for physics.

Covers: Interference (YDSE, thin films), diffraction (single slit, double slit), polarization, resolving power.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Wave Optics

### Young's Double Slit Experiment (YDSE)
- Path difference: $\\Delta x = d\\sin\\theta \\approx \\frac{dy}{D}$ (for small $\\theta$)
- Constructive interference (bright fringe): $\\Delta x = n\\lambda$ where $n = 0, \\pm 1, \\pm 2, ...$
- Destructive interference (dark fringe): $\\Delta x = (n + \\frac{1}{2})\\lambda$
- Fringe width: $\\beta = \\frac{\\lambda D}{d}$
- Position of $n$-th bright fringe: $y_n = \\frac{n\\lambda D}{d}$
- Intensity: $I = I_0\\cos^2\\left(\\frac{\\pi d\\sin\\theta}{\\lambda}\\right) = 4I_0\\cos^2\\left(\\frac{\\phi}{2}\\right)$

### Thin Film Interference
- Path difference in film: $\\Delta x = 2\\mu t\\cos r$
- Phase change of $\\pi$ on reflection from denser medium
- Constructive (with phase change): $2\\mu t\\cos r = (n + \\frac{1}{2})\\lambda$
- Destructive (with phase change): $2\\mu t\\cos r = n\\lambda$
- For normal incidence: $\\cos r = 1$

### Single Slit Diffraction
- First minimum: $a\\sin\\theta = \\lambda$ where $a$ is slit width
- $n$-th minimum: $a\\sin\\theta = n\\lambda$ ($n = \\pm 1, \\pm 2, ...$)
- Central maximum width: $2\\lambda D/a$
- Intensity: $I = I_0\\left(\\frac{\\sin\\alpha}{\\alpha}\\right)^2$ where $\\alpha = \\frac{\\pi a\\sin\\theta}{\\lambda}$

### Diffraction Grating
- Grating equation: $d\\sin\\theta = n\\lambda$ ($n = 0, 1, 2, ...$)
- Maximum order: $n_{max} = \\frac{d}{\\lambda}$
- Resolving power: $R = \\frac{\\lambda}{\\Delta\\lambda} = nN$ where $N$ is number of lines

### Polarization
- Malus's law: $I = I_0\\cos^2\\theta$
- Brewster's angle: $\\tan\\theta_B = \\frac{n_2}{n_1}$
- At Brewster's angle: reflected ray is completely polarized

### Resolving Power
- Rayleigh criterion: two sources just resolved when central maximum of one coincides with first minimum of other
- Telescope: $R = \\frac{D}{1.22\\lambda}$ where $D$ is aperture diameter
- Microscope: $R = \\frac{2\\mu\\sin\\theta}{1.22\\lambda}$

### Problem-Solving Strategy
1. Identify type of interference/diffraction
2. Calculate path difference
3. Apply condition for constructive/destructive interference
4. Use small angle approximation when applicable
5. Solve for unknown
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: YDSE fringe position
1. Identify given: $d$ (slit separation), $D$ (screen distance), $\\lambda$ (wavelength)
2. Calculate fringe width: $\\beta = \\lambda D/d$
3. Position of $n$-th bright fringe: $y_n = n\\beta$
4. For dark fringe: $y_n = (n + \\frac{1}{2})\\beta$

### Pattern 2: Thin film interference
1. Identify film thickness $t$ and refractive index $\\mu$
2. Calculate path difference: $\\Delta x = 2\\mu t$ (normal incidence)
3. Check for phase change on reflection
4. Apply constructive/destructive condition
5. Solve for wavelength or thickness

### Pattern 3: Single slit diffraction
1. Identify slit width $a$ and wavelength $\\lambda$
2. For minima: $a\\sin\\theta = n\\lambda$
3. For small angles: $\\sin\\theta \\approx \\tan\\theta = y/D$
4. Calculate position or angle

### Pattern 4: Diffraction grating
1. Identify grating spacing $d$ (or lines per cm)
2. Apply $d\\sin\\theta = n\\lambda$
3. Calculate angle for given order
4. Maximum order: $n_{max} = d/\\lambda$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use OPTICS diagram for:
- YDSE setup with slits and screen
- Thin film with incident and reflected rays
- Single slit diffraction pattern
- Diffraction grating geometry
- Polarization setups
- **Place in problem context**

### Use GRAPH for:
- Intensity distribution patterns
- Fringe pattern on screen
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For YDSE, the fringe width is:}
\\beta &= \\frac{\\lambda D}{d} \\\\
      &= \\frac{600 \\times 10^{-9} \\times 1.0}{0.001} \\\\
      &= 6.0 \\times 10^{-4} \\ \\mathrm{m} \\\\
      &= 0.6 \\ \\mathrm{mm}
\\end{align*}

\\begin{align*}
\\intertext{The position of the 3rd bright fringe is:}
y_3 &= 3\\beta \\\\
    &= 3 \\times 0.6 \\\\
    &= 1.8 \\ \\mathrm{mm}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Phase change confusion**
   - Phase change of $\\pi$ occurs on reflection from denser medium
   - This shifts interference conditions
   - Constructive becomes $(n + \\frac{1}{2})\\lambda$, destructive becomes $n\\lambda$

2. **Path difference vs phase difference**
   - Path difference: $\\Delta x$ (in meters)
   - Phase difference: $\\phi = \\frac{2\\pi}{\\lambda}\\Delta x$ (in radians)
   - Don't confuse the two

3. **YDSE vs single slit**
   - YDSE: interference, bright fringes at $n\\lambda$
   - Single slit: diffraction, dark fringes at $n\\lambda$
   - Different phenomena!

4. **Small angle approximation**
   - $\\sin\\theta \\approx \\tan\\theta \\approx \\theta$ (in radians)
   - Valid only for small angles ($\\theta < 10°$)
   - Use exact formula for large angles

5. **Grating vs YDSE**
   - Grating: $d\\sin\\theta = n\\lambda$ (maxima)
   - YDSE: $d\\sin\\theta = n\\lambda$ (maxima) - same formula!
   - But grating has many slits, sharper maxima

6. **Resolving power formulas**
   - Telescope: $R = D/(1.22\\lambda)$
   - Grating: $R = nN$
   - Don't mix them up
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving wave optics problems (interference, diffraction, polarization, YDSE, thin films).

""" + TOPIC_CONCEPTS + """

""" + COMMON_PATTERNS + """

""" + DIAGRAM_GUIDANCE + """

""" + TYPICAL_MISTAKES + """

""" + LATEX_FORMATTING_RULES + """

""" + SOLUTION_QUALITY + """

## Output Format

Return a JSON object with:
- `solution_latex`: Complete solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams needed
- `answer_type`: "subjective" or "integer"
- `answer_value`: Final numerical answer if integer type, null otherwise
"""

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving wave optics MCQ problems.

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
- `solution_latex`: Solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Correct option letter (e.g., "A", "B", "C", "D")
"""

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving wave optics MCQ (multiple correct) problems.

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
- `solution_latex`: Solution in LaTeX
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Comma-separated correct options (e.g., "A,C" or "B,D")
"""


def get_prompt(question_type: str) -> str:
    """Get wave optics prompt for question type."""
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
