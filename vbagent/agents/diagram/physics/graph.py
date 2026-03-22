"""Graph agent for function plots and data visualization."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.physics.graph import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_graph(tikz_code: str) -> bool:
    if not tikz_code or not tikz_code.strip():
        return False
    code_lower = tikz_code.lower()
    has_tikzpicture = "tikzpicture" in code_lower
    has_axis = "\\begin{axis}" in tikz_code or "begin{axis}" in code_lower
    has_plot = "\\draw" in tikz_code and "plot" in code_lower
    has_addplot = "\\addplot" in tikz_code or "addplot" in code_lower
    return has_tikzpicture and (has_axis or has_plot or has_addplot)


_agent = DiagramAgent(DiagramAgentConfig(
    name="Graph",
    agent_type="graph",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    has_rich_context=True,
    diagram_type_filter="graph",
    reference_tool_name="search_graph_reference",
    reference_tool_docstring=(
        "Search graph reference files for plotting examples.\n\n"
        "Use this to find relevant plotting patterns, axis configurations,\n"
        "or graph styles from the configured reference files."
    ),
    reference_no_results_msg="No relevant graph references found. Using default plotting conventions.",
    solution_context_hint="This explains the graph features, data relationships, and key points.",
    problem_template_key="problem_text",
    custom_validator=_validate_graph,
))

create_graph_agent = _agent.create_agent
generate_graph = _agent.generate
validate_graph_output = _agent.validate
get_graph_context_for_classification = _agent.get_context_for_classification
