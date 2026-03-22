"""MCQ Option Diagram Coordinator.

Generates all 4 MCQ option diagrams using subject-specific specialized agents.
Routes to appropriate generators based on subject and diagram type.
"""

from typing import Optional


def generate_mcq_options(
    image_path: str,
    subject: str,
    option_diagram_type: str,
    option_descriptions: Optional[list[str]] = None,
    diagram_analysis: Optional[dict] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate MCQ option diagrams using subject-specific agents.
    
    Args:
        image_path: Path to problem image
        subject: Subject (physics, chemistry, mathematics)
        option_diagram_type: Type of diagrams in options (e.g., organic_structure, graph, fbd)
        option_descriptions: List of descriptions for each option
        diagram_analysis: Full diagram analysis object
        use_context: Whether to use reference context
        show_spinner: Whether to show progress spinner
        
    Returns:
        String with \\def\\OptionA{...}\\def\\OptionB{...}\\def\\OptionC{...}\\def\\OptionD{...}
    """
    
    # Determine number of options from diagram_analysis
    num_options = 4  # Default
    if diagram_analysis and isinstance(diagram_analysis, dict):
        num_options = diagram_analysis.get('num_option_diagrams', 4)
    elif diagram_analysis and hasattr(diagram_analysis, 'num_option_diagrams'):
        num_options = diagram_analysis.num_option_diagrams
    
    # Limit option_descriptions to actual number of options
    if option_descriptions and len(option_descriptions) > num_options:
        option_descriptions = option_descriptions[:num_options]
    
    # Build description from option_descriptions
    description = f"Generate {num_options} MCQ option diagrams"
    if option_descriptions:
        description += ":\n" + "\n".join(f"({chr(65+i)}) {desc}" for i, desc in enumerate(option_descriptions))
    
    # Route based on subject
    if subject.lower() == "chemistry":
        return _generate_chemistry_options(
            image_path=image_path,
            option_diagram_type=option_diagram_type,
            description=description,
            option_descriptions=option_descriptions,
            diagram_analysis=diagram_analysis,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    elif subject.lower() == "physics":
        return _generate_physics_options(
            image_path=image_path,
            option_diagram_type=option_diagram_type,
            description=description,
            option_descriptions=option_descriptions,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    elif subject.lower() == "mathematics":
        return _generate_mathematics_options(
            image_path=image_path,
            option_diagram_type=option_diagram_type,
            description=description,
            option_descriptions=option_descriptions,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    else:
        # Fallback to generic TikZ
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )


def _generate_chemistry_options(
    image_path: str,
    option_diagram_type: str,
    description: str,
    option_descriptions: Optional[list[str]],
    diagram_analysis: Optional[dict],
    num_options: int,
    use_context: bool,
    show_spinner: bool,
) -> str:
    """Generate chemistry MCQ options using organic orchestrator."""
    
    # For organic structures, use the organic orchestrator
    if option_diagram_type in ["organic_structure", "organic", "structure"]:
        from vbagent.agents.diagram.chemistry import generate_organic_orchestrated
        
        # Build chemistry context
        chemistry_context = {}
        if diagram_analysis:
            # diagram_analysis is a dict (from model_dump())
            if isinstance(diagram_analysis, dict) and 'diagram_features' in diagram_analysis:
                chemistry_context["features"] = diagram_analysis['diagram_features']
            elif hasattr(diagram_analysis, 'diagram_features'):
                # Fallback for object (shouldn't happen but safe)
                chemistry_context["features"] = diagram_analysis.diagram_features
        
        # Add num_options to description
        description_with_count = f"{description}\n\nGenerate EXACTLY {num_options} options (A through {chr(64+num_options)})."
        
        return generate_organic_orchestrated(
            image_path=image_path,
            description=description_with_count,
            chemistry_context=chemistry_context,
            use_context=use_context,
            show_spinner=show_spinner,
            mcq_options=True,  # Critical: tells orchestrator to generate options
        )
    
    # For other chemistry diagrams, use generic TikZ with chemistry context
    else:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )


def _generate_physics_options(
    image_path: str,
    option_diagram_type: str,
    description: str,
    option_descriptions: Optional[list[str]],
    num_options: int,
    use_context: bool,
    show_spinner: bool,
) -> str:
    """Generate physics MCQ options using specialized agents where appropriate."""
    
    # For graphs, use generic TikZ (it has good graph support)
    if option_diagram_type in ["graph", "plot", "curve"]:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    # For FBD options, could use FBD agent in future
    # For now, use generic TikZ which handles simple FBDs
    elif option_diagram_type in ["fbd", "free_body_diagram"]:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    # For circuit options, could use circuit agent in future
    elif option_diagram_type in ["circuit", "electrical_circuit"]:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    # Default: generic TikZ
    else:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )


def _generate_mathematics_options(
    image_path: str,
    option_diagram_type: str,
    description: str,
    option_descriptions: Optional[list[str]],
    num_options: int,
    use_context: bool,
    show_spinner: bool,
) -> str:
    """Generate mathematics MCQ options using specialized agents where appropriate."""
    
    # For function graphs, use generic TikZ (good support)
    if option_diagram_type in ["function_graph", "graph", "plot"]:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    # For geometric diagrams, use generic TikZ
    elif option_diagram_type in ["geometry", "geometric_diagram"]:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )
    
    # Default: generic TikZ
    else:
        return _generate_generic_options(
            image_path=image_path,
            description=description,
            num_options=num_options,
            use_context=use_context,
            show_spinner=show_spinner,
        )


def _generate_generic_options(
    image_path: str,
    description: str,
    num_options: int,
    use_context: bool,
    show_spinner: bool,
) -> str:
    """Fallback: generate options using generic TikZ agent."""
    from vbagent.agents.diagram.tikz import generate_tikz
    
    # Build option list
    option_letters = [chr(65+i) for i in range(num_options)]  # A, B, C, ...
    option_defs = ", ".join(f"\\def\\Option{letter}{{...}}" for letter in option_letters)
    
    # Add explicit instruction for option format
    description_with_format = f"""{description}

CRITICAL: Output MUST be in \\def\\OptionX{{...}} format.
Generate exactly {num_options} definitions: {option_defs}"""
    
    return generate_tikz(
        description=description_with_format,
        image_path=image_path,
        use_context=use_context,
        show_spinner=show_spinner,
    )
