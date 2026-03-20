"""Physics solution generation agents.

Subject-specific solution generation for physics problems with proper
notation, units, and diagram integration.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution.physics import (
    subjective as subjective_prompts,
    mcq_sc as mcq_sc_prompts,
    mcq_mc as mcq_mc_prompts,
    assertion_reason as assertion_reason_prompts,
    match as match_prompts,
    passage as passage_prompts,
)


def generate_solution(
    problem_text: str,
    question_type: str,
    image_path: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> SolutionOutput:
    """Generate physics solution based on question type.
    
    Args:
        problem_text: Problem statement
        question_type: Question type (subjective, mcq_sc, mcq_mc, assertion_reason, match, passage)
        image_path: Optional path to problem image
        use_context: Whether to use reference context
        show_spinner: Whether to show spinner
        
    Returns:
        SolutionOutput with solution and diagram requirements
    """
    # Route to appropriate prompt based on question type
    if question_type == "subjective":
        system_prompt = subjective_prompts.SYSTEM_PROMPT
        user_template = subjective_prompts.USER_TEMPLATE
    elif question_type == "mcq_sc":
        system_prompt = mcq_sc_prompts.SYSTEM_PROMPT
        user_template = mcq_sc_prompts.USER_TEMPLATE
    elif question_type == "mcq_mc":
        system_prompt = mcq_mc_prompts.SYSTEM_PROMPT
        user_template = mcq_mc_prompts.USER_TEMPLATE
    elif question_type == "assertion_reason":
        system_prompt = assertion_reason_prompts.SYSTEM_PROMPT
        user_template = assertion_reason_prompts.USER_TEMPLATE
    elif question_type == "match":
        system_prompt = match_prompts.SYSTEM_PROMPT
        user_template = match_prompts.USER_TEMPLATE
    elif question_type == "passage":
        system_prompt = passage_prompts.SYSTEM_PROMPT
        user_template = passage_prompts.USER_TEMPLATE
    else:
        # Default to subjective
        system_prompt = subjective_prompts.SYSTEM_PROMPT
        user_template = subjective_prompts.USER_TEMPLATE
    
    # Create agent
    agent = create_agent(
        name="PhysicsSolution",
        instructions=system_prompt,
        agent_type="solution",
        response_format=SolutionOutput,
    )
    
    # Prepare message
    if image_path:
        user_prompt = user_template.format(problem=problem_text)
        message = create_image_message(image_path, user_prompt)
    else:
        user_prompt = user_template.format(problem=problem_text)
        message = [{"role": "user", "content": user_prompt}]
    
    # Generate solution
    result = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    # Parse structured output
    if isinstance(result, SolutionOutput):
        return result
    else:
        # Fallback: wrap in SolutionOutput
        return SolutionOutput(solution=str(result))
