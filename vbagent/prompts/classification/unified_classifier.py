"""Prompt for the unified classifier agent.

Single API call that handles both classification and diagram analysis.
"""


def _get_valid_types(subject: str) -> str:
    """Get valid diagram types for a subject."""
    types = {
        "physics": "fbd, circuit, graph, optics",
        "chemistry": "organic_structure, reaction_mechanism, chemical_equation, energy_diagram, orbital, lewis_structure",
        "mathematics": "number_line, function_graph, coordinate_geometry, geometric_figure, venn_diagram",
    }
    return types.get(subject, "generic")


def _get_suggested_agents(subject: str) -> str:
    """Get valid suggested_tikz_agent values for a subject."""
    agents = {
        "physics": '"fbd", "circuit", "graph", "optics", "generic"',
        "chemistry": '"organic_structure", "reaction_mechanism", "chemical_equation", "energy_diagram", "orbital", "lewis_structure", "generic"',
        "mathematics": '"number_line", "function_graph", "coordinate_geometry", "geometric_figure", "venn_diagram", "generic"',
    }
    return agents.get(subject, '"generic"')


def _get_agent_routing_guide(subject: str) -> str:
    """Get detailed agent routing guide for a subject."""
    guides = {
        "physics": """
suggested_tikz_agent selection guide (CRITICAL — pick the MOST SPECIFIC agent):

"circuit" — ANY diagram with electrical components. This includes:
  • Resistors, capacitors, inductors, batteries, EMF sources, ammeters, voltmeters
  • Wheatstone bridge, potentiometer, meter bridge
  • Electromagnetic induction: rails on magnetic field, sliding rod on rails, coils with changing flux
  • RC/RL/RLC circuits, AC circuits, transformers
  • ANY diagram drawn with CircuiTikZ components
  • If you see wires connecting components → "circuit"

"fbd" — Free body diagrams and force/mechanics setups:
  • Blocks on surfaces, inclined planes, pulleys, springs, strings
  • Collision setups, projectile trajectories, rotational mechanics setups
  • Fluid mechanics containers, pressure diagrams
  • Gravitational field diagrams (orbits, satellites)
  • ANY setup showing physical objects with forces, tensions, or constraints

"graph" — Plots, charts, and data visualizations:
  • v-t, x-t, a-t, F-t, P-V, T-S graphs
  • Phase diagrams, I-V characteristics
  • ANY axes with plotted curves or data points
  • Waveforms (sinusoidal, square, etc.)

"optics" — Ray diagrams and optical setups:
  • Lenses (convex, concave), mirrors, prisms
  • Ray tracing, image formation
  • Interference/diffraction setups (slits, screens)
  • Optical instruments (microscope, telescope)

"generic" — ONLY when the diagram truly doesn't fit any above category:
  • Simple geometric sketches with no physics components
  • Decorative or non-essential diagrams
  • Avoid "generic" if ANY specific agent applies""",

        "chemistry": """
suggested_tikz_agent selection guide (CRITICAL — pick the MOST SPECIFIC agent):

"organic_structure" — Molecular structures drawn with chemfig:
  • Skeletal structures, Newman projections, Fischer projections
  • Benzene rings, heterocycles, functional groups
  • ANY molecule that needs chemfig rendering

"reaction_mechanism" — Curved arrow mechanisms:
  • SN1, SN2, E1, E2 mechanisms
  • Nucleophilic/electrophilic additions
  • Rearrangements with electron flow arrows

"chemical_equation" — Balanced equations and reaction schemes:
  • Stoichiometric equations, ionic equations
  • Multi-step synthesis schemes (schemestart/schemestop)
  • Reaction conditions above/below arrows

"energy_diagram" — Energy level and thermodynamic diagrams:
  • Reaction coordinate diagrams, activation energy
  • Born-Haber cycles, Hess's law diagrams
  • Potential energy curves

"orbital" — Electron configuration and orbital diagrams:
  • Aufbau filling diagrams, MO diagrams
  • Hybridization diagrams, band theory
  • Crystal field splitting

"lewis_structure" — Lewis dot structures:
  • Electron dot diagrams with lone pairs
  • Formal charges, resonance structures

"generic" — ONLY when nothing above fits""",

        "mathematics": """
suggested_tikz_agent selection guide (CRITICAL — pick the MOST SPECIFIC agent):

"coordinate_geometry" — Coordinate plane with geometric objects:
  • Lines, circles, parabolas, ellipses, hyperbolas
  • Tangent/normal lines to curves
  • Locus problems, conic sections
  • ANY diagram on x-y axes showing geometric shapes

"geometric_figure" — Pure geometry without coordinate axes:
  • Triangles, quadrilaterals, polygons
  • Circles with inscribed/circumscribed figures
  • Angle bisectors, medians, altitudes
  • 3D geometry projections

"function_graph" — Function plots and calculus:
  • y = f(x) curves, piecewise functions
  • Area under curves, tangent lines
  • Derivative/integral visualizations

"number_line" — Number lines and intervals:
  • Solution sets, inequalities
  • Absolute value representations

"venn_diagram" — Set theory diagrams:
  • Union, intersection, complement
  • Probability Venn diagrams

"generic" — ONLY when nothing above fits""",
    }
    return guides.get(subject, '"generic" for all diagrams')



