"""Number line and inequality visualization agent using TikZ."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.mathematics.number_line import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="NumberLine",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="number line inequality interval solution set tikz",
    validation_return_tuple=True,
))

create_number_line_agent = _agent.create_agent
generate_number_line = _agent.generate
validate_number_line_output = _agent.validate
get_number_line_context_for_classification = _agent.get_context_for_classification
