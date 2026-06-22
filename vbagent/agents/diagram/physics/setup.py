"""Setup agent for physics PROBLEM diagrams (physical scene, no forces).

Problem-side counterpart to the FBD agent. Draws the apparatus, geometry, and
given labels of a problem WITHOUT force vectors or solution annotations.
"""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.setup import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_setup(tikz_code: str) -> bool:
    """Validate a problem setup diagram.

    Unlike the FBD agent, we do NOT require arrows — a setup figure is often
    arrow-free. We only require a non-empty tikzpicture with some drawing.
    """
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    has_draw = any(cmd in code_lower for cmd in ["\\draw", "\\node", "\\pic", "\\fill"])
    return has_tikzpicture and has_draw


_agent = DiagramAgent(DiagramAgentConfig(
    name="Setup",
    agent_type="setup",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="setup",
    reference_tool_name="search_setup_reference",
    reference_tool_docstring=(
        "Search reference files for physics setup/apparatus diagram examples.\n\n"
        "Use this to find relevant patterns for blocks, inclines, pulleys, springs,\n"
        "and other physical setups — without force annotations."
    ),
    reference_no_results_msg="No relevant setup references found. Using default conventions.",
    solution_context_hint="Use this only to understand the scene geometry — do NOT draw forces from it.",
    problem_template_key="problem_text",
    custom_validator=_validate_setup,
))

create_setup_agent = _agent.create_agent
generate_setup = _agent.generate
validate_setup_output = _agent.validate
get_setup_context_for_classification = _agent.get_context_for_classification
