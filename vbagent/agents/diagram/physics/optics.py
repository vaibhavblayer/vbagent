"""Optics agent for ray diagrams and optical systems.

Uses openai-agents SDK to generate TikZ code specifically for optics diagrams,
with specialized validation and reference context.
"""

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.physics.optics import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


_search_optics_reference_tool = None


def _get_search_optics_reference_tool():
    """Get the search_optics_reference tool, creating it lazily."""
    global _search_optics_reference_tool
    if _search_optics_reference_tool is None:
        from agents import function_tool
        
        @function_tool
        def search_optics_reference(query: str) -> str:
            """Search optics reference files for ray diagram examples.
            
            Use this to find relevant ray tracing patterns, lens/mirror conventions,
            or diagram styles from the configured reference files.
            
            Args:
                query: Search query for optics examples or patterns
                
            Returns:
                Relevant optics examples from reference files
            """
            store = ReferenceStore.get_instance()
            results = store.search(query, file_types=["sty", "tex", "pdf"])
            
            if not results:
                return "No relevant optics references found. Using default ray tracing conventions."
            
            content_parts = []
            for result in results[:3]:
                content_parts.append(f"--- From {result.file_path} ---\n{result.content}")
            
            return "\n\n".join(content_parts)
        
        _search_optics_reference_tool = search_optics_reference
    
    return _search_optics_reference_tool


class _SearchOpticsReferenceAccessor:
    """Lazy accessor for search_optics_reference tool."""
    
    def __getattr__(self, name):
        return getattr(_get_search_optics_reference_tool(), name)
    
    def __call__(self, *args, **kwargs):
        return _get_search_optics_reference_tool()(*args, **kwargs)


search_optics_reference = _SearchOpticsReferenceAccessor()


def create_optics_agent(
    use_context: bool = True,
    classification=None,
    # NEW: Optional rich context from solution agent
    problem_text: str | None = None,
    solution_context: str | None = None,
    values: dict | None = None,
    labels: list | None = None,
):
    """Create an optics agent with optional context.
    
    Args:
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        problem_text: Optional problem text for context
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
        
    Returns:
        Configured Agent instance for optics generation
    """
    prompt = SYSTEM_PROMPT
    
    if use_context and classification:
        optics_context = get_optics_context_for_classification(classification)
        if optics_context:
            prompt = prompt + "\n" + optics_context
    
    if use_context:
        from vbagent.references.context import get_context_prompt_section
        context = get_context_prompt_section("tikz", use_context)
        if context:
            prompt = prompt + "\n" + context
    
    # NEW: Add rich context from solution agent
    if problem_text:
        prompt += f"\n\n## Problem Context\n\n{problem_text}\n"
    
    if solution_context:
        prompt += f"\n\n## Solution Analysis\n\n{solution_context}\n"
        prompt += "\nThis explains the ray paths, image formation, and optical principles.\n"
    
    if values:
        values_str = ", ".join([f"{k}={v}" for k, v in values.items()])
        prompt += f"\n\n## Values to Use\n\n{values_str}\n"
    
    if labels:
        labels_str = ", ".join(labels)
        prompt += f"\n\n## Labels Required\n\n{labels_str}\n"
    
    return create_agent(
        name="Optics",
        instructions=prompt,
        tools=[_get_search_optics_reference_tool()],
        agent_type="optics",
    )


def get_optics_context_for_classification(classification) -> str:
    """Get optics-specific context matched to classification metadata.
    
    Args:
        classification: ClassificationResult with diagram metadata
        
    Returns:
        Formatted context string with matching optics examples
    """
    try:
        from vbagent.references.tikz_store import TikZReferenceStore
        
        store = TikZReferenceStore.get_instance()
        context = store.get_context_for_classification(
            classification,
            diagram_type_filter='optics'
        )
        
        if not context:
            return ""
        
        return f"""
## Matching Optics Examples

The following examples match your problem type. Use them as style references:

{context}

---
"""
    except Exception:
        return ""


def generate_optics(
    description: str = "",
    image_path: str | None = None,
    problem_text: str | None = None,
    search_references: bool = True,
    use_context: bool = True,
    classification=None,
    show_spinner: bool = True,
    # NEW: Optional rich context from solution agent
    solution_context: str | None = None,
    values: dict | None = None,
    labels: list | None = None,
) -> str:
    """Generate optics diagram TikZ code for ray diagrams and optical systems.
    
    Can generate from:
    - A text description
    - An image of the optical system
    - A problem text (LaTeX)
    - Rich context from solution agent
    - Any combination of the above
    
    Args:
        description: Text description of the optics diagram to generate
        image_path: Optional path to an image of the setup
        problem_text: Optional LaTeX problem text to analyze
        search_references: Whether to enable reference search (default True)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        show_spinner: Whether to show animated spinner (default: True)
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
    - Any combination of the above
    
    Args:
        description: Text description of the optics diagram to generate
        image_path: Optional path to an image of the optical system
        problem_text: Optional LaTeX problem text to analyze
        search_references: Whether to enable reference search (default True)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        show_spinner: Whether to show animated spinner (default: True)
        
    Returns:
        Generated optics TikZ code as a string
        
    Raises:
        FileNotFoundError: If image_path is provided but file doesn't exist
        ValueError: If no input is provided
    """
    if not description and not image_path and not problem_text:
        raise ValueError("Must provide at least one of: description, image_path, or problem_text")
    
    agent = create_optics_agent(
        use_context=use_context,
        classification=classification,
        problem_text=problem_text,
        solution_context=solution_context,
        values=values,
        labels=labels,
    )
    
    if problem_text:
        user_message = USER_TEMPLATE_FROM_PROBLEM.format(problem_text=problem_text)
        if description:
            user_message += f"\n\n**Additional context:** {description}"
    else:
        user_message = USER_TEMPLATE.format(
            description=description or "Generate optics diagram from the provided image"
        )
    
    if image_path:
        message = create_image_message(image_path, user_message)
    else:
        message = user_message
    
    raw_result = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    return clean_latex_output(raw_result)


def validate_optics_output(tikz_code: str) -> bool:
    """Validate that optics output contains expected structure.
    
    Checks for:
    - tikzpicture environment
    - Ray arrows (draw commands with ->)
    - Optical elements (lens, mirror, or focal points)
    
    Args:
        tikz_code: The TikZ code to validate
        
    Returns:
        True if the code appears to be valid optics diagram, False otherwise
    """
    if not tikz_code or not tikz_code.strip():
        return False
    
    code_lower = tikz_code.lower()
    
    has_tikzpicture = "tikzpicture" in code_lower
    has_rays = "->" in tikz_code and "\\draw" in tikz_code
    
    # Check for optical elements
    optical_elements = ["lens", "mirror", "focal", "$f$", "principal", "axis"]
    has_optical_elements = any(elem in code_lower for elem in optical_elements)
    
    return has_tikzpicture and has_rays and has_optical_elements
