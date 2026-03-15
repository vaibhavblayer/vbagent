"""Circuit agent for electrical circuit diagram generation.

Uses openai-agents SDK to generate CircuiTikZ code specifically for electrical circuits,
with specialized validation and reference context.
"""

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.physics.circuit import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


_search_circuit_reference_tool = None


def _get_search_circuit_reference_tool():
    """Get the search_circuit_reference tool, creating it lazily."""
    global _search_circuit_reference_tool
    if _search_circuit_reference_tool is None:
        from agents import function_tool
        
        @function_tool
        def search_circuit_reference(query: str) -> str:
            """Search circuit reference files for CircuiTikZ examples.
            
            Use this to find relevant circuit patterns, component usage,
            or diagram styles from the configured reference files.
            
            Args:
                query: Search query for circuit examples or patterns
                
            Returns:
                Relevant circuit examples from reference files
            """
            store = ReferenceStore.get_instance()
            results = store.search(query, file_types=["sty", "tex", "pdf"])
            
            if not results:
                return "No relevant circuit references found. Using default CircuiTikZ conventions."
            
            content_parts = []
            for result in results[:3]:
                content_parts.append(f"--- From {result.file_path} ---\n{result.content}")
            
            return "\n\n".join(content_parts)
        
        _search_circuit_reference_tool = search_circuit_reference
    
    return _search_circuit_reference_tool


class _SearchCircuitReferenceAccessor:
    """Lazy accessor for search_circuit_reference tool."""
    
    def __getattr__(self, name):
        return getattr(_get_search_circuit_reference_tool(), name)
    
    def __call__(self, *args, **kwargs):
        return _get_search_circuit_reference_tool()(*args, **kwargs)


search_circuit_reference = _SearchCircuitReferenceAccessor()


def create_circuit_agent(
    use_context: bool = True,
    classification=None,
    # NEW: Optional rich context from solution agent
    problem_text: str | None = None,
    solution_context: str | None = None,
    values: dict | None = None,
    labels: list | None = None,
):
    """Create a circuit agent with optional context.
    
    Args:
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        problem_text: Optional problem text for context
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
        
    Returns:
        Configured Agent instance for circuit generation
    """
    prompt = SYSTEM_PROMPT
    
    if use_context and classification:
        circuit_context = get_circuit_context_for_classification(classification)
        if circuit_context:
            prompt = prompt + "\n" + circuit_context
    
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
        prompt += "\nThis explains the circuit configuration, current flow, and component values.\n"
    
    if values:
        values_str = ", ".join([f"{k}={v}" for k, v in values.items()])
        prompt += f"\n\n## Values to Use\n\n{values_str}\n"
    
    if labels:
        labels_str = ", ".join(labels)
        prompt += f"\n\n## Labels Required\n\n{labels_str}\n"
    
    return create_agent(
        name="Circuit",
        instructions=prompt,
        tools=[_get_search_circuit_reference_tool()],
        agent_type="circuit",
    )


def get_circuit_context_for_classification(classification) -> str:
    """Get circuit-specific context matched to classification metadata.
    
    Args:
        classification: ClassificationResult with diagram metadata
        
    Returns:
        Formatted context string with matching circuit examples
    """
    try:
        from vbagent.references.tikz_store import TikZReferenceStore
        
        store = TikZReferenceStore.get_instance()
        context = store.get_context_for_classification(
            classification,
            diagram_type_filter='circuit'
        )
        
        if not context:
            return ""
        
        return f"""
## Matching Circuit Examples

The following examples match your problem type. Use them as style references:

{context}

---
"""
    except Exception:
        return ""


def generate_circuit(
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
    """Generate circuit diagram TikZ code for an electrical circuit.
    
    Can generate from:
    - A text description
    - An image of the circuit
    - A problem text (LaTeX)
    - Rich context from solution agent
    - Any combination of the above
    
    Args:
        description: Text description of the circuit to generate
        image_path: Optional path to an image of the circuit
        problem_text: Optional LaTeX problem text to analyze
        search_references: Whether to enable reference search (default True)
        use_context: Whether to include reference context in prompt
        classification: Optional ClassificationResult for metadata-based context
        show_spinner: Whether to show animated spinner (default: True)
        solution_context: Optional rich context from solution agent
        values: Optional dict of variable values
        labels: Optional list of labels needed
        
    Returns:
        Generated circuit TikZ code as a string
        
    Raises:
        FileNotFoundError: If image_path is provided but file doesn't exist
        ValueError: If no input is provided
    """
    if not description and not image_path and not problem_text:
        raise ValueError("Must provide at least one of: description, image_path, or problem_text")
    
    agent = create_circuit_agent(
        use_context=use_context,
        classification=classification,
        problem_text=problem_text,
        solution_context=solution_context,
        values=values,
        labels=labels,
    )
    
    if problem_text and not solution_context:
        user_message = USER_TEMPLATE_FROM_PROBLEM.format(problem_text=problem_text)
        if description:
            user_message += f"\n\n**Additional context:** {description}"
    else:
        user_message = USER_TEMPLATE.format(
            description=description or "Generate circuit diagram from the provided image"
        )
    
    if image_path:
        message = create_image_message(image_path, user_message)
    else:
        message = user_message
    
    raw_result = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    return clean_latex_output(raw_result)


def validate_circuit_output(tikz_code: str) -> bool:
    """Validate that circuit output contains expected structure.
    
    Checks for:
    - tikzpicture environment
    - CircuiTikZ component syntax (to [...])
    - Common components (R, C, L, battery, etc.)
    
    Args:
        tikz_code: The TikZ code to validate
        
    Returns:
        True if the code appears to be valid circuit, False otherwise
    """
    if not tikz_code or not tikz_code.strip():
        return False
    
    code_lower = tikz_code.lower()
    
    has_tikzpicture = "tikzpicture" in code_lower
    has_to_syntax = " to [" in tikz_code or " to[" in tikz_code
    
    # Check for common circuit components
    circuit_components = ["[r]", "[c]", "[l]", "[battery", "[v]", "[vco]", "[i]"]
    has_components = any(comp in code_lower for comp in circuit_components)
    
    return has_tikzpicture and has_to_syntax and has_components
