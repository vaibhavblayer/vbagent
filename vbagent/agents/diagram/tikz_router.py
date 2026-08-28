"""TikZ Agent Router.

Routes TikZ generation to specialized agents based on diagram analysis.
Uses structured diagram-classification output for intelligent routing.
"""

import re
from dataclasses import dataclass
from importlib import import_module
from typing import Literal, Optional

from vbagent.models.classification import DiagramAnalysis, PrimaryClassification

# All agent types
AgentType = Literal["fbd", "setup", "circuit", "gates", "graph", "optics", "mechanics", "wave", "organic_structure", "reaction_mechanism", "orbital", "lewis_structure", "chemical_equation", "energy_diagram", "function_graph", "coordinate_geometry", "geometric_figure", "number_line", "venn_diagram", "generic", "biology_image"]


@dataclass(frozen=True)
class _GeneratorSpec:
    """Lazy generator import plus the optional arguments it supports."""

    module: str
    function: str
    forwards: tuple[str, ...] = ()


_RICH_CONTEXT_FORWARDS = (
    "problem_text",
    "solution_context",
    "values",
    "labels",
)

_GENERATOR_REGISTRY: dict[AgentType, _GeneratorSpec] = {
    "fbd": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_fbd", _RICH_CONTEXT_FORWARDS),
    "setup": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_setup", _RICH_CONTEXT_FORWARDS),
    "circuit": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_circuit", _RICH_CONTEXT_FORWARDS),
    "gates": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_gates", _RICH_CONTEXT_FORWARDS),
    "graph": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_graph", _RICH_CONTEXT_FORWARDS),
    "optics": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_optics", _RICH_CONTEXT_FORWARDS),
    "mechanics": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_mechanics", _RICH_CONTEXT_FORWARDS),
    "wave": _GeneratorSpec("vbagent.agents.diagram.physics", "generate_wave", _RICH_CONTEXT_FORWARDS),
    "reaction_mechanism": _GeneratorSpec(
        "vbagent.agents.diagram.chemistry", "generate_reaction_mechanism"
    ),
    "orbital": _GeneratorSpec("vbagent.agents.diagram.chemistry", "generate_orbital"),
    "lewis_structure": _GeneratorSpec(
        "vbagent.agents.diagram.chemistry", "generate_lewis_structure"
    ),
    "chemical_equation": _GeneratorSpec(
        "vbagent.agents.diagram.chemistry", "generate_chemical_equation", ("mcq_options",)
    ),
    "energy_diagram": _GeneratorSpec(
        "vbagent.agents.diagram.chemistry", "generate_energy_diagram"
    ),
    "function_graph": _GeneratorSpec(
        "vbagent.agents.diagram.mathematics", "generate_function_graph",
        _RICH_CONTEXT_FORWARDS,
    ),
    "coordinate_geometry": _GeneratorSpec(
        "vbagent.agents.diagram.mathematics", "generate_coordinate_geometry",
        _RICH_CONTEXT_FORWARDS,
    ),
    "geometric_figure": _GeneratorSpec(
        "vbagent.agents.diagram.mathematics", "generate_geometric_figure",
        _RICH_CONTEXT_FORWARDS,
    ),
    "number_line": _GeneratorSpec(
        "vbagent.agents.diagram.mathematics", "generate_number_line",
        _RICH_CONTEXT_FORWARDS,
    ),
    "venn_diagram": _GeneratorSpec(
        "vbagent.agents.diagram.mathematics", "generate_venn_diagram",
        _RICH_CONTEXT_FORWARDS,
    ),
    "generic": _GeneratorSpec("vbagent.agents.diagram.tikz", "generate_tikz"),
}


