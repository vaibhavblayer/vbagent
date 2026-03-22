"""Reaction mechanism diagram agent using chemfig."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.chemistry.reaction_mechanism import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)


def _validate_mechanism(chemfig_code: str) -> tuple[bool, str]:
    if not chemfig_code or not chemfig_code.strip():
        return False, "Empty chemfig code"
    if "\\schemestart" not in chemfig_code:
        return False, "Missing \\schemestart command"
    if "\\schemestop" not in chemfig_code:
        return False, "Missing \\schemestop command"
    if "\\arrow" not in chemfig_code:
        return False, "Missing \\arrow command (no reaction arrow)"
    if chemfig_code.count("{") != chemfig_code.count("}"):
        o, c = chemfig_code.count("{"), chemfig_code.count("}")
        return False, f"Unbalanced braces: {o} open, {c} close"
    return True, ""


_agent = DiagramAgent(DiagramAgentConfig(
    name="ReactionMechanism",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="reaction mechanism arrow chemfig schemestart nucleophile electrophile",
    validation_return_tuple=True,
    custom_validator=_validate_mechanism,
))

create_reaction_mechanism_agent = _agent.create_agent
generate_reaction_mechanism = _agent.generate
validate_reaction_mechanism_output = _agent.validate
get_reaction_mechanism_context_for_classification = _agent.get_context_for_classification
