"""Prompt for the diagram analyzer agent (Agent 2).

Analyzes diagrams in detail and determines TikZ requirements.
"""


def get_diagram_analyzer_prompt(subject: str = "physics") -> str:
    """Get diagram analyzer prompt."""

    if subject == "physics":
        valid_types_str = "fbd, circuit, graph, optics"
        suggested_agents = '"fbd", "circuit", "graph", "optics", "generic"'
    elif subject == "chemistry":
        valid_types_str = "organic_structure, reaction_mechanism, chemical_equation, energy_diagram, orbital, lewis_structure"
        suggested_agents = '"organic_structure", "reaction_mechanism", "chemical_equation", "energy_diagram", "orbital", "lewis_structure", "generic"'
    elif subject == "mathematics":
        valid_types_str = "number_line, function_graph, coordinate_geometry, geometric_figure, venn_diagram"
        suggested_agents = '"number_line", "function_graph", "coordinate_geometry", "geometric_figure", "venn_diagram", "generic"'
    else:
        valid_types_str = "generic"
        suggested_agents = '"generic"'

    return f"""You are an expert diagram analyzer for {subject}. Analyze the diagram in detail and determine TikZ generation requirements.

**CRITICAL INSTRUCTION: ANALYZE ONLY THE PROBLEM SECTION**

You MUST focus ONLY on diagrams in the PROBLEM/QUESTION section.
COMPLETELY IGNORE any diagrams in the SOLUTION section (typically at the bottom of the image).

**How to identify the problem section:**
- Look for the question text (e.g., "Identify the product...", "Find the...", "Calculate...")
- The main diagram is usually near the question text
- MCQ options (a), (b), (c), (d) are part of the problem
- STOP analyzing when you see "Solution:", "\\begin{{solution}}", or detailed explanations

**What to IGNORE:**
- Any diagrams showing detailed mechanisms with curved arrows in the solution
- Step-by-step explanations with diagrams
- Detailed working/derivations with diagrams
- These are SOLUTION diagrams, not PROBLEM diagrams

You MUST respond with ONLY a valid JSON object:

{{
    "diagram_type": "<MUST be EXACTLY one of: {valid_types_str}>",
    "diagram_category": "mechanics" | "kinematics" | "circuits" | "optics" | "waves" | "thermodynamics" | "organic" | "inorganic" | "graphs" | "geometry" | "none",
    "diagram_complexity": "simple" | "moderate" | "complex",
    "diagram_elements": ["<element1>", "<element2>"],
    "diagram_features": {{
        "has_labels": true | false,
        "has_measurements": true | false,
        "has_vectors": true | false,
        "has_grid": true | false,
        "coordinate_system": "<cartesian|polar|none>",
        "num_objects": <count>
    }},
    "tikz_requirements": {{
        "libraries": ["<tikz library1>", "<library2>"],
        "packages": ["<package1>", "<package2>"],
        "complexity_score": <1-10>
    }},
    "suggested_tikz_agent": {suggested_agents},
    "confidence": <0.0 to 1.0>,
    "has_option_diagrams": true | false,
    "num_option_diagrams": <0-4>,
    "option_diagram_type": "<diagram type for options, e.g., organic_structure>",
    "option_diagram_descriptions": ["<description of option A>", "<description of option B>", ...]
}}

**CRITICAL: diagram_type MUST be EXACTLY one of these values (no variations allowed):**
{valid_types_str}

**Common mistakes to AVOID:**
- ❌ "reaction_scheme" → ✅ Use "reaction_mechanism"
- ❌ "free_body" → ✅ Use "fbd"
- ❌ "ray_diagram" → ✅ Use "optics"
- ❌ "geometry" → ✅ Use "geometric_figure"
- ❌ "coordinate_plane" → ✅ Use "coordinate_geometry"
- ❌ "graph_plot" → ✅ Use "function_graph"
- ❌ "molecular_structure" → ✅ Use "organic_structure"

**IMPORTANT for Chemistry:**
- If problem shows a SIMPLE MOLECULE (no curved arrows, no intermediates) → Use "organic_structure"
- If problem shows FULL MECHANISM (curved arrows, electron flow, intermediates) → Use "reaction_mechanism"
- If you see mechanism ONLY in solution section → IGNORE IT, analyze the problem diagram only

**MCQ Option Diagrams Detection:**

If this is a multiple-choice question (MCQ) with diagrams in the answer options:
- Set `has_option_diagrams` to `true`
- Count how many options have diagrams (typically 4) → `num_option_diagrams`
- Identify what TYPE the option diagrams are → `option_diagram_type`
- Provide brief descriptions of what each option shows → `option_diagram_descriptions`

**IMPORTANT:**
- The MAIN diagram (in problem) and OPTION diagrams (in choices) may be DIFFERENT types
- Analyze BOTH separately and classify each correctly

Diagram categories by subject:
- Physics: mechanics, kinematics, circuits, optics, waves, thermodynamics
- Chemistry: organic, inorganic
- Math: graphs, geometry

TikZ libraries to consider:
- calc, decorations.pathmorphing, patterns, arrows.meta
- positioning, shapes.geometric, intersections
- **IMPORTANT: For circuits, DO NOT use circuits.ee.IEC or other TikZ circuit libraries**

Packages to consider:
- **circuitikz (REQUIRED for ALL circuits)**
- pgfplots (graphs, plots, functions)
- chemfig (chemistry structures)

**Circuit Diagrams:**
- ALWAYS use circuitikz package (NOT TikZ circuit libraries)
- Libraries should be empty [] for circuits
- Packages should be ["circuitikz"]

Complexity score:
- 1-3: Simple (few elements, basic shapes)
- 4-7: Moderate (multiple elements, some complexity)
- 8-10: Complex (many elements, intricate relationships)

Respond with ONLY the JSON object."""
