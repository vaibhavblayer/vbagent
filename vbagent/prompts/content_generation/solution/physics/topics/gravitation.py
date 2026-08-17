"""Gravitation solution generation for physics.

Covers: Universal gravitation, gravitational field, potential, orbits, satellites, Kepler's laws, escape velocity.
"""

from ..common import build_topic_prompts

# Topic-specific guidance
TOPIC_CONCEPTS = """
## Key Concepts for Gravitation

### Newton's Law of Gravitation
- Force: $F = G\\frac{m_1 m_2}{r^2}$ where $G = 6.67 \\times 10^{-11}$ N·m²/kg²
- Gravitational field: $g = \\frac{F}{m} = G\\frac{M}{r^2}$
- At Earth's surface: $g = G\\frac{M_E}{R_E^2} \\approx 9.8$ m/s²
- Variation with height: $g_h = g\\left(\\frac{R_E}{R_E + h}\\right)^2$
- Variation with depth: $g_d = g\\left(1 - \\frac{d}{R_E}\\right)$

### Gravitational Potential Energy
- General: $U = -G\\frac{Mm}{r}$ (taking $U = 0$ at $r = \\infty$)
- Near surface: $U = mgh$ (approximation for small $h$)
- Potential: $V = -G\\frac{M}{r}$
- Relation: $U = mV$

### Orbital Motion
- Orbital speed: $v = \\sqrt{\\frac{GM}{r}}$
- Period: $T = 2\\pi\\sqrt{\\frac{r^3}{GM}}$
- Centripetal force = Gravitational force: $\\frac{mv^2}{r} = G\\frac{Mm}{r^2}$
- Total energy: $E = -\\frac{GMm}{2r}$ (negative for bound orbit)
- Kinetic energy: $KE = \\frac{GMm}{2r}$
- Potential energy: $PE = -\\frac{GMm}{r}$

### Kepler's Laws
- First law: Planets move in elliptical orbits with Sun at one focus
- Second law: Equal areas in equal times (angular momentum conserved)
- Third law: $T^2 \\propto r^3$ or $\\frac{T^2}{r^3} = \\frac{4\\pi^2}{GM}$

### Escape Velocity
- Minimum speed to escape: $v_e = \\sqrt{\\frac{2GM}{R}}$
- At Earth's surface: $v_e = \\sqrt{2gR_E} \\approx 11.2$ km/s
- Independent of mass of escaping object
- Relation to orbital speed: $v_e = \\sqrt{2} v_{orbital}$

### Satellites
- Geostationary orbit: $T = 24$ hours, $r \\approx 42,000$ km from center
- Low Earth orbit: $h \\approx 200-2000$ km
- Energy to launch: $E = \\frac{GMm}{2r} - \\left(-\\frac{GMm}{R_E}\\right)$

### Problem-Solving Strategy
1. Identify masses and distances
2. For orbits: equate gravitational and centripetal forces
3. For energy: use $E = KE + PE$
4. Apply Kepler's third law for period calculations
5. Check units and use consistent values
"""

COMMON_PATTERNS = """
## Common Solution Patterns

### Pattern 1: Orbital speed and period
1. Equate forces: $\\frac{mv^2}{r} = G\\frac{Mm}{r^2}$
2. Solve for speed: $v = \\sqrt{GM/r}$
3. Period: $T = 2\\pi r/v = 2\\pi\\sqrt{r^3/(GM)}$
4. Or use Kepler's third law directly

### Pattern 2: Escape velocity
1. Set total energy to zero: $\\frac{1}{2}mv_e^2 - \\frac{GMm}{R} = 0$
2. Solve: $v_e = \\sqrt{2GM/R}$
3. Or use $v_e = \\sqrt{2gR}$ if $g$ is known

### Pattern 3: Energy in orbit
1. Calculate KE: $KE = \\frac{1}{2}mv^2 = \\frac{GMm}{2r}$
2. Calculate PE: $PE = -\\frac{GMm}{r}$
3. Total: $E = KE + PE = -\\frac{GMm}{2r}$
4. Note: $E$ is negative (bound orbit)

### Pattern 4: Kepler's third law application
1. For two orbits: $\\frac{T_1^2}{r_1^3} = \\frac{T_2^2}{r_2^3}$
2. Solve for unknown period or radius
3. Or use $T^2 = \\frac{4\\pi^2}{GM}r^3$
"""