def route_tikz_agent(
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    diagram_type: Optional[str] = None,
    subject: Optional[str] = None,
    diagram_context: str = "solution",
) -> AgentType:
    """Route to appropriate TikZ agent based on diagram analysis and subject.
    
    Priority:
    1. diagram.suggested_tikz_agent
    2. Subject-specific routing (chemistry vs physics)
    3. diagram.diagram_type (specific type)
    4. diagram.diagram_category (general category)
    5. primary classification hints
    6. Default to generic
    
    Args:
        diagram: Structured diagram classification
        primary: Compact question classification
        diagram_type: Manual override
        subject: Subject name (physics, chemistry, etc.)
        diagram_context: "problem" or "solution". In "problem" context a
            free-body (force) diagram is not appropriate for the printed
            figure, so an ``fbd`` route is redirected to the ``setup`` agent
            (physical scene, no force vectors).
        
    Returns:
        Agent type to use
    """
    agent = _route_tikz_agent_inner(
        diagram=diagram,
        primary=primary,
        diagram_type=diagram_type,
        subject=subject,
    )
    # Problem figures show the physical scene, not a force diagram.
    if diagram_context == "problem" and agent == "fbd":
        return "setup"
    return agent


_SUGGESTED_AGENTS = {
    "fbd", "circuit", "gates", "graph", "optics", "mechanics", "wave",
    "organic_structure", "reaction_mechanism", "orbital", "generic",
}

_SUGGESTED_GATE_KEYWORDS = (
    "logic gate", "nand", "nor gate", "xor", "xnor", "inverter",
    "flip-flop", "latch", "boolean", "truth table", "half adder",
    "full adder", "multiplexer", "decoder", "combinational",
)

_MANUAL_TYPE_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("setup", ("setup", "schematic", "apparatus")),
    ("gates", ("gate", "logic", "nand", "nor", "xor", "xnor", "flip_flop", "latch", "boolean", "combinational", "sequential", "multiplexer", "decoder", "adder")),
    ("number_line", ("number_line", "inequality", "interval")),
    ("venn_diagram", ("venn", "set")),
    ("function_graph", ("function", "calculus")),
    ("coordinate_geometry", ("coordinate", "conic")),
    ("geometric_figure", ("triangle", "polygon", "geometric")),
    ("organic_structure", ("organic", "structure")),
    ("reaction_mechanism", ("mechanism",)),
    ("orbital", ("orbital",)),
    ("lewis_structure", ("lewis",)),
    ("chemical_equation", ("equation", "reaction")),
    ("energy_diagram", ("energy", "enthalpy")),
    ("fbd", ("fbd", "force")),
    ("circuit", ("circuit",)),
    ("mechanics", ("mechanics", "pulley", "spring", "incline")),
    ("wave", ("wave", "reflection", "transmission", "standing")),
    ("graph", ("graph", "plot")),
    ("optics", ("optic", "ray")),
)

_CHEMISTRY_TYPE_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("energy_diagram", ("energy", "enthalpy", "thermodynamic", "activation", "born_haber", "hess", "coordinate", "potential")),
    ("lewis_structure", ("lewis", "lone_pair", "electron_dot", "formal_charge")),
    ("chemical_equation", ("equation", "reaction", "equilibrium", "redox", "ionic", "kinetics")),
    ("organic_structure", ("structure", "molecular", "molecule", "organic", "compound", "benzene", "alkane", "alkene", "chemfig")),
    ("reaction_mechanism", ("mechanism", "arrow", "nucleophile", "electrophile", "substitution", "elimination", "scheme")),
    ("orbital", ("orbital", "electron_config", "configuration", "energy_level", "mo_diagram", "molecular_orbital")),
)

_MATHEMATICS_TYPE_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("number_line", ("number_line", "inequality", "interval", "solution_set", "absolute_value")),
    ("venn_diagram", ("venn", "set", "union", "intersection", "complement", "subset")),
    ("function_graph", ("function", "plot", "graph", "calculus", "derivative", "integral", "tangent_line", "normal_line", "limit", "curve")),
    ("coordinate_geometry", ("coordinate", "line", "circle", "parabola", "ellipse", "hyperbola", "conic", "tangent_to", "locus")),
    ("geometric_figure", ("triangle", "polygon", "angle", "geometry", "construction", "quadrilateral", "geometric")),
)

