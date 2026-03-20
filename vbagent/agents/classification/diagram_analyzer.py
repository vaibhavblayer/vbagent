"""Agent 2: Diagram Analyzer.

Analyzes diagrams in detail and determines TikZ requirements.
Routes to specialized TikZ agents based on diagram type.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import DiagramAnalysis, PrimaryClassification


def get_diagram_analyzer_prompt(subject: str = "physics") -> str:
    """Get diagram analyzer prompt."""
    
    # Define valid diagram types per subject
    if subject == "physics":
        valid_types = ["fbd", "circuit", "graph", "optics"]
        valid_types_str = "fbd, circuit, graph, optics"
        suggested_agents = '"fbd", "circuit", "graph", "optics", "generic"'
    elif subject == "chemistry":
        valid_types = ["organic_structure", "reaction_mechanism", "chemical_equation", "energy_diagram", "orbital", "lewis_structure"]
        valid_types_str = "organic_structure, reaction_mechanism, chemical_equation, energy_diagram, orbital, lewis_structure"
        suggested_agents = '"organic_structure", "reaction_mechanism", "chemical_equation", "energy_diagram", "orbital", "lewis_structure", "generic"'
    elif subject == "mathematics":
        valid_types = ["number_line", "function_graph", "coordinate_geometry", "geometric_figure", "venn_diagram"]
        valid_types_str = "number_line, function_graph, coordinate_geometry, geometric_figure, venn_diagram"
        suggested_agents = '"number_line", "function_graph", "coordinate_geometry", "geometric_figure", "venn_diagram", "generic"'
    else:
        valid_types = ["generic"]
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

**Example:**
If the problem shows a simple molecule structure and asks "Identify the product", 
but the solution shows a full mechanism with curved arrows:
- ✅ Analyze: The simple molecule in the problem → diagram_type: "organic_structure"
- ❌ DO NOT analyze: The mechanism in the solution

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
- ❌ "reaction_scheme" → ✅ Use "reaction_mechanism" (ONLY if problem shows mechanism, not solution)
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

If the diagram doesn't clearly match any specific type, use the closest match from the valid list above.

**MCQ Option Diagrams Detection:**

If this is a multiple-choice question (MCQ) with diagrams in the answer options:
- Set `has_option_diagrams` to `true`
- Count how many options have diagrams (typically 4) → `num_option_diagrams`
- Identify what TYPE the option diagrams are (may differ from main diagram) → `option_diagram_type`
- Provide brief descriptions of what each option shows → `option_diagram_descriptions`

**IMPORTANT:** 
- The MAIN diagram (in problem) and OPTION diagrams (in choices) may be DIFFERENT types
- Example: Main diagram shows "reaction_mechanism", but options show "organic_structure" (products)
- Analyze BOTH separately and classify each correctly

**Example for Chemistry MCQ:**
```json
{{
    "diagram_type": "organic_structure",  // Main diagram in problem: simple alkyne structure
    "has_option_diagrams": true,
    "num_option_diagrams": 4,
    "option_diagram_type": "organic_structure",  // Options show product structures
    "option_diagram_descriptions": [
        "(a) Allylic bromide with cyclohexyl group",
        "(b) Vinyl bromide with cyclohexyl group",
        "(c) Gem-dibromide with terminal methyl",
        "(d) Vic-dibromide on side chain"
    ]
}}
```

If there are NO diagrams in the options (regular question with single diagram):
- Set `has_option_diagrams` to `false`
- Set `num_option_diagrams` to `0`
- Leave `option_diagram_descriptions` as empty array `[]`

Diagram categories by subject:
- Physics: mechanics (statics, dynamics, oscillations, rotational), kinematics, circuits, optics, waves, thermodynamics
- Chemistry: organic (structure, reactions), inorganic (bonding, coordination)
- Math: graphs, geometry

TikZ libraries to consider:
- calc, decorations.pathmorphing, patterns, arrows.meta
- positioning, shapes.geometric, intersections
- angles, quotes, backgrounds
- **IMPORTANT: For circuits, DO NOT use circuits.ee.IEC or other TikZ circuit libraries**

Packages to consider:
- **circuitikz (REQUIRED for ALL circuits - resistors, capacitors, batteries, etc.)**
- pgfplots (graphs, plots, functions)
- chemfig (chemistry structures)

**Circuit Diagrams:**
- ALWAYS use circuitikz package (NOT TikZ circuit libraries)
- Libraries should be empty [] for circuits (circuitikz handles everything)
- Packages should be ["circuitikz"]

Complexity score:
- 1-3: Simple (few elements, basic shapes)
- 4-7: Moderate (multiple elements, some complexity)
- 8-10: Complex (many elements, intricate relationships)

Respond with ONLY the JSON object."""


def create_diagram_analyzer_agent(subject: Optional[str] = None):
    """Create diagram analyzer agent."""
    if subject is None:
        subject = get_config().subject
    
    prompt = get_diagram_analyzer_prompt(subject)
    
    return create_agent(
        name=f"DiagramAnalyzer-{subject}",
        instructions=prompt,
        output_type=DiagramAnalysis,
        agent_type="classifier",
    )


def analyze_diagram(
    image_path: str,
    primary: PrimaryClassification,
    subject: Optional[str] = None,
    show_spinner: bool = True
) -> DiagramAnalysis:
    """Analyze diagram in detail (Agent 2).
    
    Args:
        image_path: Path to question image
        primary: Primary classification result
        subject: Subject override
        show_spinner: Whether to show animated spinner
        
    Returns:
        DiagramAnalysis with TikZ requirements
    """
    if subject is None:
        subject = primary.subject
    
    agent = create_diagram_analyzer_agent(subject)
    
    context = f"""Analyze the diagram in this {subject} question.
Question type: {primary.question_type}
Has diagram: {primary.has_diagram}

Focus on diagram structure, elements, and TikZ generation requirements."""
    
    message = create_image_message(image_path, context)
    
    result = run_agent_sync(agent, message, show_spinner=show_spinner)
    return result



def analyze_diagram_from_description(
    description: str,
    primary: "PrimaryClassification",
    subject: Optional[str] = None
) -> DiagramAnalysis:
    """Analyze diagram from text description (for generated problems).
    
    Args:
        description: Text description of the diagram
        primary: Primary classification result
        subject: Subject override
        
    Returns:
        DiagramAnalysis with TikZ requirements
    """
    if subject is None:
        subject = primary.subject
    
    agent = create_diagram_analyzer_agent(subject)
    
    context = f"""Analyze this diagram based on its description.

**Question Context:**
- Type: {primary.question_type}
- Has diagram: {primary.has_diagram}

**Diagram Description:**
{description}

Provide diagram analysis including type, elements, complexity, and TikZ requirements."""
    
    result = run_agent_sync(agent, context, show_spinner=False)
    return result
