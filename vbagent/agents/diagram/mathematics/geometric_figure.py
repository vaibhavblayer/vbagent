"""Geometric figure agent using TikZ."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.mathematics.geometric_figure import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="GeometricFigure",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="geometry triangle polygon circle angle construction proof",
    validation_return_tuple=True,
))

create_geometric_figure_agent = _agent.create_agent
generate_geometric_figure = _agent.generate
validate_geometric_figure_output = _agent.validate
get_geometric_figure_context_for_classification = _agent.get_context_for_classification
