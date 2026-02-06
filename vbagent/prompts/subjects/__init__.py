"""Subject-specific prompt components.

Each subject has different:
- LaTeX packages (chemfig, mhchem for chemistry; tikz for physics)
- Example problems and solutions
- Topic taxonomies
- Expert terminology

Usage:
    from vbagent.prompts.subjects import get_subject_config, SUBJECTS
    
    config = get_subject_config("chemistry")
    print(config.packages)  # ['chemfig', 'mhchem', ...]
    print(config.expert_role)  # "expert chemist"
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SubjectConfig:
    """Configuration for a specific subject."""
    
    name: str
    display_name: str
    expert_role: str  # "expert physicist", "expert chemist"
    
    # LaTeX packages required
    packages: list[str] = field(default_factory=list)
    package_instructions: str = ""
    
    # Topics for classification
    topics: list[str] = field(default_factory=list)
    
    # Diagram types
    diagram_types: list[str] = field(default_factory=list)
    diagram_instructions: str = ""
    
    # Example problem (for few-shot prompting)
    example_problem: str = ""
    example_solution: str = ""
    
    # Subject-specific formatting rules
    formatting_rules: str = ""


# Physics configuration
PHYSICS_CONFIG = SubjectConfig(
    name="physics",
    display_name="Physics",
    expert_role="expert physicist and skilled LaTeX typesetter",
    packages=["tikz", "pgfplots", "tzplot", "kinematikz"],
    package_instructions=r"""
**Required LaTeX Packages:**
- `tikz` with libraries: calc, decorations.pathmorphing, patterns, arrows.meta, positioning
- `pgfplots` for graphs and data plots
- `tzplot` for simplified TikZ plotting (coordinates, curves, angles)
- `kinematikz` for mechanical diagrams (frames, supports, pivots)

**TikZ Libraries to use:**
```latex
\usetikzlibrary{calc, decorations.pathmorphing, patterns, arrows.meta, positioning, shapes.geometric}
```
""",
    topics=[
        "kinematics", "dynamics", "work_energy", "momentum",
        "rotational_motion", "gravitation", "oscillations", "waves",
        "thermodynamics", "kinetic_theory", "electrostatics",
        "current_electricity", "magnetism", "electromagnetic_induction",
        "alternating_current", "optics", "modern_physics", "semiconductors"
    ],
    diagram_types=["graph", "circuit", "free_body", "geometry", "ray_diagram", "wave"],
    diagram_instructions=r"""
**TikZ for Physics Diagrams:**
- Use `kinematikz` for frames, supports, pivots: `\pic (name) {frame=2cm};`
- Springs: `spring/.style={decorate, decoration={coil, amplitude=4pt, segment length=4.5pt}}`
- Circuits: Use `circuitikz` package for electrical components
- Free body diagrams: Use arrows with `\draw[->, thick]` for force vectors
- Use `tzplot` for quick coordinate plots: `\tzto(0,0)(3,2)`
""",
    example_problem=r"""\item A ball of mass $m = 2 \ \mathrm{kg}$ is thrown vertically upward with initial velocity $v_0 = 20 \ \mathrm{m/s}$. Find the maximum height reached. (Take $g = 10 \ \mathrm{m/s^2}$)""",
    example_solution=r"""\begin{solution}
\begin{align*}
    v^2 &= v_0^2 - 2gh \\
    \intertext{At maximum height, $v = 0$:}
    0 &= (20)^2 - 2(10)h \\
    h &= \frac{400}{20} = 20 \ \mathrm{m}
\end{align*}
\end{solution}""",
    formatting_rules=r"""
**Physics Formatting:**
- Use `\vec{a}` for vectors, `\hat{i}`, `\hat{j}`, `\hat{k}` for unit vectors
- Use `\mathrm{...}` for units: `20 \ \mathrm{m/s}`, `5 \ \mathrm{kg}`, `10 \ \mathrm{N}`
- Use `^\circ` for degrees: `30^\circ`, `\theta = 45^\circ`
- Use `\frac{a}{b}` for fractions (not `\tfrac`)
- Do NOT use `\SI{}{}` or siunitx package - use `\mathrm{}` instead
"""
)


# Chemistry configuration
CHEMISTRY_CONFIG = SubjectConfig(
    name="chemistry",
    display_name="Chemistry",
    expert_role="expert chemist and skilled LaTeX typesetter",
    packages=["chemfig", "mhchem", "chemmacros", "tikz"],
    package_instructions=r"""
**Required LaTeX Packages:**
- `mhchem` for chemical equations: `\ce{H2O}`, `\ce{2H2 + O2 -> 2H2O}`
- `chemfig` for structural formulas and reaction mechanisms
- `chemmacros` for IUPAC nomenclature and chemical symbols
- `tikz` for orbital diagrams and energy level diagrams

