"""Ray Optics solution generation for physics.

Covers: Reflection, refraction, lenses, mirrors, prisms, total internal reflection, optical instruments.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Ray Optics

### Reflection
- Law of reflection: $\\theta_i = \\theta_r$
- Plane mirror: virtual, upright, same size image
- Spherical mirrors: $\\frac{1}{f} = \\frac{1}{v} + \\frac{1}{u}$ (mirror equation)
- Magnification: $m = -\\frac{v}{u} = \\frac{h_i}{h_o}$
- Focal length: $f = \\frac{R}{2}$ where $R$ is radius of curvature
- Sign convention: object distance $u$ negative, real image $v$ positive

### Refraction
- Snell's law: $n_1\\sin\\theta_1 = n_2\\sin\\theta_2$
- Refractive index: $n = \\frac{c}{v}$
- Apparent depth: $d_{app} = \\frac{d_{real}}{n}$
- Critical angle: $\\sin\\theta_c = \\frac{n_2}{n_1}$ (for $n_1 > n_2$)
- Total internal reflection: occurs when $\\theta > \\theta_c$

### Lenses
- Lens equation: $\\frac{1}{f} = \\frac{1}{v} - \\frac{1}{u}$
- Lens maker's formula: $\\frac{1}{f} = (n-1)\\left(\\frac{1}{R_1} - \\frac{1}{R_2}\\right)$
- Power: $P = \\frac{1}{f}$ (in diopters when $f$ in meters)
- Magnification: $m = \\frac{v}{u} = \\frac{h_i}{h_o}$
- Combination: $P_{total} = P_1 + P_2$ (thin lenses in contact)

### Prism
- Deviation: $\\delta = (\\mu - 1)A$ (small angle)
- Minimum deviation: $\\mu = \\frac{\\sin\\frac{A+\\delta_m}{2}}{\\sin\\frac{A}{2}}$
- At minimum deviation: $r_1 = r_2 = \\frac{A}{2}$, $i_1 = i_2$

### Sign Convention (New Cartesian)
- Distances measured from pole/optical center
- Along incident ray direction: positive
- Opposite to incident ray: negative
- Heights above axis: positive, below: negative

### Problem-Solving Strategy
1. Draw ray diagram showing object, optical element, image
2. Identify given quantities and sign conventions
3. Apply appropriate formula (mirror/lens equation)
4. Solve for unknown
5. Interpret sign of result (real/virtual, upright/inverted)
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Mirror/lens image formation
1. Draw ray diagram (use optics diagram agent)
2. Apply sign convention to given quantities
3. Use $\\frac{1}{f} = \\frac{1}{v} + \\frac{1}{u}$ (mirror) or $\\frac{1}{f} = \\frac{1}{v} - \\frac{1}{u}$ (lens)
4. Calculate magnification: $m = -v/u$ (mirror) or $m = v/u$ (lens)
5. Interpret results

### Pattern 2: Refraction problems
1. Identify interface and media
2. Apply Snell's law: $n_1\\sin\\theta_1 = n_2\\sin\\theta_2$
3. Check for total internal reflection if going from denser to rarer
4. Calculate angles or refractive indices

### Pattern 3: Lens combination
1. For first lens: find image using lens equation
2. Image of first lens becomes object for second lens
3. Calculate object distance for second lens
4. Apply lens equation again
5. Total magnification: $m = m_1 \\times m_2$

### Pattern 4: Prism deviation
1. Apply Snell's law at both surfaces
2. Use geometry: $A = r_1 + r_2$, $\\delta = i_1 + i_2 - A$
3. For minimum deviation: use $\\mu = \\frac{\\sin\\frac{A+\\delta_m}{2}}{\\sin\\frac{A}{2}}$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use OPTICS diagram for:
- Ray diagrams for mirrors and lenses
- Refraction at interfaces
- Prism ray paths
- Total internal reflection
- Optical instrument setups
- **Place in problem context**

### Use GRAPH for:
- Object-image distance relationships
- Magnification vs distance plots
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Using the mirror equation with sign convention ($u = -30$ cm, $f = -15$ cm):}
\\frac{1}{f} &= \\frac{1}{v} + \\frac{1}{u} \\\\
\\frac{1}{-15} &= \\frac{1}{v} + \\frac{1}{-30} \\\\
\\frac{1}{v} &= -\\frac{1}{15} + \\frac{1}{30} \\\\
v &= -30 \\ \\mathrm{cm}
\\end{align*}

\\begin{align*}
\\intertext{The magnification is:}
m &= -\\frac{v}{u} = -\\frac{-30}{-30} = -1
\\end{align*}

\\intertext{The image is real, inverted, and same size as object.}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Sign convention errors**
   - Object distance $u$ is always negative (in front of mirror/lens)
   - Real image: $v$ positive, virtual image: $v$ negative
   - Concave mirror/convex lens: $f$ positive
   - Convex mirror/concave lens: $f$ negative

2. **Confusing mirror and lens equations**
   - Mirror: $\\frac{1}{f} = \\frac{1}{v} + \\frac{1}{u}$
   - Lens: $\\frac{1}{f} = \\frac{1}{v} - \\frac{1}{u}$
   - Note the sign difference!

3. **Magnification sign**
   - Mirror: $m = -v/u$
   - Lens: $m = v/u$
   - Negative $m$ means inverted image

4. **Total internal reflection conditions**
   - Only occurs when light goes from denser to rarer medium
   - Angle of incidence must exceed critical angle
   - $\\sin\\theta_c = n_2/n_1$ where $n_1 > n_2$

5. **Lens combination errors**
   - Image of first lens is object for second
   - If image is behind second lens, object distance is positive
   - If image is in front of second lens, object distance is negative

6. **Prism formula confusion**
   - $A = r_1 + r_2$ (angle relation)
   - $\\delta = i_1 + i_2 - A$ (deviation)
   - At minimum deviation: $i_1 = i_2$ and $r_1 = r_2 = A/2$
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving ray optics problems (reflection, refraction, lenses, mirrors, prisms, TIR).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving ray optics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving ray optics MCQ (multiple correct) problems.

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
    """Get ray optics prompt for question type."""
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
