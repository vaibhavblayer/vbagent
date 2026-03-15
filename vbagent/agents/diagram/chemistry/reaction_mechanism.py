"""Reaction mechanism diagram agent using chemfig.

Generates reaction mechanisms with arrow-pushing notation for organic chemistry.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.chemistry.reaction_mechanism import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


def create_reaction_mechanism_agent(use_context: bool = True) -> "Agent":
    """Create a reaction mechanism generation agent.
    
    Args:
        use_context: Whether to include reference context
        
    Returns:
        Configured Agent instance
    """
    prompt = SYSTEM_PROMPT
    
    if use_context:
        context = get_reaction_mechanism_context_for_classification()
        if context:
            prompt = prompt + "\n\n" + context
    
    return create_agent(
        name="ReactionMechanism",
        instructions=prompt,
        agent_type="tikz",
    )


def generate_reaction_mechanism(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate chemfig code for a reaction mechanism.
    
    Args:
        image_path: Path to mechanism image (optional)
        description: Text description of mechanism (optional)
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        chemfig scheme code as string
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    agent = create_reaction_mechanism_agent(use_context)
    
    if image_path:
        message = create_image_message(image_path, USER_TEMPLATE)
    else:
        # For text-only description, create a simple text message
        message = [{"role": "user", "content": USER_TEMPLATE_FROM_PROBLEM.format(problem=description)}]
    
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)


def validate_reaction_mechanism_output(chemfig_code: str) -> tuple[bool, str]:
    """Validate chemfig code for reaction mechanisms.
    
    Args:
        chemfig_code: The chemfig code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not chemfig_code or not chemfig_code.strip():
        return False, "Empty chemfig code"
    
    # Check for scheme commands
    if "\\schemestart" not in chemfig_code:
        return False, "Missing \\schemestart command"
    
    if "\\schemestop" not in chemfig_code:
        return False, "Missing \\schemestop command"
    
    # Check for arrow
    if "\\arrow" not in chemfig_code:
        return False, "Missing \\arrow command (no reaction arrow)"
    
    # Check for balanced braces
    open_count = chemfig_code.count("{")
    close_count = chemfig_code.count("}")
    if open_count != close_count:
        return False, f"Unbalanced braces: {open_count} open, {close_count} close"
    
    return True, ""


def get_reaction_mechanism_context_for_classification() -> str:
    """Get reference context for reaction mechanism generation.
    
    Returns:
        Context string with relevant examples
    """
    store = ReferenceStore()
    
    results = store.search(
        query="reaction mechanism arrow chemfig schemestart nucleophile electrophile",
        file_types=["sty", "tex", "pdf"],
        max_results=3
    )
    
    if not results:
        return ""
    
    context = "\n\n## Reference Examples\n\n"
    context += "Here are some similar reaction mechanisms from our reference library:\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"### Example {i}\n"
        context += f"```latex\n{result.content}\n```\n\n"
    
    return context
