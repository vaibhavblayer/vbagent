"""TikZ Agent Router.

Routes TikZ generation to specialized agents based on diagram analysis.
Uses Agent 2 (Diagram Analyzer) output for intelligent routing.
"""

from typing import Optional, Literal

from vbagent.models.classification_v2 import DiagramAnalysis, PrimaryClassification


AgentType = Literal["fbd", "circuit", "graph", "optics", "generic"]


def route_tikz_agent(
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    diagram_type: Optional[str] = None
) -> AgentType:
    """Route to appropriate TikZ agent based on diagram analysis.
    
    Priority:
    1. diagram.suggested_tikz_agent (from Agent 2)
    2. diagram.diagram_type (specific type)
    3. diagram.diagram_category (general category)
    4. primary classification hints
    5. Default to generic
    
    Args:
        diagram: DiagramAnalysis from Agent 2
        primary: PrimaryClassification from Agent 1
        diagram_type: Manual override
        
    Returns:
        Agent type to use: fbd, circuit, graph, optics, generic
    """
    # Priority 1: Use Agent 2's suggestion
    if diagram and diagram.suggested_tikz_agent:
        agent = diagram.suggested_tikz_agent.lower()
        if agent in ["fbd", "circuit", "graph", "optics", "generic"]:
            return agent
    
    # Priority 2: Specific diagram type
    if diagram and diagram.diagram_type:
        dtype = diagram.diagram_type.lower()
        
        # Free body diagrams
        if any(x in dtype for x in ["free_body", "fbd", "force", "forces"]):
            return "fbd"
        
        # Circuits
        if any(x in dtype for x in ["circuit", "electrical", "resistor", "capacitor"]):
            return "circuit"
        
        # Graphs and plots
        if any(x in dtype for x in ["graph", "plot", "function", "curve"]):
            return "graph"
        
        # Optics
        if any(x in dtype for x in ["ray", "lens", "mirror", "optic", "refraction", "reflection"]):
            return "optics"
    
    # Priority 3: Diagram category
    if diagram and diagram.diagram_category:
        category = str(diagram.diagram_category).lower()
        
        if category == "mechanics":
            return "fbd"
        elif category == "circuits":
            return "circuit"
        elif category == "graphs":
            return "graph"
        elif category == "optics":
            return "optics"
    
    # Priority 4: Primary classification hints
    if primary:
        topic = primary.topic.lower()
        
        if any(x in topic for x in ["force", "motion", "mechanics", "dynamics"]):
            return "fbd"
        elif any(x in topic for x in ["circuit", "current", "resistance"]):
            return "circuit"
        elif any(x in topic for x in ["optics", "light", "lens", "mirror"]):
            return "optics"
    
    # Priority 5: Manual override
    if diagram_type:
        dtype = diagram_type.lower()
        if "fbd" in dtype or "force" in dtype:
            return "fbd"
        elif "circuit" in dtype:
            return "circuit"
        elif "graph" in dtype or "plot" in dtype:
            return "graph"
        elif "optic" in dtype or "ray" in dtype:
            return "optics"
    
    # Default
    return "generic"


def generate_tikz_with_routing(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    use_context: bool = True
) -> tuple[str, AgentType]:
    """Generate TikZ code with automatic agent routing.
    
    Args:
        image_path: Path to diagram image
        description: Text description of diagram
        diagram: DiagramAnalysis from Agent 2
        primary: PrimaryClassification from Agent 1
        use_context: Whether to use reference context
        
    Returns:
        Tuple of (tikz_code, agent_type_used)
    """
    # Route to appropriate agent
    agent_type = route_tikz_agent(diagram, primary)
    
    # Generate with specialized agent
    if agent_type == "fbd":
        from vbagent.agents.fbd import generate_fbd
        tikz_code = generate_fbd(
            image_path=image_path,
            description=description,
            use_context=use_context
        )
    elif agent_type == "circuit":
        # TODO: Implement specialized circuit agent
        from vbagent.agents.tikz import generate_tikz
        tikz_code = generate_tikz(
            image_path=image_path,
            description=description or "Circuit diagram",
            use_context=use_context
        )
    elif agent_type == "graph":
        # TODO: Implement specialized graph agent
        from vbagent.agents.tikz import generate_tikz
        tikz_code = generate_tikz(
            image_path=image_path,
            description=description or "Graph/plot",
            use_context=use_context
        )
    elif agent_type == "optics":
        # TODO: Implement specialized optics agent
        from vbagent.agents.tikz import generate_tikz
        tikz_code = generate_tikz(
            image_path=image_path,
            description=description or "Optics diagram",
            use_context=use_context
        )
    else:  # generic
        from vbagent.agents.tikz import generate_tikz
        tikz_code = generate_tikz(
            image_path=image_path,
            description=description or "Diagram",
            use_context=use_context
        )
    
    return tikz_code, agent_type


def get_agent_capabilities(agent_type: AgentType) -> dict:
    """Get capabilities and specializations of an agent type.
    
    Args:
        agent_type: Type of agent
        
    Returns:
        Dict with capabilities, strengths, and limitations
    """
    capabilities = {
        "fbd": {
            "name": "Free Body Diagram Agent",
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
        "circuit": {
            "name": "Circuit Diagram Agent",
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
        "graph": {
            "name": "Graph/Plot Agent",
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
        "generic": {
            "name": "Generic TikZ Agent",
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
