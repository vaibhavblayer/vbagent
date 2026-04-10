"""Mechanics solution generation for physics.

Covers: Kinematics, dynamics, Newton's laws, forces, friction, circular motion.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Mechanics

### Kinematics
- Equations of motion: $v = u + at$, $s = ut + \\frac{1}{2}at^2$, $v^2 = u^2 + 2as$
- Relative motion: $\\vec{v}_{AB} = \\vec{v}_A - \\vec{v}_B$
- Projectile motion: horizontal and vertical components independent
- Circular motion: $a_c = \\frac{v^2}{r} = \\omega^2 r$

### Dynamics
- Newton's laws: $\\sum \\vec{F} = m\\vec{a}$
- Free body diagrams: isolate object, show all forces
- Common forces: weight ($mg$), normal ($N$), friction ($f$), tension ($T$)
- Friction: $f_s \\leq \\mu_s N$, $f_k = \\mu_k N$

### Problem-Solving Strategy
1. Draw diagram showing physical setup (use mechanics diagram for system)
2. Identify all forces acting on each object
3. Draw FBD for force analysis (if needed in solution)
4. Choose coordinate system (align with motion or incline)
5. Apply Newton's second law component-wise
6. Solve system of equations
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Single object with forces
1. Draw mechanics diagram showing setup
2. List all forces
3. Apply $\\sum F_x = ma_x$ and $\\sum F_y = ma_y$
4. Solve for unknown

### Pattern 2: Connected objects (pulley, rope)
1. Draw mechanics diagram showing full system
2. Identify constraint (same tension, same acceleration magnitude)
3. Write equations for each object
4. Solve simultaneously

### Pattern 3: Inclined plane
1. Draw mechanics diagram with block on incline
2. Choose tilted coordinates (x along incline, y perpendicular)
3. Resolve weight: $mg\\sin\\theta$ (down incline), $mg\\cos\\theta$ (into incline)
4. Apply Newton's laws in tilted frame

### Pattern 4: Circular motion
1. Draw mechanics diagram showing circular path
2. Identify center-seeking force (tension, normal, friction, or combination)
3. Apply $\\sum F_c = \\frac{mv^2}{r}$ toward center
4. Apply $\\sum F_{\\perp} = 0$ perpendicular to motion
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use MECHANICS diagram for:
- Problem setup: showing pulleys, springs, inclines, ropes, blocks
- System overview: how objects are connected
- Circular motion paths with objects
- Any physical arrangement of the system
- **Place in problem context, NOT in solution**

### Use FBD (Free Body Diagram) for:
- Force analysis in solution steps
- Showing all forces on isolated body
- When deriving equations of motion
- **Place in solution, after setting up problem**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For the block on the incline, applying Newton's second law along the incline:}
\\sum F_x &= ma \\\\
mg\\sin\\theta - f &= ma
\\end{align*}

\\begin{center}
% FBD here if needed for force analysis
\\end{center}

\\begin{align*}
\\intertext{With $f = \\mu_k N$ and $N = mg\\cos\\theta$:}
a &= g(\\sin\\theta - \\mu_k\\cos\\theta) \\\\
  &= 9.8(\\sin 30^\\circ - 0.2\\cos 30^\\circ) \\\\
  &= 3.2 \\ \\mathrm{m/s^2}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Confusing mechanics diagram with FBD**
   - Mechanics diagram = physical setup (pulleys, ropes, blocks)
   - FBD = isolated body with force arrows only

2. **Wrong coordinate system**
   - For inclines: align x-axis along incline, not horizontal
   - For circular motion: use radial-tangential, not x-y

3. **Forgetting constraint equations**
   - Connected objects: relate accelerations
   - Rope over pulley: $a_1 = a_2$ (magnitude)
   - Rope length constant: $x_1 + x_2 = L$

4. **Sign errors**
   - Be consistent with positive direction
   - Tension always pulls away from object
   - Friction opposes relative motion

5. **Missing forces**
   - Always include weight $mg$ downward
   - Normal force perpendicular to surface
   - Tension in every rope/string segment

6. **Circular motion errors**
   - Centripetal force is NET inward force, not a separate force
   - At top of circle: $T + mg = \\frac{mv^2}{r}$
   - At bottom: $T - mg = \\frac{mv^2}{r}$
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving mechanics problems (kinematics, dynamics, forces, friction, circular motion).

""" + TOPIC_CONCEPTS + """

""" + COMMON_PATTERNS + """

""" + DIAGRAM_GUIDANCE + """

""" + TYPICAL_MISTAKES + """

""" + LATEX_FORMATTING_RULES + """

""" + SOLUTION_QUALITY + """

## Output Format

Return a JSON object with:
- `solution_latex`: Complete solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams needed (use mechanics diagram for setup, FBD for force analysis)
- `answer_type`: "subjective" or "integer"
- `answer_value`: Final numerical answer if integer type, null otherwise
"""

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving mechanics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving mechanics MCQ (multiple correct) problems.

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
    """Get mechanics prompt for question type."""
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
