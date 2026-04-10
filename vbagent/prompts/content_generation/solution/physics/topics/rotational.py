"""Rotational Mechanics solution generation for physics.

Covers: Torque, angular momentum, moment of inertia, rolling motion, rotational dynamics.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Rotational Mechanics

### Rotational Kinematics
- Angular displacement: $\\theta$ (radians)
- Angular velocity: $\\omega = \\frac{d\\theta}{dt}$
- Angular acceleration: $\\alpha = \\frac{d\\omega}{dt}$
- Equations: $\\omega = \\omega_0 + \\alpha t$, $\\theta = \\omega_0 t + \\frac{1}{2}\\alpha t^2$, $\\omega^2 = \\omega_0^2 + 2\\alpha\\theta$
- Relation to linear: $v = r\\omega$, $a_t = r\\alpha$, $a_c = r\\omega^2$

### Rotational Dynamics
- Torque: $\\vec{\\tau} = \\vec{r} \\times \\vec{F}$, magnitude $\\tau = rF\\sin\\theta$
- Newton's second law: $\\sum \\tau = I\\alpha$
- Moment of inertia: $I = \\sum m_i r_i^2$ or $I = \\int r^2 \\, dm$
- Parallel axis theorem: $I = I_{cm} + Md^2$
- Perpendicular axis theorem: $I_z = I_x + I_y$ (for planar objects)

### Common Moments of Inertia
- Point mass: $I = mr^2$
- Rod (center): $I = \\frac{1}{12}ML^2$
- Rod (end): $I = \\frac{1}{3}ML^2$
- Disk (center): $I = \\frac{1}{2}MR^2$
- Sphere (center): $I = \\frac{2}{5}MR^2$
- Hoop (center): $I = MR^2$

### Angular Momentum and Energy
- Angular momentum: $\\vec{L} = I\\vec{\\omega}$ or $\\vec{L} = \\vec{r} \\times \\vec{p}$
- Conservation: $\\sum \\tau_{ext} = 0 \\Rightarrow L = constant$
- Rotational KE: $KE_{rot} = \\frac{1}{2}I\\omega^2$
- Total KE (rolling): $KE = \\frac{1}{2}mv^2 + \\frac{1}{2}I\\omega^2$

### Rolling Motion
- Pure rolling: $v_{cm} = R\\omega$ (no slipping)
- Acceleration: $a_{cm} = R\\alpha$
- Friction provides torque for rolling
- Rolling down incline: $a = \\frac{g\\sin\\theta}{1 + I/(MR^2)}$

### Problem-Solving Strategy
1. Draw mechanics diagram showing rotation axis and forces
2. Calculate torques about chosen axis
3. Apply $\\sum \\tau = I\\alpha$ or conservation of angular momentum
4. For rolling: use $v = R\\omega$ constraint
5. Solve for unknown
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Torque and angular acceleration
1. Choose rotation axis (usually through pivot or center)
2. Calculate torque for each force: $\\tau = rF\\sin\\theta$
3. Apply $\\sum \\tau = I\\alpha$
4. Solve for $\\alpha$ or other unknown

### Pattern 2: Conservation of angular momentum
1. Identify system with no external torque
2. Write $L_i = L_f$
3. Expand: $I_i\\omega_i = I_f\\omega_f$
4. Solve for final angular velocity

### Pattern 3: Rolling down incline
1. Draw mechanics diagram with forces
2. Apply $\\sum F = ma$ for translation
3. Apply $\\sum \\tau = I\\alpha$ for rotation
4. Use rolling constraint: $a = R\\alpha$
5. Solve system of equations

### Pattern 4: Energy method for rolling
1. Use conservation of energy
2. Include both translational and rotational KE
3. $mgh = \\frac{1}{2}mv^2 + \\frac{1}{2}I\\omega^2$
4. Use $v = R\\omega$ and solve
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use MECHANICS diagram for:
- Rotating objects with forces and torques
- Rolling objects on inclines
- Pulley systems with rotation
- Objects with rotation axis
- **Place in problem context**

### Use GRAPH for:
- Angular velocity vs time
- Torque vs angle
- Angular momentum vs time
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For the disk rolling down the incline, applying Newton's second law:}
\\sum F_x &= ma \\\\
mg\\sin\\theta - f &= ma
\\end{align*}

\\begin{align*}
\\intertext{For rotational motion about the center:}
\\sum \\tau &= I\\alpha \\\\
fR &= \\frac{1}{2}MR^2 \\cdot \\frac{a}{R} \\\\
f &= \\frac{1}{2}Ma
\\end{align*}

\\begin{align*}
\\intertext{Substituting back:}
mg\\sin\\theta - \\frac{1}{2}Ma &= Ma \\\\
a &= \\frac{2g\\sin\\theta}{3} \\\\
  &= \\frac{2 \\times 9.8 \\times \\sin 30^\\circ}{3} \\\\
  &= 3.3 \\ \\mathrm{m/s^2}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Wrong moment of inertia**
   - Use correct formula for shape
   - Apply parallel axis theorem when axis not through CM
   - Don't forget $I = I_{cm} + Md^2$

2. **Forgetting rolling constraint**
   - Pure rolling: $v = R\\omega$ and $a = R\\alpha$
   - This relates translational and rotational motion
   - Without slipping: friction is static, not kinetic

3. **Wrong torque calculation**
   - Torque is $\\tau = rF\\sin\\theta$ where $\\theta$ is angle between $\\vec{r}$ and $\\vec{F}$
   - Only perpendicular component of force creates torque
   - Choose consistent sign convention (CCW positive)

4. **Axis choice errors**
   - Torque depends on choice of axis
   - Choose axis through pivot or CM for simplicity
   - Forces through axis contribute zero torque

5. **Energy errors for rolling**
   - Total KE = translational + rotational
   - Don't forget $\\frac{1}{2}I\\omega^2$ term
   - Use $v = R\\omega$ to eliminate one variable

6. **Angular momentum direction**
   - $\\vec{L}$ is along rotation axis (right-hand rule)
   - For point mass: $\\vec{L} = \\vec{r} \\times \\vec{p}$
   - Conservation requires $\\sum \\tau_{ext} = 0$
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving rotational mechanics problems (torque, angular momentum, moment of inertia, rolling motion).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving rotational mechanics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving rotational mechanics MCQ (multiple correct) problems.

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
    """Get rotational mechanics prompt for question type."""
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
