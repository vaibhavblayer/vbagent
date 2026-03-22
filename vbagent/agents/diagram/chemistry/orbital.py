"""Orbital diagram agent using TikZ."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.chemistry.orbital import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="OrbitalDiagram",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="orbital electron configuration molecular orbital energy level",
    validation_return_tuple=True,
))

create_orbital_agent = _agent.create_agent
generate_orbital = _agent.generate
validate_orbital_output = _agent.validate
get_orbital_context_for_classification = _agent.get_context_for_classification
