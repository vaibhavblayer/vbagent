"""Chemical equation agent using mhchem."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.chemistry.chemical_equation import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_chemical_equation(mhchem_code: str) -> tuple[bool, str]:
    if not mhchem_code or not mhchem_code.strip():
        return False, "Empty mhchem code"
    if "\\ce{" not in mhchem_code:
        return False, "Missing \\ce{} command"
    if mhchem_code.count("{") != mhchem_code.count("}"):
        o, c = mhchem_code.count("{"), mhchem_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="ChemicalEquation",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="chemical equation reaction mhchem equilibrium redox",
    validation_return_tuple=True,
    custom_validator=_validate_chemical_equation,
))

create_chemical_equation_agent = _agent.create_agent
generate_chemical_equation = _agent.generate
validate_chemical_equation_output = _agent.validate
get_chemical_equation_context_for_classification = _agent.get_context_for_classification