_PHYSICS_TYPE_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("gates", ("gate", "logic", "nand", "nor", "xor", "xnor", "flip_flop", "latch", "boolean", "combinational", "sequential", "multiplexer", "decoder", "adder", "digital")),
    ("fbd", ("free_body", "fbd", "force", "forces")),
    ("mechanics", ("pulley", "spring", "incline", "inclined_plane", "atwood", "spring_mass", "shm", "oscillation", "rotation", "torque", "angular", "projectile", "trajectory", "kinematics", "work_energy")),
    ("wave", ("wave", "standing_wave", "reflection", "transmission", "superposition", "interference", "node", "antinode", "harmonic", "wave_front", "doppler", "beats")),
    ("circuit", ("circuit", "electrical", "resistor", "capacitor", "inductor", "induction", "emf", "battery", "rail", "rod_on_rail", "solenoid", "coil", "wheatstone", "potentiometer", "galvanometer", "ammeter", "voltmeter", "transformer")),
    ("graph", ("graph", "plot", "function", "curve")),
    ("optics", ("ray", "lens", "mirror", "optic", "refraction", "reflection")),
)

_PHYSICS_ELEMENT_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("gates", ("gate", "nand", "nor", "xor", "xnor", "and gate", "or gate", "not gate", "inverter", "flip-flop", "latch", "multiplexer", "decoder", "truth table")),
    ("circuit", ("resistor", "capacitor", "inductor", "battery", "emf", "wire", "switch", "ammeter", "voltmeter", "galvanometer", "rail", "rod", "coil", "solenoid", "transformer", "diode", "bulb", "lamp", "cell", "current")),
    ("mechanics", ("pulley", "spring", "incline", "inclined plane", "atwood", "rope hanging", "string attached", "rotation", "torque", "angular", "projectile", "trajectory", "shm", "oscillation", "pivot", "ceiling", "support", "frame", "kinematikz")),
    ("wave", ("wave", "wavelength", "amplitude", "frequency", "reflection", "transmission", "standing wave", "node", "antinode", "harmonic", "superposition", "interference", "phase", "wave front", "doppler", "tztos", "incident wave", "reflected wave")),
    ("fbd", ("force vector", "normal force", "friction force", "tension force", "applied force", "force arrow", "force diagram", "isolated body")),
    ("optics", ("lens", "mirror", "prism", "slit", "screen", "ray", "beam", "focal", "aperture")),
)

_GENERIC_TYPE_RULES: tuple[tuple[AgentType, tuple[str, ...]], ...] = (
    ("organic_structure", ("chemfig", "organic", "molecule")),
    ("reaction_mechanism", ("mechanism", "reaction_scheme")),
    ("orbital", ("orbital", "electron_config")),
    ("fbd", ("free_body", "fbd", "force")),
    ("circuit", ("circuit", "electrical", "induction", "emf", "inductor")),
    ("graph", ("graph", "plot")),
    ("optics", ("ray", "lens", "mirror", "optic")),
)

_CHEMISTRY_CATEGORY_ROUTES: dict[str, AgentType] = {
    "energy": "energy_diagram", "thermodynamics": "energy_diagram",
    "lewis": "lewis_structure", "electron_dot": "lewis_structure",
    "equation": "chemical_equation", "reaction": "chemical_equation",
    "structure": "organic_structure", "molecular": "organic_structure",
    "mechanism": "reaction_mechanism", "orbital": "orbital",
}
_MATHEMATICS_CATEGORY_ROUTES: dict[str, AgentType] = {
    "number_line": "number_line", "inequality": "number_line",
    "venn": "venn_diagram", "set_theory": "venn_diagram",
    "function": "function_graph", "calculus": "function_graph", "plot": "function_graph",
    "coordinate": "coordinate_geometry", "analytical": "coordinate_geometry",
    "geometry": "geometric_figure", "figure": "geometric_figure",
}
_PHYSICS_CATEGORY_ROUTES: dict[str, AgentType] = {
    "mechanics": "mechanics", "kinematics": "mechanics", "waves": "wave",
    "circuits": "circuit", "graphs": "graph", "optics": "optics",
}


def _route_by_keywords(
    value: str | None,
    rules: tuple[tuple[AgentType, tuple[str, ...]], ...],
) -> AgentType | None:
    if not value:
        return None
    normalized = value.lower()
    return next(
        (agent for agent, keywords in rules if any(word in normalized for word in keywords)),
        None,
    )


