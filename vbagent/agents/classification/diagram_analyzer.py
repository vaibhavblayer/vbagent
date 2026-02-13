"""Agent 2: Diagram Analyzer.

Analyzes diagrams in detail and determines TikZ requirements.
Routes to specialized TikZ agents based on diagram type.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification_v2 import DiagramAnalysis, PrimaryClassification


def get_diagram_analyzer_prompt(subject: str = "physics") -> str:
    """Get diagram analyzer prompt."""
    return f"""You are an expert diagram analyzer for {subject}. Analyze the diagram in detail and determine TikZ generation requirements.

You MUST respond with ONLY a valid JSON object:

{{
    "diagram_type": "<specific type: free_body, circuit, graph, ray_diagram, etc.>",
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
    "suggested_tikz_agent": "generic" | "fbd" | "circuit" | "graph" | "optics",
    "confidence": <0.0 to 1.0>
}}

Diagram categories by subject:
- Physics: mechanics (statics, dynamics, oscillations, rotational), kinematics, circuits, optics, waves, thermodynamics
- Chemistry: organic (structure, reactions), inorganic (bonding, coordination)
- Math: graphs, geometry

Suggested TikZ agents:
- "fbd": Free body diagrams (forces, vectors)
- "circuit": Electrical circuits (use circuitikz)
- "graph": Plots, graphs, functions
- "optics": Ray diagrams, lenses, mirrors
- "generic": Everything else

TikZ libraries to consider:
- calc, decorations.pathmorphing, patterns, arrows.meta
- positioning, shapes.geometric, intersections
- angles, quotes, backgrounds

Packages to consider:
- circuitikz (circuits)
- pgfplots (graphs)
- chemfig (chemistry structures)

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
Topic: {primary.topic}
Subtopic: {primary.subtopic}

Focus on diagram structure, elements, and TikZ generation requirements."""
    
    message = create_image_message(image_path, context)
    
    result = run_agent_sync(agent, message, show_spinner=show_spinner)
    return result