def get_unified_classifier_prompt(subject: str = "physics") -> str:
    """Build the unified classifier prompt that handles both classification and diagram analysis."""
    valid_types = _get_valid_types(subject)
    suggested_agents = _get_suggested_agents(subject)
    agent_guide = _get_agent_routing_guide(subject)

    return f"""You are an expert {subject} question analyzer. In a SINGLE pass, classify the question AND analyze any diagrams present.

Respond with ONLY a valid JSON object:

{{
    "subject": "physics" | "chemistry" | "mathematics" | "biology",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "confidence": <0.0-1.0>,

    "diagram_type": "<one of: {valid_types}, or null if no diagram>",
    "diagram_category": "mechanics" | "kinematics" | "circuits" | "optics" | "waves" | "thermodynamics" | "organic" | "inorganic" | "graphs" | "geometry" | "none",
    "diagram_complexity": "simple" | "moderate" | "complex",
    "diagram_elements": ["<element1>", "<element2>"],
    "diagram_features": {{
        "has_labels": true | false,
        "has_measurements": true | false,
        "has_vectors": true | false,
        "has_grid": true | false,
        "coordinate_system": "cartesian" | "polar" | null,
        "num_objects": <count>
    }},
    "suggested_tikz_agent": {suggested_agents},

    "has_option_diagrams": true | false,
    "num_option_diagrams": <0-4>,
    "option_diagram_type": "<diagram type for options or empty string>",
    "option_diagram_descriptions": ["<desc A>", "<desc B>", ...]
}}

Question type detection:
- mcq_sc: Single correct MCQ
- mcq_mc: Multiple correct MCQ (look for "one or more", "which of the following is/are")
- subjective: Open-ended, numerical answer, derivation
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing same context/passage/graph
- match: Match the following (two columns)

Diagram analysis rules:
- If has_diagram is false, set diagram fields to null/empty
- Analyze ONLY the PROBLEM section diagrams, IGNORE solution diagrams
- diagram_type MUST be exactly one of: {valid_types}
- Check if MCQ options contain diagrams (structures, graphs, circuits in options)
- suggested_tikz_agent MUST match diagram_type — do NOT default to "generic" unless the diagram truly fits no specialist

Common diagram_type corrections:
- "reaction_scheme" → "reaction_mechanism"
- "free_body" → "fbd"
- "ray_diagram" → "optics"
- "geometry" → "geometric_figure"
- "molecular_structure" → "organic_structure"

CRITICAL topic → diagram_type mappings (physics):
- Electromagnetic induction (rails, sliding rods, coils, flux) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Current electricity (resistors, batteries, Kirchhoff) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- AC circuits (RLC, impedance, phasor) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Electrostatics with capacitors → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Mechanics (blocks, pulleys, inclines, springs) → diagram_type: "fbd", suggested_tikz_agent: "fbd"
- Kinematics graphs (v-t, x-t, a-t) → diagram_type: "graph", suggested_tikz_agent: "graph"
- Thermodynamics graphs (P-V, T-S) → diagram_type: "graph", suggested_tikz_agent: "graph"
- Ray optics (lenses, mirrors, prisms) → diagram_type: "optics", suggested_tikz_agent: "optics"
- Wave optics (slits, interference) → diagram_type: "optics", suggested_tikz_agent: "optics"
{agent_guide}

Respond with ONLY the JSON object."""
