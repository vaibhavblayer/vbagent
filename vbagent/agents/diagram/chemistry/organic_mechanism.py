"""Organic reaction mechanism diagram agent using chemfig.

Specializes in showing electron movement, intermediates, and mechanistic steps.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.chemistry import organic_mechanism
from vbagent.utils.latex import clean_latex_output


def generate_mechanism(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    chemistry_context: Optional[dict] = None,
    problem_text: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate chemfig code for a reaction mechanism.
    
    Args:
        image_path: Path to mechanism image (optional)
        description: Text description of mechanism (optional)
        chemistry_context: Subject-specific context from Phase 2
        problem_text: Optional problem text for additional context
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        chemfig code with scheme and chemmove blocks
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    # Format context info
    context_info = organic_mechanism.format_context_info(
        chemistry_context or {},
        problem_text
    )
    
    # Create agent
    agent = create_agent(
        name="MechanismSpecialist",
        instructions=organic_mechanism.SYSTEM_PROMPT,
        agent_type="tikz",
    )
    
    # Prepare message
    if image_path:
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = organic_mechanism.USER_TEMPLATE.replace(
            "{context_info}", context_info
        )
        message = create_image_message(image_path, user_prompt)
    else:
        # Use replace instead of format to avoid issues with curly braces in context_info
        user_prompt = organic_mechanism.USER_TEMPLATE.replace(
            "{context_info}", context_info
        )
        if description:
            user_prompt = f"{user_prompt}\n\nDescription: {description}"
        if problem_text:
            user_prompt = f"{user_prompt}\n\nProblem context: {problem_text}"
        message = [{"role": "user", "content": user_prompt}]
    
    # Generate
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)
