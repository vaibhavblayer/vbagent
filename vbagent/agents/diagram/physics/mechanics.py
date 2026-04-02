"""Mechanics agent for mechanical systems diagrams."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.mechanics import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_mechanics(tikz_code: str) -> bool:
    """Validate mechanics diagram output."""
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    
    # Check for mechanical system indicators
    mechanics_indicators = [
        "pulley", "spring", "block", "mass",
        "incline", "frame", "pivot", "rope",
        "string", "tension", "kinematikz",
        "coil", "rotate", "angle"
    ]
    has_mechanics = any(indicator in code_lower for indicator in mechanics_indicators)
    
    return has_tikzpicture and has_mechanics


_agent = DiagramAgent(DiagramAgentConfig(
    name="Mechanics",
    agent_type="mechanics",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="mechanics",
    reference_tool_name="search_mechanics_reference",
    reference_tool_docstring=(
        "Search mechanics reference files for pulley, spring, and mechanical system examples.\n\n"
        "Use this to find relevant patterns for pulleys, springs, inclined planes,\n"
        "rotational systems, or diagram styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant mechanics references found. Using default mechanical system conventions.",
    solution_context_hint="This explains the mechanical system configuration, forces, motion, and constraints.",
    problem_template_key="problem_text",
    custom_validator=_validate_mechanics,
))

create_mechanics_agent = _agent.create_agent
generate_mechanics = _agent.generate
validate_mechanics_output = _agent.validate
get_mechanics_context_for_classification = _agent.get_context_for_classification
