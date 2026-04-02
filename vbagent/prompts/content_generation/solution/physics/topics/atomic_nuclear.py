"""Atomic and Nuclear Physics solution generation for physics.

Covers: Atomic models, Bohr model, X-rays, nuclear reactions, radioactivity, decay, binding energy.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Atomic and Nuclear Physics

### Bohr Model
- Energy levels: $E_n = -\\frac{13.6}{n^2}$ eV (hydrogen)
- Radius: $r_n = n^2 a_0$ where $a_0 = 0.529$ Å (Bohr radius)
- Angular momentum: $L = n\\hbar$ where $\\hbar = h/(2\\pi)$
- Frequency: $f = \\frac{E_i - E_f}{h}$
- Rydberg formula: $\\frac{1}{\\lambda} = R\\left(\\frac{1}{n_f^2} - \\frac{1}{n_i^2}\\right)$ where $R = 1.097 \\times 10^7$ m⁻¹

### Spectral Series
- Lyman series: $n_f = 1$ (UV)
- Balmer series: $n_f = 2$ (visible)
- Paschen series: $n_f = 3$ (IR)
- Brackett series: $n_f = 4$ (IR)

### X-rays
- Minimum wavelength: $\\lambda_{min} = \\frac{hc}{eV}$ where $V$ is accelerating voltage
- Moseley's law: $f = a(Z - b)$ where $Z$ is atomic number
- Characteristic X-rays: from electron transitions

### Nuclear Structure
- Mass number: $A = Z + N$ (protons + neutrons)
- Atomic mass unit: $1$ u $= 931.5$ MeV/c²
- Nuclear radius: $R = R_0 A^{1/3}$ where $R_0 \\approx 1.2$ fm

### Binding Energy
- Mass defect: $\\Delta m = (Zm_p + Nm_n) - M_{nucleus}$
- Binding energy: $BE = \\Delta m c^2$
- Binding energy per nucleon: $BE/A$
- Most stable: $^{56}$Fe with highest $BE/A$

### Radioactive Decay
- Decay law: $N(t) = N_0 e^{-\\lambda t}$
- Activity: $A(t) = \\lambda N(t) = A_0 e^{-\\lambda t}$
- Half-life: $t_{1/2} = \\frac{\\ln 2}{\\lambda} = \\frac{0.693}{\\lambda}$
- Mean life: $\\tau = \\frac{1}{\\lambda}$

### Decay Types
- Alpha decay: $^A_Z X \\to ^{A-4}_{Z-2}Y + ^4_2He$
- Beta minus: $^A_Z X \\to ^A_{Z+1}Y + e^- + \\bar{\\nu}_e$
- Beta plus: $^A_Z X \\to ^A_{Z-1}Y + e^+ + \\nu_e$
- Gamma decay: $^A_Z X^* \\to ^A_Z X + \\gamma$

### Nuclear Reactions
- Q-value: $Q = (m_i - m_f)c^2$
- Conservation: mass-energy, charge, mass number, momentum
- Fission: heavy nucleus splits
- Fusion: light nuclei combine

### Problem-Solving Strategy
1. Identify atomic/nuclear process
2. Apply conservation laws
3. Calculate energy changes
4. For decay: use exponential law
5. Convert between mass and energy using $c^2$
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Bohr model transitions
1. Identify initial and final states: $n_i$ and $n_f$
2. Calculate energies: $E_n = -13.6/n^2$ eV
3. Energy of photon: $E_{photon} = E_i - E_f$
4. Wavelength: $\\lambda = hc/E_{photon}$

### Pattern 2: Radioactive decay
1. Identify half-life $t_{1/2}$ or decay constant $\\lambda$
2. Relate: $\\lambda = 0.693/t_{1/2}$
3. Apply decay law: $N(t) = N_0 e^{-\\lambda t}$
4. For activity: $A(t) = A_0 e^{-\\lambda t}$

### Pattern 3: Binding energy calculation
1. Find mass defect: $\\Delta m = (Zm_p + Nm_n) - M$
2. Convert to energy: $BE = \\Delta m \\times 931.5$ MeV
3. Per nucleon: $BE/A$
4. Compare for stability

### Pattern 4: Nuclear reaction Q-value
1. List masses of reactants and products
2. Calculate mass difference: $\\Delta m = m_i - m_f$
3. Q-value: $Q = \\Delta m c^2 = \\Delta m \\times 931.5$ MeV
4. $Q > 0$: exothermic, $Q < 0$: endothermic
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GENERIC diagram for:
- Energy level diagrams
- Spectral series
- Nuclear decay schemes
- Reaction diagrams
- **Place in problem context**

### Use GRAPH for:
- Decay curves (N vs t or A vs t)
- Binding energy per nucleon vs A
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For the transition from $n = 3$ to $n = 2$ in hydrogen:}
E_3 &= -\\frac{13.6}{3^2} = -1.51 \\ \\mathrm{eV} \\\\
E_2 &= -\\frac{13.6}{2^2} = -3.40 \\ \\mathrm{eV}
\\end{align*}

\\begin{align*}
\\intertext{The energy of the emitted photon is:}
E_{photon} &= E_3 - E_2 \\\\
           &= -1.51 - (-3.40) \\\\
           &= 1.89 \\ \\mathrm{eV}
\\end{align*}

\\begin{align*}
\\intertext{The wavelength is:}
\\lambda &= \\frac{hc}{E} \\\\
         &= \\frac{1240 \\ \\mathrm{eV \\cdot nm}}{1.89 \\ \\mathrm{eV}} \\\\
         &= 656 \\ \\mathrm{nm}
\\end{align*}

\\intertext{This is the H$_\\alpha$ line in the Balmer series.}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Energy sign errors**
   - Bohr energies are negative (bound states)
   - Energy released: $E_{photon} = E_i - E_f$ (positive)
   - Ground state has most negative energy

2. **Half-life vs decay constant**
   - $t_{1/2} = 0.693/\\lambda$ (not $1/\\lambda$)
   - After one half-life: $N = N_0/2$ (not zero)
   - After $n$ half-lives: $N = N_0/2^n$

3. **Mass-energy conversion**
   - $1$ u $= 931.5$ MeV/c² (not 931.5 MeV)
   - $E = mc^2$ requires $c^2$ factor
   - Use consistent units (MeV or J)

4. **Binding energy confusion**
   - Higher binding energy per nucleon = more stable
   - Mass defect is positive (mass lost in binding)
   - Binding energy is energy required to disassemble nucleus

5. **Conservation in decay**
   - Mass number $A$ conserved
   - Charge (atomic number $Z$) conserved
   - Energy-momentum conserved
   - Neutrino carries away energy in beta decay

6. **Spectral series**
   - Lyman: $n_f = 1$ (UV, highest energy)
   - Balmer: $n_f = 2$ (visible)
   - Paschen: $n_f = 3$ (IR, lower energy)
   - Don't confuse final state values
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving atomic and nuclear physics problems (Bohr model, X-rays, radioactivity, nuclear reactions, binding energy).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving atomic and nuclear physics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving atomic and nuclear physics MCQ (multiple correct) problems.

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
    """Get atomic/nuclear physics prompt for question type."""
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
