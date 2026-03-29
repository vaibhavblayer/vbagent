"""Logic gates agent for digital logic circuit diagram generation."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.gates import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_gates(tikz_code: str) -> bool:
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    gate_nodes = ["and port", "or port", "not port", "nand port",
                  "nor port", "xor port", "xnor port"]
    has_gates = any(g in code_lower for g in gate_nodes)
    return has_tikzpicture and has_gates


_agent = DiagramAgent(DiagramAgentConfig(
    name="Gates",
    agent_type="gates",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="gates",
    reference_tool_name="search_gates_reference",
    reference_tool_docstring=(
        "Search logic gates reference files for CircuiTikZ examples.\n\n"
        "Use this to find relevant gate patterns, combinational circuits,\n"
        "or digital logic styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant gates references found. Using default CircuiTikZ IEEE conventions.",
    solution_context_hint="This explains the logic function, truth table, or Boolean expression.",
    problem_template_key="problem_text",
    custom_validator=_validate_gates,
))

create_gates_agent = _agent.create_agent
generate_gates = _agent.generate
validate_gates_output = _agent.validate
get_gates_context_for_classification = _agent.get_context_for_classification