def _route_by_category(
    diagram: DiagramAnalysis | None,
    routes: dict[str, AgentType],
) -> AgentType | None:
    if not diagram or not diagram.diagram_category:
        return None
    return routes.get(str(diagram.diagram_category).lower())


def _route_chemistry(diagram: DiagramAnalysis | None) -> AgentType:
    route = _route_by_keywords(
        diagram.diagram_type if diagram else None,
        _CHEMISTRY_TYPE_RULES,
    )
    return route or _route_by_category(diagram, _CHEMISTRY_CATEGORY_ROUTES) or "organic_structure"


def _route_mathematics(diagram: DiagramAnalysis | None) -> AgentType:
    route = _route_by_keywords(
        diagram.diagram_type if diagram else None,
        _MATHEMATICS_TYPE_RULES,
    )
    return route or _route_by_category(diagram, _MATHEMATICS_CATEGORY_ROUTES) or "function_graph"


def _route_physics(diagram: DiagramAnalysis | None) -> AgentType | None:
    route = _route_by_keywords(
        diagram.diagram_type if diagram else None,
        _PHYSICS_TYPE_RULES,
    )
    if route:
        return route
    route = _route_by_category(diagram, _PHYSICS_CATEGORY_ROUTES)
    if route or not diagram or not diagram.diagram_elements:
        return route
    return _route_by_keywords(" ".join(diagram.diagram_elements), _PHYSICS_ELEMENT_RULES)


def _route_tikz_agent_inner(
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    diagram_type: Optional[str] = None,
    subject: Optional[str] = None,
) -> AgentType:
    """Core routing logic, ordered from explicit hints to broad fallbacks."""
    resolved_subject = subject or (primary.subject if primary else None)
    if resolved_subject and resolved_subject.lower() == "biology":
        return "biology_image"

    if diagram and diagram.suggested_tikz_agent:
        suggested = diagram.suggested_tikz_agent.lower()
        if suggested in _SUGGESTED_AGENTS:
            elements = " ".join(diagram.diagram_elements or []).lower()
            if suggested == "circuit" and any(
                keyword in elements for keyword in _SUGGESTED_GATE_KEYWORDS
            ):
                return "gates"
            return suggested  # type: ignore[return-value]

    manual_route = _route_by_keywords(diagram_type, _MANUAL_TYPE_RULES)
    if manual_route:
        return manual_route

    if resolved_subject:
        subject_lower = resolved_subject.lower()
        if subject_lower == "chemistry":
            return _route_chemistry(diagram)
        if subject_lower == "mathematics":
            return _route_mathematics(diagram)
        if subject_lower == "physics":
            physics_route = _route_physics(diagram)
            if physics_route:
                return physics_route

    generic_route = _route_by_keywords(
        diagram.diagram_type if diagram else None,
        _GENERIC_TYPE_RULES,
    )
    if generic_route:
        return generic_route

    if primary and primary.subject == "chemistry":
        return "organic_structure"
    if primary and primary.subject == "mathematics":
        return "function_graph"
    return "generic"


def _parse_chemistry_context(solution_context: str | None) -> dict | None:
    """Extract optional organic-diagram hints from solution context."""
    if not solution_context:
        return None

    context = {}
    flags = {"show_lone_pairs", "show_charges"}
    valued_fields = {
        "mechanism_step",
        "stereochemistry",
        "reaction_conditions",
        "key_functional_groups",
    }
    for part in re.split(r"[|\n]", solution_context):
        key, separator, value = part.strip().partition(":")
        if key in flags:
            context[key] = value.strip() if separator else "yes"
        elif key in valued_fields and separator:
            context[key] = value.strip()

    return context


