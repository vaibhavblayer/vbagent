"""Energy diagram agent using TikZ and pgfplots."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.chemistry.energy_diagram import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_energy_diagram(tikz_code: str) -> tuple[bool, str]:
    if not tikz_code or not tikz_code.strip():
        return False, "Empty TikZ code"
    if "\\begin{tikzpicture}" not in tikz_code:
        return False, "Missing \\begin{tikzpicture}"
    if "\\end{tikzpicture}" not in tikz_code:
        return False, "Missing \\end{tikzpicture}"
    if tikz_code.count("{") != tikz_code.count("}"):
        o, c = tikz_code.count("{"), tikz_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    has_energy = any(w in tikz_code.lower() for w in ["energy", "enthalpy", "gibbs", "activation"])
    if not has_energy:
        return False, "Missing energy-related labels"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="EnergyDiagram",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="energy diagram reaction coordinate activation enthalpy thermodynamics",
    validation_return_tuple=True,
    custom_validator=_validate_energy_diagram,
))

create_energy_diagram_agent = _agent.create_agent
generate_energy_diagram = _agent.generate
validate_energy_diagram_output = _agent.validate
get_energy_diagram_context_for_classification = _agent.get_context_for_classification
