"""Modern Physics solution generation for physics.

Covers: Photoelectric effect, Compton scattering, de Broglie waves, uncertainty principle, special relativity.
"""

from ..common import LATEX_FORMATTING_RULES, SOLUTION_QUALITY

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Modern Physics

### Photoelectric Effect
- Einstein's equation: $E_{photon} = hf = \\phi + KE_{max}$
- Work function: $\\phi = hf_0$ where $f_0$ is threshold frequency
- Stopping potential: $eV_0 = KE_{max}$
- Photon energy: $E = hf = \\frac{hc}{\\lambda}$
- Planck's constant: $h = 6.63 \\times 10^{-34}$ J·s

### Compton Scattering
- Wavelength shift: $\\Delta\\lambda = \\lambda' - \\lambda = \\frac{h}{m_e c}(1 - \\cos\\theta)$
- Compton wavelength: $\\lambda_C = \\frac{h}{m_e c} = 2.43 \\times 10^{-12}$ m
- Energy conservation: $E_{photon,i} = E_{photon,f} + KE_{electron}$
- Momentum conservation: $\\vec{p}_{photon,i} = \\vec{p}_{photon,f} + \\vec{p}_{electron}$

### de Broglie Waves
- de Broglie wavelength: $\\lambda = \\frac{h}{p} = \\frac{h}{mv}$
- For photon: $\\lambda = \\frac{c}{f}$
- Wave-particle duality: all matter has wave properties
- Electron diffraction confirms wave nature

### Heisenberg Uncertainty Principle
- Position-momentum: $\\Delta x \\Delta p \\geq \\frac{h}{4\\pi} = \\frac{\\hbar}{2}$
- Energy-time: $\\Delta E \\Delta t \\geq \\frac{h}{4\\pi} = \\frac{\\hbar}{2}$
- Fundamental limit on measurement precision

### Special Relativity
- Time dilation: $\\Delta t = \\frac{\\Delta t_0}{\\sqrt{1 - v^2/c^2}} = \\gamma \\Delta t_0$
- Length contraction: $L = L_0\\sqrt{1 - v^2/c^2} = \\frac{L_0}{\\gamma}$
- Lorentz factor: $\\gamma = \\frac{1}{\\sqrt{1 - v^2/c^2}}$
- Relativistic momentum: $p = \\gamma mv$
- Relativistic energy: $E = \\gamma mc^2$
- Rest energy: $E_0 = mc^2$
- Energy-momentum relation: $E^2 = (pc)^2 + (mc^2)^2$

### Photon Properties
- Energy: $E = hf = \\frac{hc}{\\lambda}$
- Momentum: $p = \\frac{E}{c} = \\frac{h}{\\lambda}$
- Rest mass: zero
- Speed: $c$ in vacuum

### Problem-Solving Strategy
1. Identify phenomenon (photoelectric, Compton, etc.)
2. List given quantities and convert units
3. Apply appropriate formula
4. For relativity: calculate $\\gamma$ first
5. Check if result makes physical sense
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Photoelectric effect
1. Calculate photon energy: $E = hf$ or $E = hc/\\lambda$
2. Find kinetic energy: $KE_{max} = E - \\phi$
3. If stopping potential given: $KE_{max} = eV_0$
4. For threshold: $hf_0 = \\phi$

### Pattern 2: Compton scattering
1. Calculate initial photon wavelength: $\\lambda = hc/E$
2. Find wavelength shift: $\\Delta\\lambda = \\lambda_C(1 - \\cos\\theta)$
3. Final wavelength: $\\lambda' = \\lambda + \\Delta\\lambda$
4. Final photon energy: $E' = hc/\\lambda'$
5. Electron KE: $KE = E - E'$

### Pattern 3: de Broglie wavelength
1. Find momentum: $p = mv$ (non-relativistic) or $p = \\gamma mv$ (relativistic)
2. Calculate wavelength: $\\lambda = h/p$
3. Compare with object size for wave effects

### Pattern 4: Relativistic calculations
1. Calculate $\\gamma = 1/\\sqrt{1 - v^2/c^2}$
2. For time dilation: $\\Delta t = \\gamma \\Delta t_0$
3. For length contraction: $L = L_0/\\gamma$
4. For energy: $E = \\gamma mc^2$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GENERIC diagram for:
- Photoelectric effect setup
- Compton scattering geometry
- Electron diffraction patterns
- Spacetime diagrams
- **Place in problem context**

### Use GRAPH for:
- Photoelectric current vs voltage
- KE vs frequency plots
- Energy level diagrams
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{The energy of the incident photon is:}
E &= \\frac{hc}{\\lambda} \\\\
  &= \\frac{6.63 \\times 10^{-34} \\times 3 \\times 10^8}{400 \\times 10^{-9}} \\\\
  &= 4.97 \\times 10^{-19} \\ \\mathrm{J} \\\\
  &= 3.1 \\ \\mathrm{eV}
\\end{align*}

\\begin{align*}
\\intertext{The maximum kinetic energy of ejected electrons is:}
KE_{max} &= E - \\phi \\\\
         &= 3.1 - 2.0 \\\\
         &= 1.1 \\ \\mathrm{eV}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Unit conversion errors**
   - Energy: convert eV to J using $1$ eV $= 1.6 \\times 10^{-19}$ J
   - Wavelength: convert nm to m
   - Frequency: use Hz (not MHz or GHz without conversion)

2. **Photoelectric effect misconceptions**
   - Intensity affects number of electrons, not their energy
   - Frequency determines maximum KE
   - Below threshold: no emission regardless of intensity

3. **Compton formula errors**
   - $\\Delta\\lambda = \\lambda_C(1 - \\cos\\theta)$ (not $\\lambda_C\\cos\\theta$)
   - Maximum shift at $\\theta = 180°$: $\\Delta\\lambda_{max} = 2\\lambda_C$
   - Shift independent of incident wavelength

4. **de Broglie wavelength**
   - $\\lambda = h/p$ where $p = mv$ (not $p = m/v$)
   - For photon: $\\lambda = c/f$ (not $h/f$)
   - Wavelength inversely proportional to momentum

5. **Relativity errors**
   - Time dilation: moving clock runs slower ($\\Delta t > \\Delta t_0$)
   - Length contraction: moving object shorter ($L < L_0$)
   - Use $c = 3 \\times 10^8$ m/s consistently

6. **Energy-momentum confusion**
   - For photon: $E = pc$ (massless)
   - For massive particle: $E^2 = (pc)^2 + (mc^2)^2$
   - Rest energy: $E_0 = mc^2$
"""

# Build system prompts for different question types
SYSTEM_PROMPT_SUBJECTIVE = """You are an expert physics educator solving modern physics problems (photoelectric effect, Compton scattering, de Broglie waves, uncertainty, relativity).

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

SYSTEM_PROMPT_MCQ_SC = """You are an expert physics educator solving modern physics MCQ problems.

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

SYSTEM_PROMPT_MCQ_MC = """You are an expert physics educator solving modern physics MCQ (multiple correct) problems.

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
    """Get modern physics prompt for question type."""
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
