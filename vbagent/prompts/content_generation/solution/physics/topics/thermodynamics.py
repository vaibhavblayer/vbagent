"""Thermodynamics solution generation for physics.

Covers: Laws of thermodynamics, PV diagrams, thermodynamic processes, cycles, entropy, efficiency.
"""

from ..common import build_topic_prompts

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Thermodynamics

### Laws of Thermodynamics
- Zeroth law: Thermal equilibrium is transitive
- First law: $\\Delta U = Q - W$ (energy conservation)
- Second law: Entropy of isolated system never decreases
- Third law: Entropy approaches zero as $T \\to 0$ K

### Thermodynamic Processes
- Isothermal: $\\Delta T = 0$, $\\Delta U = 0$, $Q = W = nRT\\ln\\dfrac{V_f}{V_i}$
- Adiabatic: $Q = 0$, $\\Delta U = -W$, $TV^{\\gamma-1} = const$, $PV^\\gamma = const$
- Isochoric: $\\Delta V = 0$, $W = 0$, $Q = \\Delta U = nC_V\\Delta T$
- Isobaric: $\\Delta P = 0$, $W = P\\Delta V$, $Q = nC_P\\Delta T$
- Free expansion: $Q = 0$, $W = 0$, $\\Delta U = 0$

### Ideal Gas Relations
- Equation of state: $PV = nRT$
- Internal energy: $U = nC_VT$ (ideal gas)
- Molar heat capacities: $C_P - C_V = R$
- Ratio: $\\gamma = \\dfrac{C_P}{C_V}$ (monoatomic: 5/3, diatomic: 7/5)

### Work and Heat
- Work done by gas: $W = \\int P \\, dV$
- For constant pressure: $W = P\\Delta V$
- For isothermal: $W = nRT\\ln\\dfrac{V_f}{V_i}$
- For adiabatic: $W = \\dfrac{nR(T_i - T_f)}{\\gamma - 1}$

### Heat Engines and Cycles
- Efficiency: $\\eta = \\dfrac{W_{net}}{Q_H} = 1 - \\dfrac{Q_C}{Q_H}$
- Carnot efficiency: $\\eta_C = 1 - \\dfrac{T_C}{T_H}$ (maximum possible)
- Coefficient of performance (refrigerator): $K = \\dfrac{Q_C}{W}$
- Coefficient of performance (heat pump): $K = \\dfrac{Q_H}{W}$

### Entropy
- Change in entropy: $\\Delta S = \\int \\dfrac{dQ}{T}$
- For reversible process: $\\Delta S = \\dfrac{Q}{T}$
- For isothermal: $\\Delta S = nR\\ln\\dfrac{V_f}{V_i}$
- Second law: $\\Delta S_{universe} \\geq 0$

### Problem-Solving Strategy
1. Identify process type (isothermal, adiabatic, etc.)
2. List initial and final states
3. Apply appropriate relations for process
4. Calculate $Q$, $W$, $\\Delta U$ using first law
5. For cycles: calculate net work and efficiency
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Single process calculation
1. Identify process type
2. Use ideal gas law to relate states: $\\dfrac{P_1V_1}{T_1} = \\dfrac{P_2V_2}{T_2}$
3. Apply process-specific relation (e.g., $PV^\\gamma = const$ for adiabatic)
4. Calculate $W$, $Q$, $\\Delta U$ using first law

### Pattern 2: Cyclic process
1. Draw PV diagram showing cycle
2. Calculate work for each leg of cycle
3. Net work: $W_{net} = \\oint P \\, dV$ (area enclosed)
4. Calculate heat absorbed and rejected
5. Efficiency: $\\eta = W_{net}/Q_H$

### Pattern 3: Carnot cycle
1. Identify hot and cold reservoir temperatures
2. Calculate Carnot efficiency: $\\eta_C = 1 - T_C/T_H$
3. If work or heat given, use $\\eta = W/Q_H$
4. Calculate other quantities

### Pattern 4: Adiabatic process
1. Use $PV^\\gamma = const$ or $TV^{\\gamma-1} = const$
2. Find final state from initial state
3. Calculate work: $W = \\dfrac{nR(T_i - T_f)}{\\gamma - 1}$
4. $Q = 0$, $\\Delta U = -W$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GRAPH for:
- PV diagrams showing processes and cycles
- TS diagrams (temperature-entropy)
- Indicator diagrams
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For an isothermal expansion, the work done is:}
W &= nRT\\ln\\dfrac{V_f}{V_i} \\\\
  &= 2 \\times 8.314 \\times 300 \\times \\ln\\dfrac{2V_i}{V_i} \\\\
  &= 2 \\times 8.314 \\times 300 \\times \\ln 2 \\\\
  &= 3458 \\ \\mathrm{J}
\\end{align*}

\\begin{align*}
\\intertext{Since the process is isothermal, $\\Delta U = 0$, so:}
Q &= W = 3458 \\ \\mathrm{J}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Sign convention errors**
   - Heat absorbed by system: $Q > 0$
   - Work done by system: $W > 0$
   - First law: $\\Delta U = Q - W$ (not $Q + W$)

2. **Confusing process types**
   - Isothermal: constant temperature, $\\Delta U = 0$
   - Adiabatic: no heat transfer, $Q = 0$
   - Isochoric: constant volume, $W = 0$
   - Isobaric: constant pressure

3. **Wrong heat capacity**
   - Constant volume: use $C_V$
   - Constant pressure: use $C_P$
   - Remember: $C_P = C_V + R$

4. **Adiabatic relation errors**
   - Use $PV^\\gamma = const$, not $PV = const$
   - $\\gamma = C_P/C_V$ depends on gas type
   - Monoatomic: $\\gamma = 5/3$, diatomic: $\\gamma = 7/5$

5. **Efficiency confusion**
   - Efficiency: $\\eta = W/Q_H$ (not $W/Q_C$)
   - Carnot: $\\eta_C = 1 - T_C/T_H$ (temperatures in Kelvin!)
   - Real engine efficiency always less than Carnot

6. **Cyclic process errors**
   - Net work = area enclosed in PV diagram
   - For clockwise cycle: $W_{net} > 0$ (engine)
   - For counterclockwise: $W_{net} < 0$ (refrigerator)
"""

# Build system prompts for different question types
_PROMPTS = build_topic_prompts(
    subjective_intro='You are an expert physics educator solving thermodynamics problems (laws, processes, cycles, entropy, efficiency).',
    mcq_intro='You are an expert physics educator solving thermodynamics MCQ problems.',
    mcq_mc_intro='You are an expert physics educator solving thermodynamics MCQ (multiple correct) problems.',
    topic_concepts=TOPIC_CONCEPTS,
    common_patterns=COMMON_PATTERNS,
    diagram_guidance=DIAGRAM_GUIDANCE,
    typical_mistakes=TYPICAL_MISTAKES,
)

SYSTEM_PROMPT_SUBJECTIVE = _PROMPTS.subjective
SYSTEM_PROMPT_MCQ_SC = _PROMPTS.mcq_sc
SYSTEM_PROMPT_MCQ_MC = _PROMPTS.mcq_mc


def get_prompt(question_type: str) -> str:
    """Get thermodynamics prompt for question type."""
    return _PROMPTS.for_question_type(question_type)


__all__ = [
    "SYSTEM_PROMPT_SUBJECTIVE",
    "SYSTEM_PROMPT_MCQ_SC",
    "SYSTEM_PROMPT_MCQ_MC",
    "get_prompt",
]
