"""Prompt for the unified classifier agent.

Single API call that handles both classification and diagram analysis.
"""

from vbagent.prompts.classification.taxonomy import get_chapters, SUBJECT_TAXONOMY


def _get_valid_types(subject: str) -> str:
    """Get valid diagram types for a subject."""
    types = {
        "physics": "circuit, gates, graph, optics, mechanics, wave, fbd",
        "chemistry": "organic_structure, reaction_mechanism, chemical_equation, energy_diagram, orbital, lewis_structure",
        "mathematics": "number_line, function_graph, coordinate_geometry, geometric_figure, venn_diagram",
    }
    return types.get(subject, "generic")


def _get_chapter_topic_guide(subject: str) -> str:
    """Build a compact chapter → topics reference for the prompt."""
    taxonomy = SUBJECT_TAXONOMY.get(subject, {})
    if not taxonomy:
        return ""
    lines = []
    for chapter, topics in taxonomy.items():
        topic_str = ", ".join(topics[:6])
        if len(topics) > 6:
            topic_str += f" (+{len(topics)-6} more)"
        lines.append(f'  "{chapter}": [{topic_str}]')
    return "\n".join(lines)


def _get_suggested_agents(subject: str) -> str:
    """Get valid suggested_tikz_agent values for a subject."""
    agents = {
        "physics": '"circuit", "gates", "graph", "optics", "mechanics", "wave", "fbd", "generic"',
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
  • NOTE: If the diagram has ONLY logic gates (AND, OR, NOT, NAND, NOR, XOR), use "gates" instead

"gates" — Digital logic gate circuits:
  • AND, OR, NOT, NAND, NOR, XOR, XNOR gates
  • Combinational circuits (half adder, full adder, multiplexer, decoder)
  • Boolean algebra circuit implementations
  • Flip-flops, latches, sequential logic
  • If you see gate symbols with inputs A, B and output Y → "gates"
  • NOT for analog circuits with resistors/capacitors — those are "circuit"

"mechanics" — Physical system setups (USE THIS FOR MOST MECHANICS PROBLEMS):
  • Pulley systems (single, double, Atwood machine, movable pulleys)
  • Spring-mass systems (horizontal, vertical, SHM, oscillations)
  • Blocks on inclined planes, connected blocks
  • Rotational systems (rotating disks, torque on rods, pivots)
  • Circular motion with particles on paths
  • Projectile trajectories, kinematics diagrams
  • Work-energy scenarios with objects in motion
  • ANY diagram showing the PHYSICAL SETUP of a mechanical system
  • If you see pulleys, springs, ropes, supports, paths, or system arrangement → "mechanics"

"fbd" — Free body diagrams (RARE — mostly for solution diagrams):
  • ONLY use if diagram shows an ISOLATED body with ONLY force arrows
  • NO physical system elements (no pulleys, springs, supports, paths)
  • Body is a simple dot or box with force vectors
  • Typically appears in SOLUTION sections, NOT main problems
  • When in doubt between "fbd" and "mechanics" → choose "mechanics"

"graph" — Plots, charts, and data visualizations:
  • v-t, x-t, a-t, F-t, P-V, T-S graphs
  • Phase diagrams, I-V characteristics
  • ANY axes with plotted curves or data points
  • Waveforms (sinusoidal, square, etc.)

"optics" — Ray diagrams and optical setups:
  • Lenses (convex, concave), mirrors, prisms
  • Ray tracing, image formation
  • Interference/diffraction setups (Young's double slit, diffraction grating)
  • Optical instruments (microscope, telescope)

"wave" — Wave propagation and wave mechanics:
  • Traveling waves, wave pulses, sinusoidal waves
  • Reflection at boundaries (fixed end, free end, phase changes)
  • Transmission at medium boundaries (denser to rarer)
  • Standing waves on strings and in pipes (nodes, antinodes, harmonics)
  • Superposition and interference of waves
  • Wave properties (wavelength, amplitude, frequency, phase)
  • Doppler effect and wave fronts
  • NOTE: Use "wave" for wave propagation/reflection/transmission; use "optics" for ray tracing with lenses/mirrors

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
    chapter_topic_guide = _get_chapter_topic_guide(subject)

    return f"""You are an expert {subject} question analyzer. In a SINGLE pass, classify the question AND analyze any diagrams present.

Respond with ONLY a valid JSON object:

{{
    "subject": "physics" | "chemistry" | "mathematics" | "biology",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "confidence": <0.0-1.0>,

    "chapter": "<chapter name from the taxonomy below>",
    "topic": "<topic name from the taxonomy below>",

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
- Truth tables are NOT diagrams — they are plain LaTeX tables (tabular environment). If the ONLY visual element is a truth table, set has_diagram=false. The scanner will extract it as a tabular. Only set has_diagram=true if there is an actual graphical element (gate circuit, waveform, ray diagram, etc.) alongside or instead of the table.
- Similarly, simple data tables, matching columns, and text-only charts are NOT diagrams.
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
- Logic gates (AND, OR, NAND, NOR, XOR, combinational) → diagram_type: "gates", suggested_tikz_agent: "gates"
- Electromagnetic induction (rails, sliding rods, coils, flux) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Current electricity (resistors, batteries, Kirchhoff) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- AC circuits (RLC, impedance, phasor) → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Electrostatics with capacitors → diagram_type: "circuit", suggested_tikz_agent: "circuit"
- Mechanics (blocks, pulleys, inclines, springs, circular motion) → diagram_type: "mechanics", suggested_tikz_agent: "mechanics"
- Wave mechanics (wave propagation, reflection, transmission, standing waves) → diagram_type: "wave", suggested_tikz_agent: "wave"
- Kinematics graphs (v-t, x-t, a-t) → diagram_type: "graph", suggested_tikz_agent: "graph"
- Thermodynamics graphs (P-V, T-S) → diagram_type: "graph", suggested_tikz_agent: "graph"
- Ray optics (lenses, mirrors, prisms, ray tracing) → diagram_type: "optics", suggested_tikz_agent: "optics"
- Wave optics (Young's double slit, diffraction grating, interference) → diagram_type: "optics", suggested_tikz_agent: "optics"
- Force analysis (isolated body with force arrows ONLY) → diagram_type: "fbd", suggested_tikz_agent: "fbd"
{agent_guide}

Chapter/Topic taxonomy (pick the BEST match from this list):
{chapter_topic_guide}

- chapter MUST be one of the chapter names listed above
- topic MUST be one of the topics under that chapter
- If unsure, pick the closest match — do NOT leave null

Respond with ONLY the JSON object."""
