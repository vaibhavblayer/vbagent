"""Current Electricity solution generation for physics.

Covers: DC circuits, Ohm's law, Kirchhoff's laws, RC circuits, electrical power, resistor networks.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Current Electricity

### Basic Concepts
- Current: $I = \\frac{dQ}{dt}$ (rate of charge flow)
- Ohm's law: $V = IR$
- Resistance: $R = \\rho\\frac{L}{A}$ where $\\rho$ is resistivity
- Conductance: $G = \\frac{1}{R}$
- Current density: $\\vec{J} = \\frac{I}{A} = \\sigma\\vec{E}$

### Kirchhoff's Laws
- Current law (KCL): $\\sum I_{in} = \\sum I_{out}$ at any junction
- Voltage law (KVL): $\\sum V = 0$ around any closed loop
- Sign convention: voltage rise positive, voltage drop negative

### Resistor Combinations
- Series: $R_{eq} = R_1 + R_2 + ...$
- Parallel: $\\frac{1}{R_{eq}} = \\frac{1}{R_1} + \\frac{1}{R_2} + ...$
- In series: same current, voltages add
- In parallel: same voltage, currents add

### Power and Energy
- Power dissipated: $P = VI = I^2R = \\frac{V^2}{R}$
- Energy: $E = Pt = VIt$
- Maximum power transfer: when load resistance equals source resistance

### EMF and Internal Resistance
- Terminal voltage: $V = \\mathcal{E} - Ir$ where $r$ is internal resistance
- Power delivered: $P = VI = I(\\mathcal{E} - Ir)$
- Power dissipated internally: $P_r = I^2r$

### RC Circuits
- Charging: $Q(t) = Q_0(1 - e^{-t/RC})$, $I(t) = I_0 e^{-t/RC}$
- Discharging: $Q(t) = Q_0 e^{-t/RC}$, $I(t) = I_0 e^{-t/RC}$
- Time constant: $\\tau = RC$
- After time $\\tau$: charge reaches $63\\%$ of final value (charging)

### Wheatstone Bridge
- Balanced condition: $\\frac{R_1}{R_2} = \\frac{R_3}{R_4}$
- No current through galvanometer when balanced

### Problem-Solving Strategy
1. Draw circuit diagram clearly
2. Identify series and parallel combinations
3. Simplify circuit step by step
4. Apply Kirchhoff's laws if needed
5. Calculate currents, voltages, power
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Simple resistor network
1. Identify series and parallel combinations
2. Calculate equivalent resistance step by step
3. Find total current: $I = V/R_{eq}$
4. Work backwards to find current/voltage in each resistor

### Pattern 2: Kirchhoff's laws application
1. Label all currents (assume directions)
2. Apply KCL at junctions
3. Apply KVL around independent loops
4. Solve system of equations
5. Negative current means opposite direction

### Pattern 3: RC circuit charging
1. Identify $R$, $C$, and $\\mathcal{E}$
2. Time constant: $\\tau = RC$
3. Charge: $Q(t) = C\\mathcal{E}(1 - e^{-t/\\tau})$
4. Current: $I(t) = \\frac{\\mathcal{E}}{R}e^{-t/\\tau}$
5. Voltage across capacitor: $V_C(t) = \\mathcal{E}(1 - e^{-t/\\tau})$

### Pattern 4: Power calculations
1. Find current through each element
2. Calculate power: $P = I^2R$ or $P = VI$
3. Total power supplied by source: $P = \\mathcal{E}I$
4. Check: power supplied = power dissipated
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use CIRCUIT diagram for:
- All circuit problems
- Resistor networks
- RC circuits
- Wheatstone bridge
- **Place in problem context**

### Use GRAPH for:
- Current vs time (RC circuits)
- Voltage vs time (RC circuits)
- Charge vs time (RC circuits)
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For resistors in series, the equivalent resistance is:}
R_{eq} &= R_1 + R_2 + R_3 \\\\
       &= 10 + 20 + 30 \\\\
       &= 60 \\ \\Omega
\\end{align*}

\\begin{align*}
\\intertext{The current through the circuit is:}
I &= \\frac{V}{R_{eq}} \\\\
  &= \\frac{12}{60} \\\\
  &= 0.2 \\ \\mathrm{A}
\\end{align*}

\\begin{align*}
\\intertext{The power dissipated is:}
P &= VI \\\\
  &= 12 \\times 0.2 \\\\
  &= 2.4 \\ \\mathrm{W}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Series vs parallel confusion**
   - Series: same current, $R_{eq} = \\sum R_i$
   - Parallel: same voltage, $\\frac{1}{R_{eq}} = \\sum \\frac{1}{R_i}$
   - Opposite of capacitor rules!

2. **Kirchhoff's law sign errors**
   - KVL: voltage rise (+), voltage drop (−)
   - Going through resistor with current: voltage drop
   - Going through battery from − to +: voltage rise

3. **Internal resistance**
   - Terminal voltage: $V = \\mathcal{E} - Ir$ (not $\\mathcal{E} + Ir$)
   - When current increases, terminal voltage decreases
   - Maximum current when $V = 0$: $I_{max} = \\mathcal{E}/r$

4. **Power formula selection**
   - $P = I^2R$: use when current known
   - $P = V^2/R$: use when voltage known
   - $P = VI$: use when both known
   - All equivalent, but choose wisely

5. **RC circuit errors**
   - Time constant $\\tau = RC$ (not $1/RC$)
   - After $\\tau$: $63\\%$ charged (not $100\\%$)
   - Fully charged: $t \\approx 5\\tau$
   - Initial current: $I_0 = \\mathcal{E}/R$ (not $\\mathcal{E}/R + 1/C$)

6. **Wheatstone bridge**
   - Balanced: $R_1/R_2 = R_3/R_4$
   - No current through galvanometer when balanced
   - Don't try to simplify bridge when not balanced
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving current electricity problems (DC circuits, Ohm's law, Kirchhoff's laws, RC circuits, power).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving current electricity MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving current electricity MCQ (multiple correct) problems.

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
    """Get current electricity prompt for question type."""
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
