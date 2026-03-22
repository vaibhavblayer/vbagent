"""Coordinate geometry agent using TikZ."""

from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram.mathematics.coordinate_geometry import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)

_agent = DiagramAgent(DiagramAgentConfig(
    name="CoordinateGeometry",
    agent_type="tikz",
    system_prompt=SYSTEM_PROMPT,
    user_template=USER_TEMPLATE,
    user_template_from_problem=USER_TEMPLATE_FROM_PROBLEM,
    reference_search_query="coordinate geometry line circle parabola ellipse tangent normal",
    validation_return_tuple=True,
))

create_coordinate_geometry_agent = _agent.create_agent
generate_coordinate_geometry = _agent.generate
validate_coordinate_geometry_output = _agent.validate
get_coordinate_geometry_context_for_classification = _agent.get_context_for_classification
