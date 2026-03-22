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


def get_unified_classifier_prompt(subject: str = "physics") -> str:
    """Build the unified classifier prompt that handles both classification and diagram analysis."""
    valid_types = _get_valid_types(subject)
    suggested_agents = _get_suggested_agents(subject)

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

Common diagram_type corrections:
- "reaction_scheme" → "reaction_mechanism"
- "free_body" → "fbd"
- "ray_diagram" → "optics"
- "geometry" → "geometric_figure"
- "molecular_structure" → "organic_structure"

Respond with ONLY the JSON object."""