**TikZ Libraries:**
```latex
\usetikzlibrary{calc, arrows.meta, positioning, shapes.geometric}
```
""",
    topics=[
        "atomic_structure", "chemical_bonding", "states_of_matter",
        "thermodynamics", "equilibrium", "ionic_equilibrium",
        "redox_reactions", "electrochemistry", "chemical_kinetics",
        "surface_chemistry", "coordination_compounds", "organic_chemistry",
        "polymers", "biomolecules", "chemistry_in_everyday_life",
        "s_block", "p_block", "d_block", "f_block", "metallurgy"
    ],
    diagram_types=["structure", "mechanism", "orbital", "graph", "apparatus"],
    diagram_instructions=r"""
**Chemistry Diagrams:**
- Structural formulas: Use `chemfig` package
  ```latex
  \chemfig{H-C(-[2]H)(-[6]H)-C(-[2]H)(-[6]H)-H}  % Ethane
  ```
- Reaction mechanisms: Use `chemfig` with arrows
  ```latex
  \schemestart
  \chemfig{R-X} \arrow{->[\ce{Nu^-}]} \chemfig{R-Nu}
  \schemestop
  ```
- Orbital diagrams: Use TikZ with boxes and arrows
- Energy diagrams: Use `pgfplots` or TikZ
""",
    example_problem=r"""\item Balance the following redox reaction in acidic medium:
\ce{MnO4^- + Fe^{2+} -> Mn^{2+} + Fe^{3+}}""",
    example_solution=r"""\begin{solution}
\begin{align*}
    \intertext{Oxidation half-reaction:}
    \ce{Fe^{2+} &-> Fe^{3+} + e^-} \\
    \intertext{Reduction half-reaction:}
    \ce{MnO4^- + 8H^+ + 5e^- &-> Mn^{2+} + 4H2O} \\
    \intertext{Balancing electrons (multiply oxidation by 5):}
    \ce{5Fe^{2+} &-> 5Fe^{3+} + 5e^-} \\
    \intertext{Adding both half-reactions:}
    \ce{MnO4^- + 8H^+ + 5Fe^{2+} &-> Mn^{2+} + 5Fe^{3+} + 4H2O}
\end{align*}
\end{solution}""",
    formatting_rules=r"""
**Chemistry Formatting:**
- Use `\ce{...}` for all chemical formulas and equations
- Use `\chemfig{...}` for structural formulas
- Subscripts in formulas: `\ce{H2SO4}` (not `H_2SO_4`)
- Reaction arrows: `\ce{->}`, `\ce{<=>}`, `\ce{<<=>}` for equilibrium
- State symbols: `\ce{(s)}`, `\ce{(l)}`, `\ce{(g)}`, `\ce{(aq)}`
- Use `\mathrm{...}` for units: `25 \ \mathrm{kJ/mol}`, `0.1 \ \mathrm{M}`
- Use `^\circ` for degrees: `25^\circ \mathrm{C}`, `100^\circ \mathrm{C}`
"""
)


# Mathematics configuration
MATHEMATICS_CONFIG = SubjectConfig(
    name="mathematics",
    display_name="Mathematics",
    expert_role="expert mathematician and skilled LaTeX typesetter",
    packages=["amsmath", "amssymb", "amsthm", "tikz", "pgfplots", "tzplot"],
    package_instructions=r"""
**Required LaTeX Packages:**
- `amsmath` for advanced math environments
- `amssymb` for mathematical symbols
- `amsthm` for theorem environments
- `tikz` for geometric figures
- `pgfplots` for function graphs
- `tzplot` for simplified coordinate plotting

**TikZ Libraries:**
```latex
\usetikzlibrary{calc, arrows.meta, positioning, intersections, angles, quotes}
```
""",
    topics=[
        "sets_relations_functions", "complex_numbers", "quadratic_equations",
        "sequences_series", "permutations_combinations", "binomial_theorem",
        "matrices_determinants", "limits_continuity", "differentiation",
        "integration", "differential_equations", "coordinate_geometry",
        "straight_lines", "circles", "conics", "vectors_3d",
        "probability", "statistics", "trigonometry", "inverse_trigonometry"
    ],
    diagram_types=["graph", "geometry", "coordinate", "venn_diagram"],
    diagram_instructions=r"""
**Mathematics Diagrams:**
- Function graphs: Use `pgfplots` with `axis` environment or `tzplot`
- Geometric figures: Use TikZ with coordinate calculations
- Coordinate geometry: Use TikZ with grid and axes
- Venn diagrams: Use TikZ with circles and labels
- Use `tzplot` for quick plots: `\tzaxes(-1,-1)(5,5)` `\tzfn{sin(\x)}[0:2*pi]`
""",
    example_problem=r"""\item Evaluate: $\displaystyle\int_0^{\pi/2} \frac{\sin x}{\sin x + \cos x} \, dx$""",
    example_solution=r"""\begin{solution}
