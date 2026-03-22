"""FBD agent for Free Body Diagram generation."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.fbd import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="FBD",
    agent_type="fbd",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="free_body",
    reference_tool_name="search_fbd_reference",
    reference_tool_docstring=(
        "Search FBD reference files for syntax examples.\n\n"
        "Use this to find relevant FBD TikZ patterns, force conventions,\n"
        "or diagram styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant FBD references found. Using default conventions.",
    solution_context_hint="This explains what forces to show, their directions, and physical meaning.",
    problem_template_key="problem_text",
    validation_markers=["->"],
))

create_fbd_agent = _agent.create_agent
generate_fbd = _agent.generate
validate_fbd_output = _agent.validate
get_fbd_context_for_classification = _agent.get_context_for_classification
