"""Functional group transformation diagram agent using chemfig.

Specializes in highlighting specific functional group changes.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.chemistry import organic_functional
from vbagent.utils.latex import clean_latex_output


def generate_functional_group_transformation(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    chemistry_context: Optional[dict] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate chemfig code for a functional group transformation.
    
    Args:
        image_path: Path to structure image (optional)
        description: Text description of transformation (optional)
        chemistry_context: Subject-specific context from Phase 2
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        chemfig code with scheme
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    # Format context info
    context_info = organic_functional.format_context_info(chemistry_context or {})
    
    # Create agent
    agent = create_agent(
        name="FunctionalGroupSpecialist",
        instructions=organic_functional.SYSTEM_PROMPT,
        agent_type="tikz",
    )
    
    # Prepare message
    if image_path:
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = organic_functional.USER_TEMPLATE.replace(
            "{context_info}", context_info
        )
        message = create_image_message(image_path, user_prompt)
    else:
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = organic_functional.USER_TEMPLATE.replace(
            "{context_info}", context_info
        )
        if description:
            user_prompt = f"{user_prompt}\n\nDescription: {description}"
        message = [{"role": "user", "content": user_prompt}]
    
    # Generate
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)
