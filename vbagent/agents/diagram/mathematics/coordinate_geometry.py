"""Coordinate geometry agent using TikZ.

Generates coordinate geometry diagrams: lines, circles, conics,
tangents, normals, and analytical geometry problems.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.mathematics.coordinate_geometry import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


def create_coordinate_geometry_agent(use_context: bool = True) -> "Agent":
    """Create a coordinate geometry generation agent.
    
    Args:
        use_context: Whether to include reference context
        
    Returns:
        Configured Agent instance
    """
    prompt = SYSTEM_PROMPT
    
    if use_context:
        context = get_coordinate_geometry_context_for_classification()
        if context:
            prompt = prompt + "\n\n" + context
    
    return create_agent(
        name="CoordinateGeometry",
        instructions=prompt,
        agent_type="tikz",
    )


def generate_coordinate_geometry(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate TikZ code for a coordinate geometry diagram.
    
    Args:
        image_path: Path to diagram image (optional)
        description: Text description of diagram (optional)
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        TikZ code as string
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    agent = create_coordinate_geometry_agent(use_context)
    
    if image_path:
        message = create_image_message(image_path, USER_TEMPLATE)
    else:
        message = [{"role": "user", "content": USER_TEMPLATE_FROM_PROBLEM.format(problem=description)}]
    
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)


def validate_coordinate_geometry_output(tikz_code: str) -> tuple[bool, str]:
    """Validate TikZ code for coordinate geometry.
    
    Args:
        tikz_code: The TikZ code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tikz_code or not tikz_code.strip():
        return False, "Empty TikZ code"
    
    if "\\begin{tikzpicture}" not in tikz_code:
        return False, "Missing \\begin{tikzpicture}"
    
    if "\\end{tikzpicture}" not in tikz_code:
        return False, "Missing \\end{tikzpicture}"
    
    # Check for balanced braces
    open_count = tikz_code.count("{")
    close_count = tikz_code.count("}")
    if open_count != close_count:
        return False, f"Unbalanced braces: {open_count} open, {close_count} close"
    
    return True, ""


def get_coordinate_geometry_context_for_classification() -> str:
    """Get reference context for coordinate geometry generation.
    
    Returns:
        Context string with relevant examples
    """
    store = ReferenceStore()
    
    results = store.search(
        query="coordinate geometry line circle parabola ellipse tangent normal",
        file_types=["sty", "tex", "pdf"],
        max_results=3
    )
    
    if not results:
        return ""
    
    context = "\n\n## Reference Examples\n\n"
    context += "Here are some similar coordinate geometry diagrams from our reference library:\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"### Example {i}\n"
        context += f"```latex\n{result.content}\n```\n\n"
    
    return context
