"""Diagram generation agents.

This module contains agents responsible for generating and managing diagrams:
- TikZ: Generate TikZ diagrams
- FBD: Generate free body diagrams
- TikZ Router: Route diagram generation requests
- TikZ Checker: Validate TikZ diagrams
"""

from .tikz import generate_tikz, create_tikz_agent, validate_tikz_output, get_tikz_context_for_classification
from .fbd import generate_fbd, create_fbd_agent, validate_fbd_output, get_fbd_context_for_classification
from .tikz_router import route_tikz_agent, generate_tikz_with_routing, get_agent_capabilities
from .tikz_checker import (
    check_tikz,
    check_tikz_with_patch,
    create_tikz_checker_agent,
    create_tikz_patch_agent,
    parse_check_result,
    has_tikz_passed,
    has_tikz_environment,
)

__all__ = [
    # TikZ
    "generate_tikz",
    "create_tikz_agent",
    "validate_tikz_output",
    "get_tikz_context_for_classification",
    # FBD
    "generate_fbd",
    "create_fbd_agent",
    "validate_fbd_output",
    "get_fbd_context_for_classification",
    # Router
    "route_tikz_agent",
    "generate_tikz_with_routing",
    "get_agent_capabilities",
    # Checker
    "check_tikz",
    "check_tikz_with_patch",
    "create_tikz_checker_agent",
    "create_tikz_patch_agent",
    "parse_check_result",
    "has_tikz_passed",
    "has_tikz_environment",
]
