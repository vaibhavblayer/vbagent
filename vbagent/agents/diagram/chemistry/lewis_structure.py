"""Lewis structure agent using chemfig with lone pairs."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.chemistry.lewis_structure import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_lewis(chemfig_code: str) -> tuple[bool, str]:
    if not chemfig_code or not chemfig_code.strip():
        return False, "Empty chemfig code"
    if "\\chemfig{" not in chemfig_code:
        return False, "Missing \\chemfig{} command"
    if "\\lewis{" not in chemfig_code:
        return False, "Missing \\lewis{} command (no lone pairs shown)"
    if chemfig_code.count("{") != chemfig_code.count("}"):
        o, c = chemfig_code.count("{"), chemfig_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="LewisStructure",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="Lewis structure lone pairs electrons chemfig formal charge",
    validation_return_tuple=True,
    custom_validator=_validate_lewis,
))

create_lewis_structure_agent = _agent.create_agent
generate_lewis_structure = _agent.generate
validate_lewis_structure_output = _agent.validate
get_lewis_structure_context_for_classification = _agent.get_context_for_classification
