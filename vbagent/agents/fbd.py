"""FBD agent for Free Body Diagram generation.

Uses openai-agents SDK to generate TikZ code specifically for physics FBDs,
with specialized validation and reference context.
"""

import re

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.fbd import SYSTEM_PROMPT, USER_TEMPLATE, USER_TEMPLATE_FROM_PROBLEM
from vbagent.references.store import ReferenceStore


def clean_latex_output(latex: str) -> str:
    """Clean up LaTeX output by removing markdown code block markers."""
    if not latex:
        return latex
    
    latex = re.sub(r'^```(?:latex|tex|LaTeX)?\s*\n?', '', latex, flags=re.IGNORECASE)
    latex = re.sub(r'\n?```\s*$', '', latex)
    latex = re.sub(r'^```\s*', '', latex)
    
    return latex.strip()


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


def create_fbd_agent(use_context: bool = True, classification=None):
    """Create an FBD agent with optional context.
    
    Args:
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        
    Returns:
        Configured Agent instance for FBD generation
    """
    prompt = SYSTEM_PROMPT
    
    if use_context and classification:
        fbd_context = get_fbd_context_for_classification(classification)
        if fbd_context:
            prompt = prompt + "\n" + fbd_context
    
    if use_context:
        from vbagent.references.context import get_context_prompt_section
        context = get_context_prompt_section("tikz", use_context)
        if context:
            prompt = prompt + "\n" + context
    
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
) -> str:
    """Generate FBD TikZ code for a physics problem.
    
    Can generate from:
    - A text description
    - An image of the scenario
    - A problem text (LaTeX)
    - Any combination of the above
    
    Args:
        description: Text description of the FBD to generate
        image_path: Optional path to an image of the scenario
        problem_text: Optional LaTeX problem text to analyze
        search_references: Whether to enable reference search (default True)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        
    Returns:
        Generated FBD TikZ code as a string
        
    Raises:
        FileNotFoundError: If image_path is provided but file doesn't exist
        ValueError: If no input is provided
    """
    if not description and not image_path and not problem_text:
        raise ValueError("Must provide at least one of: description, image_path, or problem_text")
    
    agent = create_fbd_agent(use_context, classification)
    
    if problem_text:
        user_message = USER_TEMPLATE_FROM_PROBLEM.format(problem_text=problem_text)
        if description:
            user_message += f"\n\n**Additional context:** {description}"
    else:
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