def _description_with_context(description: str | None, fields: dict) -> str | None:
    """Preserve spec fields for generators without dedicated context arguments."""
    sections = [description] if description else []
    for name, value in fields.items():
        if value is None:
            continue
        if name == "labels" and not value:
            text = "No additional text labels requested; retain necessary axes/ticks and drawing actions."
        elif isinstance(value, dict):
            text = "\n".join(f"{key}: {item}" for key, item in value.items())
        elif isinstance(value, list):
            text = "\n".join(f"- {item}" for item in value)
        else:
            text = str(value)
        if text:
            sections.append(f"{name}:\n{text}")
    return "\n\n".join(sections) if sections else description


def _invoke_registered_generator(
    agent_type: AgentType,
    *,
    image_path: str | None,
    description: str | None,
    use_context: bool,
    show_spinner: bool,
    problem_text: str | None,
    solution_context: str | None,
    values: dict | None,
    labels: list | None,
    mcq_options: bool,
) -> str:
    """Load and invoke a standard generator from the dispatch registry."""
    spec = _GENERATOR_REGISTRY[agent_type]
    generator = getattr(import_module(spec.module), spec.function)
    optional_values = {
        "problem_text": problem_text,
        "solution_context": solution_context,
        "values": values,
        "labels": labels,
        "mcq_options": mcq_options,
    }
    effective_description = (
        description or "Diagram" if agent_type == "generic" else description
    )
    effective_description = _description_with_context(
        effective_description,
        {
            name: value for name, value in optional_values.items()
            if name in _RICH_CONTEXT_FORWARDS and name not in spec.forwards
        },
    )
    kwargs = {
        "image_path": image_path,
        "description": effective_description,
        "use_context": use_context,
        "show_spinner": show_spinner,
        **{name: optional_values[name] for name in spec.forwards},
    }
    return generator(**kwargs)


def generate_tikz_with_routing(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    use_context: bool = True,
    show_spinner: bool = True,
    subject: Optional[str] = None,
    diagram_type: Optional[str] = None,
    # NEW: Optional rich context from solution agent
    problem_text: Optional[str] = None,
    solution_context: Optional[str] = None,
    values: Optional[dict] = None,
    labels: Optional[list] = None,
    mcq_options: bool = False,
    diagram_context: str = "solution",
) -> tuple[str, AgentType]:
    """Generate TikZ code with automatic agent routing.
    
    Args:
        image_path: Path to diagram image
        description: Text description of diagram
        diagram: Structured diagram classification
        primary: Compact question classification
        use_context: Whether to use reference context
        show_spinner: Whether to show animated spinner (default: True)
        subject: Subject name (physics, chemistry, etc.)
        diagram_type: Manual diagram type override for routing
        problem_text: Optional problem text for context
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
        mcq_options: Whether generating MCQ options (use \\def\\OptionA{...} format)
        diagram_context: "problem" or "solution". When "problem", force/FBD
            routing is redirected to the neutral ``setup`` agent so the printed
            problem figure shows the physical scene without force vectors.
        
    Returns:
        Tuple of (tikz_code, agent_type_used)
    """
    # IMPORTANT: Only use option_diagram_type when actually generating MCQ options
    # The mcq_options parameter tells us if we're generating options vs main diagram
    # Don't confuse has_option_diagrams (classification flag) with mcq_options (generation mode)
    if mcq_options and diagram and diagram.option_diagram_type:
        # We're generating option diagrams, use option_diagram_type for routing
        routing_diagram_type = diagram.option_diagram_type
    else:
        # We're generating the main diagram, use diagram_type (or manual override)
        routing_diagram_type = diagram_type
    
    # Route to appropriate agent
    agent_type = route_tikz_agent(
        diagram, primary, diagram_type=routing_diagram_type, subject=subject,
        diagram_context=diagram_context,
    )
    
    # Biology: use gpt-image-2 instead of TikZ
    if agent_type == "biology_image":
        from pathlib import Path

        from vbagent.agents.diagram.biology import generate_biology_diagram

        # Derive output path from source image path (same stem, diagrams/ dir)
        if image_path:
            stem = Path(image_path).stem  # e.g. "problem_10"
        else:
            import hashlib
            stem = "bio_" + hashlib.sha256((description or "diagram").encode()).hexdigest()[:8]

        output_png = Path("agentic/diagrams") / f"{stem}.png"

        # Use diagram_draw_description if available (biology-specific field from DiagramAnalysis)
        # This is a proper "what to draw" description, not a description of the source image
        draw_description = description or "Biology diagram"
        if diagram and hasattr(diagram, 'diagram_draw_description') and diagram.diagram_draw_description:
            draw_description = diagram.diagram_draw_description
        elif diagram and diagram.diagram_elements:
            # Build from elements if no draw description
            elements_str = ", ".join(diagram.diagram_elements)
            draw_description = f"Scientific biology illustration showing: {elements_str}"

        result = generate_biology_diagram(
            description=draw_description,
            output_path=output_png,
            image_path=image_path,
            labels=labels,
            context=solution_context or problem_text,
            show_spinner=show_spinner,
        )
        if not result.success:
            raise RuntimeError(result.error or "Biology diagram generation failed")
        # Return the latex_include as the "tikz_code" — Option A
        return result.latex_include, "biology_image"
    
    if agent_type == "organic_structure":
        from vbagent.agents.diagram.chemistry import generate_organic_orchestrated

        tikz_code = generate_organic_orchestrated(
            image_path=image_path,
            description=_description_with_context(
                description,
                {"solution_context": solution_context, "values": values, "labels": labels},
            ),
            chemistry_context=_parse_chemistry_context(solution_context),
            problem_text=problem_text,
            use_context=use_context,
            show_spinner=show_spinner,
            mcq_options=mcq_options,
        )
    else:
        tikz_code = _invoke_registered_generator(
            agent_type,
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner,
            problem_text=problem_text,
            solution_context=solution_context,
            values=values,
            labels=labels,
            mcq_options=mcq_options,
        )

    if not isinstance(tikz_code, str) or not tikz_code.strip():
        raise ValueError(f"{agent_type} agent returned empty diagram output")

    return tikz_code, agent_type