DIAGRAM_GUIDANCE = """
## When to Use Diagrams

### Use GENERIC diagram for:
- Orbital paths
- Gravitational field lines
- Satellite configurations
- Energy diagrams
- **Place in problem context**

### Use GRAPH for:
- Gravitational field vs distance
- Potential vs distance
- Orbital energy diagrams
- **Can be inline in solution**

### Example structure:
```latex
\\begin{solution}
\\begin{align*}
\\intertext{For a satellite in circular orbit, equating gravitational and centripetal forces:}
\\frac{mv^2}{r} &= G\\frac{Mm}{r^2} \\\\
v^2 &= \\frac{GM}{r}
\\end{align*}

\\begin{align*}
\\intertext{The orbital speed is:}
v &= \\sqrt{\\frac{GM}{r}} \\\\
  &= \\sqrt{\\frac{6.67 \\times 10^{-11} \\times 6 \\times 10^{24}}{6.4 \\times 10^6 + 2 \\times 10^5}} \\\\
  &= 7.8 \\times 10^3 \\ \\mathrm{m/s} \\\\
  &= 7.8 \\ \\mathrm{km/s}
\\end{align*}
\\end{solution}
```
"""

TYPICAL_MISTAKES = """
## Common Mistakes to Avoid

1. **Sign of gravitational PE**
   - Correct: $U = -GMm/r$ (negative)
   - Taking $U = 0$ at infinity is standard convention
   - PE increases (becomes less negative) as $r$ increases

2. **Orbital energy relations**
   - Total energy: $E = -GMm/(2r)$ (half of PE)
   - $KE = -E$ (kinetic energy equals negative of total energy)
   - $PE = 2E$ (potential energy is twice total energy)

3. **Escape velocity confusion**
   - $v_e = \\sqrt{2GM/R}$ (not $\\sqrt{GM/R}$)
   - Factor of $\\sqrt{2}$ compared to orbital speed
   - Independent of mass of escaping object

4. **Kepler's third law**
   - $T^2 \\propto r^3$ (not $T \\propto r$)
   - $r$ is distance from center, not from surface
   - Valid for all objects orbiting same central body

5. **Variation of g**
   - With height: $g_h = g(R_E/(R_E + h))^2$ (inverse square)
   - With depth: $g_d = g(1 - d/R_E)$ (linear decrease)
   - At center: $g = 0$

6. **Geostationary orbit**
   - Period must be exactly 24 hours
   - Must be in equatorial plane
   - Specific radius: $r \\approx 42,000$ km from center
   - Height above surface: $h \\approx 36,000$ km
"""

# Build system prompts for different question types
_PROMPTS = build_topic_prompts(
    subjective_intro="You are an expert physics educator solving gravitation problems (universal gravitation, orbits, satellites, Kepler's laws, escape velocity).",
    mcq_intro='You are an expert physics educator solving gravitation MCQ problems.',
    mcq_mc_intro='You are an expert physics educator solving gravitation MCQ (multiple correct) problems.',
    topic_concepts=TOPIC_CONCEPTS,
    common_patterns=COMMON_PATTERNS,
    diagram_guidance=DIAGRAM_GUIDANCE,
    typical_mistakes=TYPICAL_MISTAKES,
)

SYSTEM_PROMPT_SUBJECTIVE = _PROMPTS.subjective
SYSTEM_PROMPT_MCQ_SC = _PROMPTS.mcq_sc
SYSTEM_PROMPT_MCQ_MC = _PROMPTS.mcq_mc


def get_prompt(question_type: str) -> str:
    """Get gravitation prompt for question type."""
    return _PROMPTS.for_question_type(question_type)


__all__ = [
    "SYSTEM_PROMPT_SUBJECTIVE",
    "SYSTEM_PROMPT_MCQ_SC",
    "SYSTEM_PROMPT_MCQ_MC",
    "get_prompt",
]
