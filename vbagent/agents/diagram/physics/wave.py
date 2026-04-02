"""Wave mechanics agent for wave diagrams."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.wave import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_wave(tikz_code: str) -> bool:
    """Validate wave diagram output."""
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    
    # Check for wave indicators
    wave_indicators = [
        "tztos", "wave", "sin(", "cos(",
        "reflection", "transmission", "standing",
        "node", "antinode", "amplitude", "wavelength",
        "incident", "reflected", "transmitted",
        "boundary", "medium", "phase"
    ]
    has_wave = any(indicator in code_lower for indicator in wave_indicators)
    
    return has_tikzpicture and has_wave


_agent = DiagramAgent(DiagramAgentConfig(
    name="Wave",
    agent_type="wave",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="wave",
    reference_tool_name="search_wave_reference",
    reference_tool_docstring=(
        "Search wave mechanics reference files for wave propagation, reflection, and transmission examples.\n\n"
        "Use this to find relevant patterns for traveling waves, standing waves, superposition,\n"
        "or diagram styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant wave references found. Using default wave mechanics conventions.",
    solution_context_hint="This explains the wave properties, boundary conditions, and wave behavior.",
    problem_template_key="problem_text",
    custom_validator=_validate_wave,
))

create_wave_agent = _agent.create_agent
generate_wave = _agent.generate
validate_wave_output = _agent.validate
get_wave_context_for_classification = _agent.get_context_for_classification
