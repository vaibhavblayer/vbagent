"""Function and calculus graph agent using pgfplots."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.mathematics.function_graph import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_function_graph(tikz_code: str) -> tuple[bool, str]:
    if not tikz_code or not tikz_code.strip():
        return False, "Empty TikZ code"
    if "\\begin{tikzpicture}" not in tikz_code:
        return False, "Missing \\begin{tikzpicture}"
    if "\\end{tikzpicture}" not in tikz_code:
        return False, "Missing \\end{tikzpicture}"
    has_axis = "\\begin{axis}" in tikz_code or "\\addplot" in tikz_code
    if not has_axis:
        return False, "Missing axis environment or plot command"
    if tikz_code.count("{") != tikz_code.count("}"):
        o, c = tikz_code.count("{"), tikz_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="FunctionGraph",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="function graph plot calculus derivative integral tangent pgfplots",
    validation_return_tuple=True,
    custom_validator=_validate_function_graph,
))

create_function_graph_agent = _agent.create_agent
generate_function_graph = _agent.generate
validate_function_graph_output = _agent.validate
get_function_graph_context_for_classification = _agent.get_context_for_classification