def get_agent_capabilities(agent_type: AgentType) -> dict:
    """Get capabilities and specializations of an agent type.
    
    Args:
        agent_type: Type of agent
        
    Returns:
        Dict with capabilities, strengths, and limitations
    """
    capabilities = {
        # Physics agents
        "fbd": {
            "name": "Free Body Diagram Agent",
            "subject": "physics",
            "specializes_in": [
                "Force vectors",
                "Normal forces",
                "Friction forces",
                "Tension forces",
                "Weight/gravity",
                "Applied forces",
                "Coordinate systems"
            ],
            "strengths": [
                "Accurate force representation",
                "Proper vector notation",
                "Standard physics conventions",
                "Clean, minimal diagrams"
            ],
            "best_for": ["mechanics", "statics", "dynamics", "forces"]
        },
        "setup": {
            "name": "Problem Setup Diagram Agent",
            "subject": "physics",
            "specializes_in": [
                "Physical apparatus and scene",
                "Bodies, surfaces, supports",
                "Inclines, pulleys, springs (geometry)",
                "Given dimensions and angles",
                "Labels of given quantities",
            ],
            "strengths": [
                "Neutral problem figures (no forces)",
                "Clean kinematikz surfaces",
                "Given-data labeling only",
                "Counterpart to the FBD/force agent",
            ],
            "best_for": ["problem figures", "apparatus", "setups without forces"]
        },
        "circuit": {
            "name": "Circuit Diagram Agent",
            "subject": "physics",
            "specializes_in": [
                "Resistors",
                "Capacitors",
                "Inductors",
                "Voltage sources",
                "Current sources",
                "Switches",
                "Circuit topology"
            ],
            "strengths": [
                "Standard circuit symbols",
                "Proper connections",
                "Node labeling",
                "Current/voltage notation"
            ],
            "best_for": ["circuits", "electricity", "electronics"]
        },
        "gates": {
            "name": "Logic Gates Agent",
            "subject": "physics",
            "specializes_in": [
                "AND, OR, NOT gates",
                "NAND, NOR, XOR, XNOR gates",
                "Combinational circuits",
                "Half/full adders",
                "Multiplexers, decoders",
                "Flip-flops, latches",
            ],
            "strengths": [
                "IEEE-style gate symbols",
                "CircuiTikZ logic ports",
                "Multi-level wiring",
                "Clean input/output labeling",
            ],
            "best_for": ["logic gates", "digital circuits", "boolean algebra", "combinational logic"]
        },
        "graph": {
            "name": "Graph/Plot Agent",
            "subject": "physics",
            "specializes_in": [
                "Function plots",
                "Data visualization",
                "Coordinate systems",
                "Axes and labels",
                "Multiple curves",
                "Annotations"
            ],
            "strengths": [
                "Accurate plotting",
                "Clean axes",
                "Proper scaling",
                "Mathematical notation"
            ],
            "best_for": ["graphs", "functions", "data", "kinematics"]
        },
        "optics": {
            "name": "Optics Diagram Agent",
            "subject": "physics",
            "specializes_in": [
                "Ray diagrams",
                "Lenses",
                "Mirrors",
                "Refraction",
                "Reflection",
                "Image formation"
            ],
            "strengths": [
                "Accurate ray tracing",
                "Lens/mirror conventions",
                "Focal points",
                "Image properties"
            ],
            "best_for": ["optics", "light", "lenses", "mirrors"]
        },
        "mechanics": {
            "name": "Mechanics Diagram Agent",
            "subject": "physics",
            "specializes_in": [
                "Pulley systems",
                "Spring-mass systems",
                "Inclined planes",
                "Rotational systems",
                "Kinematics",
                "Projectile motion",
                "Work-energy scenarios",
                "SHM diagrams"
            ],
            "strengths": [
                "Accurate mechanical systems",
                "Proper pulley arrangements",
                "Spring conventions",
                "Kinematic notation",
                "Clean system diagrams"
            ],
            "best_for": ["mechanics", "pulleys", "springs", "inclines", "rotation", "kinematics"]
        },
        "wave": {
            "name": "Wave Mechanics Agent",
            "subject": "physics",
            "specializes_in": [
                "Wave propagation",
                "Reflection and transmission",
                "Standing waves",
                "Superposition",
                "Interference patterns",
                "Wave properties",
                "Doppler effect"
            ],
            "strengths": [
                "Smooth wave curves with tztos",
                "Boundary conditions",
                "Phase relationships",
                "Amplitude and wavelength marking",
                "Clean wave diagrams"
            ],
            "best_for": ["waves", "reflection", "transmission", "standing waves", "interference", "superposition"]
        },
        # Chemistry agents
        "organic_structure": {
            "name": "Organic Structure Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Molecular structures",
                "Organic compounds",
                "Functional groups",
                "Stereochemistry",
                "Ring structures",
                "Aromatic compounds"
            ],
            "strengths": [
                "chemfig expertise",
                "Proper bonding",
                "IUPAC conventions",
                "Clean structures"
            ],
            "best_for": ["organic chemistry", "molecules", "structures"]
        },
        "reaction_mechanism": {
            "name": "Reaction Mechanism Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Reaction schemes",
                "Arrow-pushing notation",
                "Electron flow",
                "Intermediates",
                "Transition states",
                "Multi-step reactions"
            ],
            "strengths": [
                "Proper arrow notation",
                "Electron movement",
                "Mechanism clarity",
                "Reagent labeling"
            ],
            "best_for": ["organic mechanisms", "reactions", "synthesis"]
        },
        "orbital": {
            "name": "Orbital Diagram Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Electron configurations",
                "Atomic orbitals",
                "Molecular orbitals",
                "Energy levels",
                "Hybridization",
                "MO diagrams"
            ],
            "strengths": [
                "Quantum mechanics",
                "Proper electron filling",
                "Energy ordering",
                "Clear notation"
            ],
            "best_for": ["atomic structure", "bonding theory", "quantum chemistry"]
        },
        "lewis_structure": {
            "name": "Lewis Structure Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Electron dot structures",
                "Lone pairs",
                "Formal charges",
                "Bonding electrons",
                "Octet rule",
                "Resonance structures"
            ],
            "strengths": [
                "chemfig \\lewis command",
                "Proper electron placement",
                "Formal charge calculation",
                "Clear lone pair notation"
            ],
            "best_for": ["Lewis structures", "electron counting", "formal charges", "bonding"]
        },
        "chemical_equation": {
            "name": "Chemical Equation Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Chemical reactions",
                "Equilibrium equations",
                "Redox reactions",
                "Ionic equations",
                "Kinetics",
                "Thermodynamics"
            ],
            "strengths": [
                "mhchem expertise",
                "Balanced equations",
                "Proper notation",
                "State symbols"
            ],
            "best_for": ["reactions", "equilibria", "physical chemistry", "inorganic chemistry"]
        },
        "energy_diagram": {
            "name": "Energy Diagram Agent",
            "subject": "chemistry",
            "specializes_in": [
                "Reaction coordinate diagrams",
                "Activation energy",
                "Enthalpy diagrams",
                "Born-Haber cycles",
                "Potential energy surfaces",
                "Thermodynamic plots"
            ],
            "strengths": [
                "TikZ/pgfplots expertise",
                "Energy profiles",
                "Transition states",
                "Thermodynamic cycles"
            ],
            "best_for": ["thermodynamics", "kinetics", "physical chemistry", "energy plots"]
        },
        # Mathematics agents
        "function_graph": {
            "name": "Function Graph Agent",
            "subject": "mathematics",
            "specializes_in": [
                "Function plotting",
                "Calculus visualization",
                "Tangent lines",
                "Normal lines",
                "Derivatives",
                "Integrals",
                "Limits and continuity"
            ],
            "strengths": [
                "pgfplots expertise",
                "Calculus concepts",
                "Curve analysis",
                "Mathematical precision"
            ],
            "best_for": ["calculus", "functions", "analysis", "curve sketching"]
        },
        "coordinate_geometry": {
            "name": "Coordinate Geometry Agent",
            "subject": "mathematics",
            "specializes_in": [
                "Lines and slopes",
                "Circles",
                "Conic sections",
                "Tangents to conics",
                "Normals",
                "Analytical geometry"
            ],
            "strengths": [
                "TikZ precision",
                "Coordinate systems",
                "Geometric relationships",
                "Tangent/normal calculations"
            ],
            "best_for": ["coordinate geometry", "conics", "analytical geometry"]
        },
        "geometric_figure": {
            "name": "Geometric Figure Agent",
            "subject": "mathematics",
            "specializes_in": [
                "Triangles",
                "Polygons",
                "Circles",
                "Angles",
                "Geometric constructions",
                "Proofs"
            ],
            "strengths": [
                "Pure geometry",
                "Standard markings",
                "Construction lines",
                "Geometric notation"
            ],
            "best_for": ["geometry", "triangles", "constructions", "proofs"]
        },
        "number_line": {
            "name": "Number Line Agent",
            "subject": "mathematics",
            "specializes_in": [
                "Number lines",
                "Inequalities",
                "Intervals",
                "Solution sets",
                "Absolute value inequalities",
                "Complex plane (Argand diagram)"
            ],
            "strengths": [
                "Open/closed circles",
                "Ray notation",
                "Interval notation",
                "Clear inequality representation"
            ],
            "best_for": ["inequalities", "intervals", "number lines", "solution sets"]
        },
        "venn_diagram": {
            "name": "Venn Diagram Agent",
            "subject": "mathematics",
            "specializes_in": [
                "Venn diagrams",
                "Set operations",
                "Union and intersection",
                "Complement",
                "Set theory",
                "Probability applications"
            ],
            "strengths": [
                "Set shading",
                "Standard notation",
                "Cardinality",
                "Clear set relationships"
            ],
            "best_for": ["set theory", "Venn diagrams", "probability", "set operations"]
        },
        # Generic
        "generic": {
            "name": "Generic TikZ Agent",
            "subject": "general",
            "specializes_in": [
                "General diagrams",
                "Geometric shapes",
                "Annotations",
                "Custom drawings"
            ],
            "strengths": [
                "Flexible",
                "Handles various types",
                "Good for simple diagrams"
            ],
            "best_for": ["general", "geometry", "simple diagrams"]
        }
    }
    
    return capabilities.get(agent_type, capabilities["generic"])
