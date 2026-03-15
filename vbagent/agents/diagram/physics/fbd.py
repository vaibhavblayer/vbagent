"""FBD agent for Free Body Diagram generation.

Uses openai-agents SDK to generate TikZ code specifically for physics FBDs,
with specialized validation and reference context.
"""

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.physics.fbd import SYSTEM_PROMPT, USER_TEMPLATE, USER_TEMPLATE_FROM_PROBLEM
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


_search_fbd_reference_tool = None


def _get_search_fbd_reference_tool():
    """Get the search_fbd_reference tool, creating it lazily."""
    global _search_fbd_reference_tool
    if _search_fbd_reference_tool is None:
        from agents import function_tool
        
        @function_tool
        def search_fbd_reference(query: str) -> str:
            """Search FBD reference files for syntax examples.
            
            Use this to find relevant FBD TikZ patterns, force conventions,
            or diagram styles from the configured reference files.
            
            Args:
                query: Search query for FBD examples or patterns
                
            Returns:
                Relevant FBD examples from reference files
            """
            store = ReferenceStore.get_instance()
            results = store.search(query, file_types=["sty", "tex", "pdf"])
            
            if not results:
                return "No relevant FBD references found. Using default conventions."
            
            content_parts = []
            for result in results[:3]:
                content_parts.append(f"--- From {result.file_path} ---\n{result.content}")
            
            return "\n\n".join(content_parts)
        
        _search_fbd_reference_tool = search_fbd_reference
    
    return _search_fbd_reference_tool


class _SearchFBDReferenceAccessor:
    """Lazy accessor for search_fbd_reference tool."""
    
    def __getattr__(self, name):
        return getattr(_get_search_fbd_reference_tool(), name)
    
    def __call__(self, *args, **kwargs):
        return _get_search_fbd_reference_tool()(*args, **kwargs)


search_fbd_reference = _SearchFBDReferenceAccessor()


def create_fbd_agent(
    use_context: bool = True,
    classification=None,
    # NEW: Optional rich context from solution agent
    problem_text: str | None = None,
    solution_context: str | None = None,
    values: dict | None = None,
    labels: list | None = None,
):
    """Create an FBD agent with optional context.
    
    Args:
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        problem_text: Optional problem text for context
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values (e.g., {"T": "10 N", "mg": "19.6 N"})
        labels: Optional list of labels needed (e.g., ["T", "mg", "N"])
        
    Returns:
        Configured Agent instance for FBD generation
    """
    prompt = SYSTEM_PROMPT
    
    # Add classification context
    if use_context and classification:
        fbd_context = get_fbd_context_for_classification(classification)
        if fbd_context:
            prompt = prompt + "\n" + fbd_context
    
    # Add reference context
    if use_context:
        from vbagent.references.context import get_context_prompt_section
        context = get_context_prompt_section("tikz", use_context)
        if context:
            prompt = prompt + "\n" + context
    
    # NEW: Add rich context from solution agent (dynamic composition)
    if problem_text:
        prompt += f"\n\n## Problem Context\n\n{problem_text}\n"
    
    if solution_context:
        prompt += f"\n\n## Solution Analysis\n\n{solution_context}\n"
        prompt += "\nThis explains what forces to show, their directions, and physical meaning.\n"
    
    if values:
        values_str = ", ".join([f"{k}={v}" for k, v in values.items()])
        prompt += f"\n\n## Values to Use\n\n{values_str}\n"
    
    if labels:
        labels_str = ", ".join(labels)
        prompt += f"\n\n## Labels Required\n\n{labels_str}\n"
        prompt += "\nEnsure all these labels appear in the diagram.\n"
    
    return create_agent(
        name="FBD",
        instructions=prompt,
        tools=[_get_search_fbd_reference_tool()],
        agent_type="fbd",
    )


def get_fbd_context_for_classification(classification) -> str:
    """Get FBD-specific context matched to classification metadata.
    
    Args:
        classification: ClassificationResult with diagram metadata
        
    Returns:
        Formatted context string with matching FBD examples
    """
    try:
        from vbagent.references.tikz_store import TikZReferenceStore
        
        store = TikZReferenceStore.get_instance()
        context = store.get_context_for_classification(
            classification,
            diagram_type_filter='free_body'
        )
        
        if not context:
            return ""
        
        return f"""
## Matching FBD Examples

The following examples match your problem type. Use them as style references:

{context}

---
"""
    except Exception:
        return ""


def generate_fbd(
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
    """Generate FBD TikZ code for a physics problem.
    
    Can generate from:
    - A text description
    - An image of the scenario
    - A problem text (LaTeX)
    - Rich context from solution agent (forces, values, labels)
    - Any combination of the above
    
    Args:
        description: Text description of the FBD to generate
        image_path: Optional path to an image of the scenario
        problem_text: Optional LaTeX problem text to analyze
        search_references: Whether to enable reference search (default True)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        show_spinner: Whether to show animated spinner
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values (e.g., {"T": "10 N"})
        labels: Optional list of labels needed (e.g., ["T", "mg"])
        
    Returns:
        Generated FBD TikZ code as a string
        
    Raises:
        FileNotFoundError: If image_path is provided but file doesn't exist
        ValueError: If no input is provided
    """
    if not description and not image_path and not problem_text:
        raise ValueError("Must provide at least one of: description, image_path, or problem_text")
    
    # Create agent with rich context
    agent = create_fbd_agent(
        use_context=use_context,
        classification=classification,
        problem_text=problem_text,
        solution_context=solution_context,
        values=values,
        labels=labels,
    )
    
    # Build user message
    if problem_text and not solution_context:
        # Legacy: problem_text in user message
        user_message = USER_TEMPLATE_FROM_PROBLEM.format(problem_text=problem_text)
        if description:
            user_message += f"\n\n**Additional context:** {description}"
    else:
        # New: description in user message, problem_text in system prompt
        user_message = USER_TEMPLATE.format(
            description=description or "Generate FBD from the provided image"
        )
    
    if image_path:
        message = create_image_message(image_path, user_message)
    else:
        message = user_message
    
    raw_result = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    return clean_latex_output(raw_result)


def validate_fbd_output(tikz_code: str) -> bool:
    """Validate that FBD output contains expected structure.
    
    Checks for:
    - tikzpicture environment
    - Force arrows (draw commands)
    - Coordinate system indicators
    
    Args:
        tikz_code: The TikZ code to validate
        
    Returns:
        True if the code appears to be valid FBD, False otherwise
    """
    if not tikz_code or not tikz_code.strip():
        return False
    
    code_lower = tikz_code.lower()
    
    has_tikzpicture = "tikzpicture" in code_lower
    has_draw_commands = any(cmd in code_lower for cmd in ["\\draw", "\\node"])
    has_arrows = "->" in tikz_code or "stealth" in code_lower
    
    return has_tikzpicture and has_draw_commands and has_arrows
