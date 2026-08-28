"""Energy and Work solution generation for physics.

Covers: Work-energy theorem, kinetic energy, potential energy, power, collisions, momentum.
"""

from ..common import build_topic_prompts

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Energy and Work

### Work and Energy
- Work: $W = \\vec{F} \\cdot \\vec{d} = Fd\\cos\\theta$
- Work-energy theorem: $W_{net} = \\Delta KE = \\dfrac{1}{2}m(v_f^2 - v_i^2)$
- Kinetic energy: $KE = \\dfrac{1}{2}mv^2$
- Potential energy (gravity): $PE = mgh$
- Potential energy (spring): $PE = \\dfrac{1}{2}kx^2$
- Power: $P = \\dfrac{W}{t} = \\vec{F} \\cdot \\vec{v}$

### Conservation of Energy
- Mechanical energy: $E = KE + PE$
- Conservative forces: $\\Delta E = 0$ (no friction)
- Non-conservative forces: $W_{nc} = \\Delta E$
- Energy dissipated by friction: $W_f = f \\cdot d = \\mu_k N d$

### Momentum and Collisions
- Momentum: $\\vec{p} = m\\vec{v}$
- Impulse: $\\vec{J} = \\Delta \\vec{p} = \\vec{F}_{avg} \\Delta t$
- Conservation of momentum: $\\sum \\vec{p}_i = \\sum \\vec{p}_f$
- Elastic collision: momentum AND energy conserved
- Inelastic collision: only momentum conserved
- Coefficient of restitution: $e = \\dfrac{v_2 - v_1}{u_1 - u_2}$

### Problem-Solving Strategy
1. Identify system and choose reference level for PE
2. List initial and final energies
3. Identify conservative vs non-conservative forces
4. Apply conservation laws or work-energy theorem
5. Solve for unknown
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Conservation of mechanical energy
1. Choose reference level (usually ground or lowest point)
2. Write $E_i = E_f$ (if no friction)
3. Expand: $KE_i + PE_i = KE_f + PE_f$
4. Substitute values and solve

### Pattern 2: Work-energy with friction
1. Calculate work done by all forces
2. Apply $W_{net} = \\Delta KE$
3. Or use $W_{nc} = \\Delta E = (KE_f + PE_f) - (KE_i + PE_i)$
4. Solve for unknown

### Pattern 3: Collision problems
1. Draw mechanics diagram showing before/after states
2. Apply conservation of momentum: $m_1u_1 + m_2u_2 = m_1v_1 + m_2v_2$
3. For elastic: also apply $\\dfrac{1}{2}m_1u_1^2 + \\dfrac{1}{2}m_2u_2^2 = \\dfrac{1}{2}m_1v_1^2 + \\dfrac{1}{2}m_2v_2^2$
4. Solve system of equations

### Pattern 4: Power problems
1. Identify force and velocity
2. Use $P = Fv\\cos\\theta$ for instantaneous power
3. Or $P = \\dfrac{W}{t}$ for average power
4. Relate to energy changes
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use MECHANICS diagram for:
- Initial and final states of system
- Collision scenarios (before/after)
- Energy level diagrams
- Spring-mass systems
- **Place in problem context**

### Use GRAPH for:
- Energy vs position plots
- Power vs time graphs
- Force vs displacement (work calculation)
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{Using conservation of mechanical energy between initial and final positions:}
E_i &= E_f \\\\
KE_i + PE_i &= KE_f + PE_f \\\\
\\dfrac{1}{2}mv_i^2 + mgh_i &= \\dfrac{1}{2}mv_f^2 + mgh_f
\\end{align*}

\\begin{align*}
\\intertext{Taking ground as reference ($h_f = 0$) and $v_i = 0$:}
mgh_i &= \\dfrac{1}{2}mv_f^2 \\\\
v_f &= \\sqrt{2gh_i} \\\\
    &= \\sqrt{2 \\times 9.8 \\times 5} \\\\
    &= 9.9 \\ \\mathrm{m/s}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Wrong reference level for PE**
   - Choose consistent reference (usually ground)
   - PE can be negative if below reference

2. **Forgetting to account for friction**
   - Friction is non-conservative: energy is lost
   - Use $W_{nc} = \\Delta E$ when friction present

3. **Confusing elastic vs inelastic collisions**
   - Elastic: both momentum and KE conserved
   - Inelastic: only momentum conserved, KE lost
   - Perfectly inelastic: objects stick together

4. **Sign errors in work**
   - Work is positive if force and displacement in same direction
   - Work is negative if opposite (e.g., friction)
   - Use $W = Fd\\cos\\theta$ carefully

5. **Forgetting rotational KE**
   - For rolling objects: $KE_{total} = \\dfrac{1}{2}mv^2 + \\dfrac{1}{2}I\\omega^2$
   - Use $v = r\\omega$ to relate linear and angular

6. **Power vs energy confusion**
   - Power is rate of energy transfer: $P = \\dfrac{dE}{dt}$
   - Energy is integral of power: $E = \\int P \\, dt$
"""

# Build system prompts for different question types
_PROMPTS = build_topic_prompts(
    subjective_intro='You are an expert physics educator solving energy and work problems (work-energy theorem, conservation of energy, power, collisions, momentum).',
    mcq_intro='You are an expert physics educator solving energy and work MCQ problems.',
    mcq_mc_intro='You are an expert physics educator solving energy and work MCQ (multiple correct) problems.',
    topic_concepts=TOPIC_CONCEPTS,
    common_patterns=COMMON_PATTERNS,
    diagram_guidance=DIAGRAM_GUIDANCE,
    typical_mistakes=TYPICAL_MISTAKES,
)

SYSTEM_PROMPT_SUBJECTIVE = _PROMPTS.subjective
SYSTEM_PROMPT_MCQ_SC = _PROMPTS.mcq_sc
SYSTEM_PROMPT_MCQ_MC = _PROMPTS.mcq_mc


def get_prompt(question_type: str) -> str:
    """Get energy/work prompt for question type."""
    return _PROMPTS.for_question_type(question_type)


__all__ = [
    "SYSTEM_PROMPT_SUBJECTIVE",
    "SYSTEM_PROMPT_MCQ_SC",
    "SYSTEM_PROMPT_MCQ_MC",
    "get_prompt",
]
