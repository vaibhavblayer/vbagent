"""Venn diagram and set theory visualization agent using TikZ.

Generates Venn diagrams, set operations, and set theory visualizations.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.mathematics.venn_diagram import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


def create_venn_diagram_agent(use_context: bool = True) -> "Agent":
    """Create a Venn diagram generation agent.
    
    Args:
        use_context: Whether to include reference context
        
    Returns:
        Configured Agent instance
    """
    prompt = SYSTEM_PROMPT
    
    if use_context:
        context = get_venn_diagram_context_for_classification()
        if context:
            prompt = prompt + "\n\n" + context
    
    return create_agent(
        name="VennDiagram",
        instructions=prompt,
        agent_type="tikz",
    )


def generate_venn_diagram(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate TikZ code for a Venn diagram.
    
    Args:
        image_path: Path to Venn diagram image (optional)
        description: Text description of Venn diagram (optional)
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        TikZ code as string
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    agent = create_venn_diagram_agent(use_context)
    
    if image_path:
        message = create_image_message(image_path, USER_TEMPLATE)
    else:
        message = [{"role": "user", "content": USER_TEMPLATE_FROM_PROBLEM.format(problem=description)}]
    
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)


def validate_venn_diagram_output(tikz_code: str) -> tuple[bool, str]:
    """Validate TikZ code for Venn diagrams.
    
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
    
    # Check for Venn diagram elements (circles or rectangles)
    has_shapes = "\\draw" in tikz_code or "\\fill" in tikz_code
    if not has_shapes:
        return False, "Missing Venn diagram shapes (\\draw or \\fill commands)"
    
    # Check for balanced braces
    open_count = tikz_code.count("{")
    close_count = tikz_code.count("}")
    if open_count != close_count:
        return False, f"Unbalanced braces: {open_count} open, {close_count} close"
    
    return True, ""


def get_venn_diagram_context_for_classification() -> str:
    """Get reference context for Venn diagram generation.
    
    Returns:
        Context string with relevant examples
    """
    store = ReferenceStore()
    
    results = store.search(
        query="venn diagram set theory union intersection tikz",
        file_types=["sty", "tex", "pdf"],
        max_results=3
    )
    
    if not results:
        return ""
    
    context = "\n\n## Reference Examples\n\n"
    context += "Here are some similar Venn diagrams from our reference library:\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"### Example {i}\n"
        context += f"```latex\n{result.content}\n```\n\n"
    
    return context
