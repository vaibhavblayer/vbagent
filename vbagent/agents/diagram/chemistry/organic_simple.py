"""Simple organic molecule diagram agent using chemfig.

Specializes in basic organic structures: chains, simple rings, common functional groups.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.chemistry import organic_simple
from vbagent.utils.latex import clean_latex_output


def generate_simple_molecule(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    chemistry_context: Optional[dict] = None,
    use_context: bool = True,
    show_spinner: bool = True,
    mcq_options: bool = False,
) -> str:
    """Generate chemfig code for a simple organic molecule.
    
    Args:
        image_path: Path to structure image (optional)
        description: Text description of structure (optional)
        chemistry_context: Subject-specific context from Phase 2
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        mcq_options: Whether to generate all 4 MCQ options
        
    Returns:
        chemfig code as string
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    # Format context info
    context_info = organic_simple.format_context_info(chemistry_context or {})
    
    # Create agent
    agent = create_agent(
        name="SimpleMolecule",
        instructions=organic_simple.SYSTEM_PROMPT,
        agent_type="tikz",
    )
    
    # Prepare message
    if image_path:
        template = (
            organic_simple.USER_TEMPLATE_MCQ_OPTIONS if mcq_options
            else organic_simple.USER_TEMPLATE
        )
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = template.replace("{context_info}", context_info)
        message = create_image_message(image_path, user_prompt)
    else:
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = organic_simple.USER_TEMPLATE.replace("{context_info}", context_info)
        if description:
            user_prompt = f"{user_prompt}\n\nDescription: {description}"
        message = [{"role": "user", "content": user_prompt}]
    
    # Generate
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)
