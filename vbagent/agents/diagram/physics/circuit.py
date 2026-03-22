"""Circuit agent for electrical circuit diagram generation."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.circuit import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_circuit(tikz_code: str) -> bool:
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    has_to_syntax = " to [" in tikz_code or " to[" in tikz_code
    circuit_components = ["[r]", "[c]", "[l]", "[battery", "[v]", "[vco]", "[i]"]
    has_components = any(comp in code_lower for comp in circuit_components)
    return has_tikzpicture and has_to_syntax and has_components


_agent = DiagramAgent(DiagramAgentConfig(
    name="Circuit",
    agent_type="circuit",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="circuit",
    reference_tool_name="search_circuit_reference",
    reference_tool_docstring=(
        "Search circuit reference files for CircuiTikZ examples.\n\n"
        "Use this to find relevant circuit patterns, component usage,\n"
        "or diagram styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant circuit references found. Using default CircuiTikZ conventions.",
    solution_context_hint="This explains the circuit configuration, current flow, and component values.",
    problem_template_key="problem_text",
    custom_validator=_validate_circuit,
))

create_circuit_agent = _agent.create_agent
generate_circuit = _agent.generate
validate_circuit_output = _agent.validate
get_circuit_context_for_classification = _agent.get_context_for_classification