\begin{align*}
    I &= \int_0^{\pi/2} \frac{\sin x}{\sin x + \cos x} \, dx \\
    \intertext{Using property: $\int_0^a f(x)\,dx = \int_0^a f(a-x)\,dx$}
    I &= \int_0^{\pi/2} \frac{\cos x}{\cos x + \sin x} \, dx \\
    \intertext{Adding both:}
    2I &= \int_0^{\pi/2} \frac{\sin x + \cos x}{\sin x + \cos x} \, dx = \int_0^{\pi/2} 1 \, dx = \frac{\pi}{2} \\
    I &= \frac{\pi}{4}
\end{align*}
\end{solution}""",
    formatting_rules=r"""
**Mathematics Formatting:**
- Use `\displaystyle` for inline fractions and integrals
- Use `\left( ... \right)` for auto-sizing brackets
- Use `\mathbb{R}`, `\mathbb{N}`, `\mathbb{Z}` for number sets
- Use `\therefore` for "therefore", `\because` for "because"
- Use `\mathrm{...}` for text in math: `\mathrm{cm}`, `\mathrm{units}`
- Use `^\circ` for degrees: `90^\circ`, `\angle ABC = 60^\circ`
"""
)


# Biology configuration
BIOLOGY_CONFIG = SubjectConfig(
    name="biology",
    display_name="Biology",
    expert_role="expert biologist and skilled LaTeX typesetter",
    packages=["tikz", "pgfplots"],
    package_instructions=r"""
**Required LaTeX Packages:**
- `tikz` for diagrams (cell structures, flowcharts)
- `pgfplots` for graphs (population curves, enzyme kinetics)

**TikZ Libraries:**
```latex
\usetikzlibrary{calc, arrows.meta, positioning, shapes.geometric, decorations.pathmorphing}
```
""",
    topics=[
        "cell_biology", "biomolecules", "cell_division", "genetics",
        "molecular_biology", "evolution", "classification", "plant_kingdom",
        "animal_kingdom", "morphology_flowering_plants", "anatomy_flowering_plants",
        "structural_organization_animals", "digestion_absorption",
        "breathing_exchange_gases", "body_fluids_circulation",
        "excretory_products", "locomotion_movement", "neural_control",
        "chemical_coordination", "reproduction_organisms",
        "human_reproduction", "reproductive_health", "heredity_variation",
        "molecular_basis_inheritance", "biotechnology", "ecology"
    ],
    diagram_types=["flowchart", "structure", "graph", "cycle"],
    diagram_instructions=r"""
**Biology Diagrams:**
- Cell structures: Use TikZ with shapes and labels
- Flowcharts: Use TikZ with nodes and arrows
- Graphs (population, enzyme kinetics): Use pgfplots
- Cycles (Krebs, Calvin): Use TikZ with circular arrangements
""",
    example_problem=r"""\item Describe the process of DNA replication. Explain why it is called semi-conservative.""",
    example_solution=r"""\begin{solution}
DNA replication is semi-conservative because each new DNA molecule contains one original (parental) strand and one newly synthesized strand.

\textbf{Steps:}
\begin{enumerate}
    \item \textbf{Initiation:} Helicase unwinds the double helix at the origin of replication.
    \item \textbf{Elongation:} DNA polymerase III synthesizes new strands in 5' to 3' direction.
    \item \textbf{Termination:} Replication forks meet and DNA ligase joins Okazaki fragments.
\end{enumerate}

Meselson and Stahl (1958) experimentally proved semi-conservative replication using $^{15}$N-labeled DNA.
\end{solution}""",
    formatting_rules=r"""
**Biology Formatting:**
- Use `\textbf{...}` for key terms
- Use `enumerate` for sequential steps
- Use `itemize` for lists of features
- Scientific names in italics: \textit{Homo sapiens}
- Use `\mathrm{...}` for units: `0.9\% \ \mathrm{NaCl}`
- Use `^\circ` for temperature: `37^\circ \mathrm{C}`, `4^\circ \mathrm{C}`
"""
)


# Subject registry
SUBJECT_CONFIGS: dict[str, SubjectConfig] = {
    "physics": PHYSICS_CONFIG,
    "chemistry": CHEMISTRY_CONFIG,
    "mathematics": MATHEMATICS_CONFIG,
    "biology": BIOLOGY_CONFIG,
}

SUBJECTS = list(SUBJECT_CONFIGS.keys())


def get_subject_config(subject: str) -> SubjectConfig:
    """Get configuration for a subject.
    
    Args:
        subject: Subject name (physics, chemistry, mathematics, biology)
        
    Returns:
        SubjectConfig for the subject
        
    Raises:
        ValueError: If subject is not recognized
    """
    if subject not in SUBJECT_CONFIGS:
        raise ValueError(f"Unknown subject: {subject}. Valid: {SUBJECTS}")
    return SUBJECT_CONFIGS[subject]


__all__ = [
    "SubjectConfig",
    "get_subject_config",
    "SUBJECTS",
    "SUBJECT_CONFIGS",
    "PHYSICS_CONFIG",
    "CHEMISTRY_CONFIG", 
    "MATHEMATICS_CONFIG",
    "BIOLOGY_CONFIG",
]
