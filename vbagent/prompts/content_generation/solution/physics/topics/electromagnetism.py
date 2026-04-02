"""Electromagnetism solution generation for physics.

Covers: Electromagnetic induction, Faraday's law, Lenz's law, AC circuits, transformers, inductance.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Electromagnetism

### Electromagnetic Induction
- Faraday's law: $\\mathcal{E} = -\\frac{d\\Phi_B}{dt}$ where $\\Phi_B = \\int \\vec{B} \\cdot d\\vec{A}$
- For $N$ turns: $\\mathcal{E} = -N\\frac{d\\Phi_B}{dt}$
- Lenz's law: induced current opposes change in flux
- Motional EMF: $\\mathcal{E} = Blv$ (rod moving in field)

### Inductance
- Self-inductance: $\\mathcal{E} = -L\\frac{dI}{dt}$
- Solenoid: $L = \\mu_0 n^2 Al$ where $A$ is area, $l$ is length
- Energy stored: $U = \\frac{1}{2}LI^2$
- Energy density: $u = \\frac{B^2}{2\\mu_0}$

### LR Circuits
- Growth of current: $I(t) = I_0(1 - e^{-t/\\tau})$ where $\\tau = L/R$
- Decay of current: $I(t) = I_0 e^{-t/\\tau}$
- Time constant: $\\tau = L/R$

### AC Circuits
- Voltage: $V(t) = V_0\\sin(\\omega t)$
- Current: $I(t) = I_0\\sin(\\omega t + \\phi)$
- RMS values: $V_{rms} = V_0/\\sqrt{2}$, $I_{rms} = I_0/\\sqrt{2}$
- Power: $P_{avg} = V_{rms}I_{rms}\\cos\\phi$ where $\\phi$ is phase difference

### Reactance and Impedance
- Inductive reactance: $X_L = \\omega L$
- Capacitive reactance: $X_C = \\frac{1}{\\omega C}$
- Impedance: $Z = \\sqrt{R^2 + (X_L - X_C)^2}$
- Phase angle: $\\tan\\phi = \\frac{X_L - X_C}{R}$

### Resonance
- Resonant frequency: $\\omega_0 = \\frac{1}{\\sqrt{LC}}$
- At resonance: $X_L = X_C$, $Z = R$ (minimum), current maximum
- Quality factor: $Q = \\frac{\\omega_0 L}{R}$

### Transformers
- Voltage ratio: $\\frac{V_s}{V_p} = \\frac{N_s}{N_p}$
- Current ratio: $\\frac{I_s}{I_p} = \\frac{N_p}{N_s}$
- Power: $P_p = P_s$ (ideal transformer)
- Step-up: $N_s > N_p$, step-down: $N_s < N_p$

### Problem-Solving Strategy
1. Identify changing magnetic flux
2. Calculate $d\\Phi_B/dt$
3. Apply Faraday's law: $\\mathcal{E} = -N d\\Phi_B/dt$
4. Use Lenz's law for direction
5. For AC circuits: calculate reactances and impedance
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Induced EMF from changing flux
1. Calculate initial and final flux: $\\Phi_B = BA\\cos\\theta$
2. Find rate of change: $\\frac{d\\Phi_B}{dt}$
3. Apply Faraday's law: $\\mathcal{E} = -N\\frac{d\\Phi_B}{dt}$
4. Use Lenz's law for current direction

### Pattern 2: Motional EMF
1. Identify rod length $l$, velocity $v$, and field $B$
2. Calculate EMF: $\\mathcal{E} = Blv$
3. If circuit closed: current $I = \\mathcal{E}/R$
4. Force on rod: $F = BIl$ (opposes motion)

### Pattern 3: LR circuit
1. Identify $L$, $R$, and $\\mathcal{E}$
2. Time constant: $\\tau = L/R$
3. Final current: $I_0 = \\mathcal{E}/R$
4. Current growth: $I(t) = I_0(1 - e^{-t/\\tau})$

### Pattern 4: AC circuit analysis
1. Calculate reactances: $X_L = \\omega L$, $X_C = 1/(\\omega C)$
2. Calculate impedance: $Z = \\sqrt{R^2 + (X_L - X_C)^2}$
3. Current: $I_{rms} = V_{rms}/Z$
4. Phase angle: $\\tan\\phi = (X_L - X_C)/R$
5. Power: $P = V_{rms}I_{rms}\\cos\\phi$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use CIRCUIT diagram for:
- LR circuits
- AC circuits (RLC)
- Transformer circuits
- **Place in problem context**

### Use GENERIC diagram for:
- Magnetic flux through loops
- Moving conductors in magnetic fields
- Induced current directions
- **Place in problem context**

### Use GRAPH for:
- Current vs time (LR circuits)
- Voltage/current vs time (AC)
- Impedance vs frequency
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{The rate of change of magnetic flux is:}
\\frac{d\\Phi_B}{dt} &= \\frac{\\Delta(BA)}{\\Delta t} \\\\
                     &= A\\frac{\\Delta B}{\\Delta t} \\\\
                     &= \\pi(0.1)^2 \\times \\frac{0.5 - 0}{0.1} \\\\
                     &= 0.157 \\ \\mathrm{Wb/s}
\\end{align*}

\\begin{align*}
\\intertext{The induced EMF is:}
\\mathcal{E} &= -N\\frac{d\\Phi_B}{dt} \\\\
             &= -100 \\times 0.157 \\\\
             &= -15.7 \\ \\mathrm{V}
\\end{align*}

\\intertext{The magnitude is $15.7$ V, and the negative sign indicates the direction by Lenz's law.}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Sign in Faraday's law**
   - Negative sign indicates Lenz's law (opposition)
   - Magnitude: $|\\mathcal{E}| = N|d\\Phi_B/dt|$
   - Direction: use Lenz's law separately

2. **Flux calculation errors**
   - $\\Phi_B = BA\\cos\\theta$ where $\\theta$ is angle between $\\vec{B}$ and normal
   - Maximum flux when $\\theta = 0°$ (perpendicular)
   - Zero flux when $\\theta = 90°$ (parallel)

3. **LR circuit confusion**
   - Time constant: $\\tau = L/R$ (not $R/L$)
   - After $\\tau$: current reaches $63\\%$ of final value
   - Final current: $I_0 = \\mathcal{E}/R$ (inductance doesn't affect steady state)

4. **AC circuit errors**
   - Use RMS values for power: $P = V_{rms}I_{rms}\\cos\\phi$
   - Don't use peak values unless specified
   - Phase angle matters: $\\cos\\phi$ is power factor

5. **Reactance vs resistance**
   - Resistance: dissipates energy
   - Reactance: stores energy (no power dissipation)
   - Only resistance contributes to power: $P = I_{rms}^2 R$

6. **Transformer equations**
   - Voltage ratio: $V_s/V_p = N_s/N_p$
   - Current ratio: $I_s/I_p = N_p/N_s$ (inverse!)
   - Power conserved: $V_pI_p = V_sI_s$

7. **Resonance conditions**
   - At resonance: $X_L = X_C$ (not $X_L + X_C = 0$)
   - Impedance minimum: $Z = R$
   - Current maximum: $I = V/R$
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving electromagnetism problems (EMI, Faraday's law, Lenz's law, AC circuits, transformers).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving electromagnetism MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving electromagnetism MCQ (multiple correct) problems.

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
    """Get electromagnetism prompt for question type."""
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
