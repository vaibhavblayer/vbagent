"""TikZ Agent Router.

Routes TikZ generation to specialized agents based on diagram analysis.
Uses Agent 2 (Diagram Analyzer) output for intelligent routing.
"""

from typing import Optional, Literal

from vbagent.models.classification import DiagramAnalysis, PrimaryClassification


# All agent types
AgentType = Literal["fbd", "circuit", "graph", "optics", "organic_structure", "reaction_mechanism", "orbital", "lewis_structure", "chemical_equation", "energy_diagram", "function_graph", "coordinate_geometry", "geometric_figure", "number_line", "venn_diagram", "generic"]


def route_tikz_agent(
    diagram: Optional[DiagramAnalysis] = None,
    primary: Optional[PrimaryClassification] = None,
    diagram_type: Optional[str] = None,
    subject: Optional[str] = None,
) -> AgentType:
    """Route to appropriate TikZ agent based on diagram analysis and subject.
    
    Priority:
    1. diagram.suggested_tikz_agent (from Agent 2)
    2. Subject-specific routing (chemistry vs physics)
    3. diagram.diagram_type (specific type)
    4. diagram.diagram_category (general category)
    5. primary classification hints
    6. Default to generic
    
    Args:
        diagram: DiagramAnalysis from Agent 2
        primary: PrimaryClassification from Agent 1
        diagram_type: Manual override
        subject: Subject name (physics, chemistry, etc.)
        
    Returns:
        Agent type to use
    """
    # Priority 1: Use Agent 2's suggestion
    if diagram and diagram.suggested_tikz_agent:
        agent = diagram.suggested_tikz_agent.lower()
        valid_agents = ["fbd", "circuit", "graph", "optics", "organic_structure", "reaction_mechanism", "orbital", "generic"]
        if agent in valid_agents:
            return agent
    
    # Priority 2: Manual override (diagram_type parameter)
    if diagram_type:
        dtype = diagram_type.lower()
        # Mathematics
        if "number_line" in dtype or "inequality" in dtype or "interval" in dtype:
            return "number_line"
        if "venn" in dtype or "set" in dtype:
            return "venn_diagram"
        if "function" in dtype or "calculus" in dtype:
            return "function_graph"
        if "coordinate" in dtype or "conic" in dtype:
            return "coordinate_geometry"
        if "triangle" in dtype or "polygon" in dtype or "geometric" in dtype:
            return "geometric_figure"
        # Chemistry
        if "organic" in dtype or "structure" in dtype:
            return "organic_structure"
        if "mechanism" in dtype:
            return "reaction_mechanism"
        if "orbital" in dtype:
            return "orbital"
        if "lewis" in dtype:
            return "lewis_structure"
        if "equation" in dtype or "reaction" in dtype:
            return "chemical_equation"
        if "energy" in dtype or "enthalpy" in dtype:
            return "energy_diagram"
        # Physics
        if "fbd" in dtype or "force" in dtype:
            return "fbd"
        if "circuit" in dtype:
            return "circuit"
        if "graph" in dtype or "plot" in dtype:
            return "graph"
        if "optic" in dtype or "ray" in dtype:
            return "optics"
    
    # Get subject from primary if not provided
    if not subject and primary and hasattr(primary, 'subject'):
        subject = primary.subject
    
    # Priority 3: Subject-specific routing
    if subject:
        subject_lower = subject.lower()
        
        # Chemistry routing
        if subject_lower == "chemistry":
            if diagram and diagram.diagram_type:
                dtype = diagram.diagram_type.lower()
                
                # Energy diagrams (thermodynamics, reaction coordinates)
                if any(x in dtype for x in ["energy", "enthalpy", "thermodynamic", "activation", "born_haber", "hess", "coordinate", "potential"]):
                    return "energy_diagram"
                
                # Lewis structures (lone pairs, formal charges)
                if any(x in dtype for x in ["lewis", "lone_pair", "electron_dot", "formal_charge"]):
                    return "lewis_structure"
                
                # Chemical equations (reactions, equilibria)
                if any(x in dtype for x in ["equation", "reaction", "equilibrium", "redox", "ionic", "kinetics"]):
                    return "chemical_equation"
                
                # Organic structures
                if any(x in dtype for x in ["structure", "molecular", "molecule", "organic", "compound", "benzene", "alkane", "alkene", "chemfig"]):
                    return "organic_structure"
                
                # Reaction mechanisms
                if any(x in dtype for x in ["mechanism", "arrow", "nucleophile", "electrophile", "substitution", "elimination", "scheme"]):
                    return "reaction_mechanism"
                
                # Orbital diagrams
                if any(x in dtype for x in ["orbital", "electron_config", "configuration", "energy_level", "mo_diagram", "molecular_orbital"]):
                    return "orbital"
            
            # Check diagram category for chemistry
            if diagram and diagram.diagram_category:
                category = str(diagram.diagram_category).lower()
                
                if category in ["energy", "thermodynamics"]:
                    return "energy_diagram"
                elif category in ["lewis", "electron_dot"]:
                    return "lewis_structure"
                elif category in ["equation", "reaction"]:
                    return "chemical_equation"
                elif category in ["structure", "molecular"]:
                    return "organic_structure"
                elif category in ["mechanism"]:
                    return "reaction_mechanism"
                elif category in ["orbital"]:
                    return "orbital"
            
            # Default for chemistry: check if it's an equation or structure
            # If description mentions "reaction" or "equation", use chemical_equation
            # Otherwise default to organic_structure (most common)
            return "organic_structure"
        
        # Mathematics routing
        elif subject_lower == "mathematics":
            if diagram and diagram.diagram_type:
                dtype = diagram.diagram_type.lower()
                
                # Number lines and inequalities
                if any(x in dtype for x in ["number_line", "inequality", "interval", "solution_set", "absolute_value"]):
                    return "number_line"
                
                # Venn diagrams and set theory
                if any(x in dtype for x in ["venn", "set", "union", "intersection", "complement", "subset"]):
                    return "venn_diagram"
                
                # Function graphs and calculus
                if any(x in dtype for x in ["function", "plot", "graph", "calculus", "derivative", "integral", "tangent_line", "normal_line", "limit", "curve"]):
                    return "function_graph"
                
                # Coordinate geometry
                if any(x in dtype for x in ["coordinate", "line", "circle", "parabola", "ellipse", "hyperbola", "conic", "tangent_to", "locus"]):
                    return "coordinate_geometry"
                
                # Geometric figures
                if any(x in dtype for x in ["triangle", "polygon", "angle", "geometry", "construction", "quadrilateral", "geometric"]):
                    return "geometric_figure"
            
            # Check diagram category for mathematics
            if diagram and diagram.diagram_category:
                category = str(diagram.diagram_category).lower()
                
                if category in ["number_line", "inequality"]:
                    return "number_line"
                elif category in ["venn", "set_theory"]:
                    return "venn_diagram"
                elif category in ["function", "calculus", "plot"]:
                    return "function_graph"
                elif category in ["coordinate", "analytical"]:
                    return "coordinate_geometry"
                elif category in ["geometry", "figure"]:
                    return "geometric_figure"
            
            # Default for mathematics: function_graph (most common)
            return "function_graph"
        
        # Physics routing
        elif subject_lower == "physics":
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
            
            # Check diagram category for physics
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
    
    # Priority 3: Specific diagram type (subject-agnostic)
    if diagram and diagram.diagram_type:
        dtype = diagram.diagram_type.lower()
        
        # Chemistry types
        if any(x in dtype for x in ["chemfig", "organic", "molecule"]):
            return "organic_structure"
        if any(x in dtype for x in ["mechanism", "reaction_scheme"]):
            return "reaction_mechanism"
        if any(x in dtype for x in ["orbital", "electron_config"]):
            return "orbital"
        
        # Physics types
        if any(x in dtype for x in ["free_body", "fbd", "force"]):
            return "fbd"
        if any(x in dtype for x in ["circuit", "electrical"]):
            return "circuit"
        if any(x in dtype for x in ["graph", "plot"]):
            return "graph"
        if any(x in dtype for x in ["ray", "lens", "mirror", "optic"]):
            return "optics"
    
    # Priority 4: Primary classification hints
    if primary and hasattr(primary, 'topic') and primary.topic:
        topic = primary.topic.lower()
        
        # Chemistry topics
        if any(x in topic for x in ["organic", "hydrocarbon", "functional_group"]):
            return "organic_structure"
        if any(x in topic for x in ["mechanism", "reaction"]):
            return "reaction_mechanism"
        if any(x in topic for x in ["orbital", "electron", "configuration"]):
            return "orbital"
        
        # Physics topics
        if any(x in topic for x in ["force", "motion", "mechanics", "dynamics"]):
            return "fbd"
        if any(x in topic for x in ["circuit", "current", "resistance"]):
            return "circuit"
        if any(x in topic for x in ["optics", "light", "lens", "mirror"]):
            return "optics"
    
    # Default
    return "generic"


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
) -> tuple[str, AgentType]:
    """Generate TikZ code with automatic agent routing.
    
    Args:
        image_path: Path to diagram image
        description: Text description of diagram
        diagram: DiagramAnalysis from Agent 2
        primary: PrimaryClassification from Agent 1
        use_context: Whether to use reference context
        show_spinner: Whether to show animated spinner (default: True)
        subject: Subject name (physics, chemistry, etc.)
        diagram_type: Manual diagram type override for routing
        problem_text: Optional problem text for context
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
        
    Returns:
        Tuple of (tikz_code, agent_type_used)
    """
    # Route to appropriate agent
    agent_type = route_tikz_agent(diagram, primary, diagram_type=diagram_type, subject=subject)
    
    # Generate with specialized agent
    # Physics agents
    if agent_type == "fbd":
        from vbagent.agents.diagram.physics import generate_fbd
        tikz_code = generate_fbd(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner,
            problem_text=problem_text,
            solution_context=solution_context,
            values=values,
            labels=labels,
        )
    elif agent_type == "circuit":
        from vbagent.agents.diagram.physics import generate_circuit
        tikz_code = generate_circuit(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner,
            problem_text=problem_text,
            solution_context=solution_context,
            values=values,
            labels=labels,
        )
    elif agent_type == "graph":
        from vbagent.agents.diagram.physics import generate_graph
        tikz_code = generate_graph(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner,
            problem_text=problem_text,
            solution_context=solution_context,
            values=values,
            labels=labels,
        )
    elif agent_type == "optics":
        from vbagent.agents.diagram.physics import generate_optics
        tikz_code = generate_optics(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner,
            problem_text=problem_text,
            solution_context=solution_context,
            values=values,
            labels=labels,
        )
    # Chemistry agents
    elif agent_type == "organic_structure":
        from vbagent.agents.diagram.chemistry import generate_organic_structure
        tikz_code = generate_organic_structure(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "reaction_mechanism":
        from vbagent.agents.diagram.chemistry import generate_reaction_mechanism
        tikz_code = generate_reaction_mechanism(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "orbital":
        from vbagent.agents.diagram.chemistry import generate_orbital
        tikz_code = generate_orbital(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "lewis_structure":
        from vbagent.agents.diagram.chemistry import generate_lewis_structure
        tikz_code = generate_lewis_structure(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "chemical_equation":
        from vbagent.agents.diagram.chemistry import generate_chemical_equation
        tikz_code = generate_chemical_equation(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "energy_diagram":
        from vbagent.agents.diagram.chemistry import generate_energy_diagram
        tikz_code = generate_energy_diagram(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    # Mathematics agents
    elif agent_type == "function_graph":
        from vbagent.agents.diagram.mathematics import generate_function_graph
        tikz_code = generate_function_graph(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "coordinate_geometry":
        from vbagent.agents.diagram.mathematics import generate_coordinate_geometry
        tikz_code = generate_coordinate_geometry(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "geometric_figure":
        from vbagent.agents.diagram.mathematics import generate_geometric_figure
        tikz_code = generate_geometric_figure(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "number_line":
        from vbagent.agents.diagram.mathematics import generate_number_line
        tikz_code = generate_number_line(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    elif agent_type == "venn_diagram":
        from vbagent.agents.diagram.mathematics import generate_venn_diagram
        tikz_code = generate_venn_diagram(
            image_path=image_path,
            description=description,
            use_context=use_context,
            show_spinner=show_spinner
        )
    else:  # generic
        from vbagent.agents.diagram.tikz import generate_tikz
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
