"""Venn diagram and set theory visualization agent using TikZ."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.mathematics.venn_diagram import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_venn(tikz_code: str) -> tuple[bool, str]:
    if not tikz_code or not tikz_code.strip():
        return False, "Empty TikZ code"
    if "\\begin{tikzpicture}" not in tikz_code:
        return False, "Missing \\begin{tikzpicture}"
    if "\\end{tikzpicture}" not in tikz_code:
        return False, "Missing \\end{tikzpicture}"
    if "\\draw" not in tikz_code and "\\fill" not in tikz_code:
        return False, "Missing Venn diagram shapes (\\draw or \\fill commands)"
    if tikz_code.count("{") != tikz_code.count("}"):
        o, c = tikz_code.count("{"), tikz_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="VennDiagram",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="venn diagram set theory union intersection tikz",
    validation_return_tuple=True,
    custom_validator=_validate_venn,
))

create_venn_diagram_agent = _agent.create_agent
generate_venn_diagram = _agent.generate
validate_venn_diagram_output = _agent.validate
get_venn_diagram_context_for_classification = _agent.get_context_for_classification
