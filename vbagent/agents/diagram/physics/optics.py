"""Optics agent for ray diagrams and optical systems."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.optics import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="Optics",
    agent_type="optics",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="optics",
    reference_tool_name="search_optics_reference",
    reference_tool_docstring=(
        "Search optics reference files for ray diagram examples.\n\n"
        "Use this to find relevant ray tracing patterns, lens/mirror conventions,\n"
        "or diagram styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant optics references found. Using default ray tracing conventions.",
    solution_context_hint="This explains the ray paths, image formation, and optical principles.",
    problem_template_key="problem_text",
    validation_markers=["->"],
))

create_optics_agent = _agent.create_agent
generate_optics = _agent.generate
validate_optics_output = _agent.validate
get_optics_context_for_classification = _agent.get_context_for_classification
