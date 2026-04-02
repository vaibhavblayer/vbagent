"""Heat Transfer solution generation for physics.

Covers: Calorimetry, specific heat, latent heat, thermal conduction, convection, radiation, thermal expansion.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Heat Transfer

### Calorimetry
- Heat transfer: $Q = mc\\Delta T$ (no phase change)
- Principle of calorimetry: $Q_{lost} = Q_{gained}$ (isolated system)
- Specific heat capacity: $c$ (J/kg·K)
- Water equivalent: $W = mc$ (effective mass of water)

### Phase Changes
- Latent heat of fusion: $Q = mL_f$ (solid ↔ liquid)
- Latent heat of vaporization: $Q = mL_v$ (liquid ↔ gas)
- During phase change: temperature remains constant
- Total heat for multiple phases: sum heat for each stage

### Thermal Conduction
- Fourier's law: $\\frac{dQ}{dt} = -kA\\frac{dT}{dx}$
- Steady state: $H = \\frac{kA\\Delta T}{L}$ where $H = dQ/dt$
- Thermal resistance: $R = \\frac{L}{kA}$
- Series: $R_{total} = R_1 + R_2 + ...$
- Parallel: $\\frac{1}{R_{total}} = \\frac{1}{R_1} + \\frac{1}{R_2} + ...$

### Thermal Radiation
- Stefan-Boltzmann law: $P = \\sigma A e T^4$
- Net radiation: $P_{net} = \\sigma A e (T^4 - T_0^4)$
- Wien's displacement law: $\\lambda_{max} T = b$ where $b = 2.9 \\times 10^{-3}$ m·K
- Stefan's constant: $\\sigma = 5.67 \\times 10^{-8}$ W/m²·K⁴

### Thermal Expansion
- Linear expansion: $\\Delta L = \\alpha L_0 \\Delta T$
- Area expansion: $\\Delta A = 2\\alpha A_0 \\Delta T$
- Volume expansion: $\\Delta V = \\gamma V_0 \\Delta T$ where $\\gamma = 3\\alpha$
- For liquids: $\\gamma$ is coefficient of volume expansion

### Newton's Law of Cooling
- Rate of cooling: $\\frac{dT}{dt} = -k(T - T_0)$
- Solution: $T(t) = T_0 + (T_i - T_0)e^{-kt}$
- Valid for small temperature differences

### Problem-Solving Strategy
1. Identify all objects and their initial temperatures
2. Determine if phase changes occur
3. Write heat equations for each object
4. Apply conservation of energy: $\\sum Q = 0$
5. Solve for unknown (final temperature, mass, etc.)
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Calorimetry (no phase change)
1. List all objects with $m$, $c$, $T_i$
2. Let final temperature be $T_f$
3. Write $Q = mc(T_f - T_i)$ for each object
4. Apply $\\sum Q = 0$ (heat lost = heat gained)
5. Solve for $T_f$

### Pattern 2: Calorimetry with phase change
1. Identify which substance undergoes phase change
2. Calculate heat for each stage:
   - Heating to melting/boiling point
   - Phase change (use latent heat)
   - Heating after phase change
3. Apply $\\sum Q = 0$
4. Solve for unknown

### Pattern 3: Thermal conduction
1. Identify layers and their thermal conductivities
2. In steady state: heat current same through all layers
3. For series: $H = \\frac{\\Delta T_{total}}{R_{total}}$
4. Calculate temperature at interfaces if needed

### Pattern 4: Radiation problems
1. Identify emitting surface area and temperature
2. Use $P = \\sigma A e T^4$ for power radiated
3. For net radiation: $P_{net} = \\sigma A e (T^4 - T_0^4)$
4. Calculate energy or temperature
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GRAPH for:
- Temperature vs time plots (cooling curves)
- Heat vs temperature (showing phase changes)
- Temperature distribution in conduction
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Heat lost by hot water:}
Q_1 &= m_1 c (T_i - T_f) \\\\
    &= 0.5 \\times 4200 \\times (80 - T_f) \\\\
    &= 2100(80 - T_f)
\\end{align*}

\\begin{align*}
\\intertext{Heat gained by cold water:}
Q_2 &= m_2 c (T_f - T_i) \\\\
    &= 0.3 \\times 4200 \\times (T_f - 20) \\\\
    &= 1260(T_f - 20)
\\end{align*}

\\begin{align*}
\\intertext{Applying $Q_1 = Q_2$:}
2100(80 - T_f) &= 1260(T_f - T_f) \\\\
168000 - 2100T_f &= 1260T_f - 25200 \\\\
3360T_f &= 193200 \\\\
T_f &= 57.5 \\ ^\\circ\\mathrm{C}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Sign errors in calorimetry**
   - Heat gained: $Q = mc(T_f - T_i)$ where $T_f > T_i$
   - Heat lost: $Q = mc(T_i - T_f)$ where $T_i > T_f$
   - Or use $\\sum Q = 0$ with proper signs

2. **Forgetting phase change heat**
   - When ice melts: need $Q = mL_f$ in addition to $mc\\Delta T$
   - When water boils: need $Q = mL_v$
   - Temperature constant during phase change

3. **Wrong specific heat**
   - Water: $c = 4200$ J/kg·K
   - Ice: $c = 2100$ J/kg·K
   - Different substances have different $c$ values

4. **Thermal conduction errors**
   - In steady state: heat current same everywhere
   - Temperature drop proportional to thermal resistance
   - Don't confuse thermal conductivity $k$ with heat current $H$

5. **Radiation formula errors**
   - Use absolute temperature (Kelvin) in $P = \\sigma A e T^4$
   - Don't forget emissivity $e$ (0 < e ≤ 1)
   - For net radiation: $T^4 - T_0^4$, not $(T - T_0)^4$

6. **Thermal expansion confusion**
   - Linear: $\\Delta L = \\alpha L_0 \\Delta T$
   - Volume: $\\Delta V = 3\\alpha V_0 \\Delta T$ (for solids)
   - For liquids: use volume expansion coefficient directly
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving heat transfer problems (calorimetry, specific heat, latent heat, conduction, radiation, thermal expansion).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving heat transfer MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving heat transfer MCQ (multiple correct) problems.

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
    """Get heat transfer prompt for question type."""
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
