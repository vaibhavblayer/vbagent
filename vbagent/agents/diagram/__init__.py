"""Diagram generation agents.

This module contains agents responsible for generating and managing diagrams:
- TikZ: Generate TikZ diagrams (generic fallback)
- Physics: Specialized physics diagram agents (FBD, Circuit, Graph, Optics)
- Chemistry: Specialized chemistry diagram agents (Organic, Mechanism, Orbital)
- TikZ Router: Route diagram generation requests
- TikZ Checker: Validate TikZ diagrams
"""

from .tikz import generate_tikz, create_tikz_agent, validate_tikz_output, get_tikz_context_for_classification

# Physics agents
from .physics import (
    generate_fbd, create_fbd_agent, validate_fbd_output, get_fbd_context_for_classification,
    generate_circuit, create_circuit_agent, validate_circuit_output, get_circuit_context_for_classification,
    generate_graph, create_graph_agent, validate_graph_output, get_graph_context_for_classification,
    generate_optics, create_optics_agent, validate_optics_output, get_optics_context_for_classification,
)

# Chemistry agents
from .chemistry import (
    generate_organic_structure, create_organic_structure_agent, validate_organic_structure_output, get_organic_structure_context_for_classification,
    generate_reaction_mechanism, create_reaction_mechanism_agent, validate_reaction_mechanism_output, get_reaction_mechanism_context_for_classification,
    generate_orbital, create_orbital_agent, validate_orbital_output, get_orbital_context_for_classification,
    generate_lewis_structure, create_lewis_structure_agent, validate_lewis_structure_output, get_lewis_structure_context_for_classification,
    generate_chemical_equation, create_chemical_equation_agent, validate_chemical_equation_output, get_chemical_equation_context_for_classification,
    generate_energy_diagram, create_energy_diagram_agent, validate_energy_diagram_output, get_energy_diagram_context_for_classification,
)

# Mathematics agents
from .mathematics import (
    generate_function_graph, create_function_graph_agent, validate_function_graph_output, get_function_graph_context_for_classification,
    generate_coordinate_geometry, create_coordinate_geometry_agent, validate_coordinate_geometry_output, get_coordinate_geometry_context_for_classification,
    generate_geometric_figure, create_geometric_figure_agent, validate_geometric_figure_output, get_geometric_figure_context_for_classification,
    generate_number_line, create_number_line_agent, validate_number_line_output, get_number_line_context_for_classification,
    generate_venn_diagram, create_venn_diagram_agent, validate_venn_diagram_output, get_venn_diagram_context_for_classification,
)

from .tikz_router import route_tikz_agent, generate_tikz_with_routing, get_agent_capabilities
from .mcq_option_coordinator import generate_mcq_options
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
    # TikZ (generic)
    "generate_tikz",
    "create_tikz_agent",
    "validate_tikz_output",
    "get_tikz_context_for_classification",
    # Physics - FBD
    "generate_fbd",
    "create_fbd_agent",
    "validate_fbd_output",
    "get_fbd_context_for_classification",
    # Physics - Circuit
    "generate_circuit",
    "create_circuit_agent",
    "validate_circuit_output",
    "get_circuit_context_for_classification",
    # Physics - Graph
    "generate_graph",
    "create_graph_agent",
    "validate_graph_output",
    "get_graph_context_for_classification",
    # Physics - Optics
    "generate_optics",
    "create_optics_agent",
    "validate_optics_output",
    "get_optics_context_for_classification",
    # Chemistry - Organic Structure
    "generate_organic_structure",
    "create_organic_structure_agent",
    "validate_organic_structure_output",
    "get_organic_structure_context_for_classification",
    # Chemistry - Reaction Mechanism
    "generate_reaction_mechanism",
    "create_reaction_mechanism_agent",
    "validate_reaction_mechanism_output",
    "get_reaction_mechanism_context_for_classification",
    # Chemistry - Orbital
    "generate_orbital",
    "create_orbital_agent",
    "validate_orbital_output",
    "get_orbital_context_for_classification",
    # Chemistry - Lewis Structure
    "generate_lewis_structure",
    "create_lewis_structure_agent",
    "validate_lewis_structure_output",
    "get_lewis_structure_context_for_classification",
    # Chemistry - Chemical Equation
    "generate_chemical_equation",
    "create_chemical_equation_agent",
    "validate_chemical_equation_output",
    "get_chemical_equation_context_for_classification",
    # Chemistry - Energy Diagram
    "generate_energy_diagram",
    "create_energy_diagram_agent",
    "validate_energy_diagram_output",
    "get_energy_diagram_context_for_classification",
    # Mathematics - Function Graph
    "generate_function_graph",
    "create_function_graph_agent",
    "validate_function_graph_output",
    "get_function_graph_context_for_classification",
    # Mathematics - Coordinate Geometry
    "generate_coordinate_geometry",
    "create_coordinate_geometry_agent",
    "validate_coordinate_geometry_output",
    "get_coordinate_geometry_context_for_classification",
    # Mathematics - Geometric Figure
    "generate_geometric_figure",
    "create_geometric_figure_agent",
    "validate_geometric_figure_output",
    "get_geometric_figure_context_for_classification",
    # Mathematics - Number Line
    "generate_number_line",
    "create_number_line_agent",
    "validate_number_line_output",
    "get_number_line_context_for_classification",
    # Mathematics - Venn Diagram
    "generate_venn_diagram",
    "create_venn_diagram_agent",
    "validate_venn_diagram_output",
    "get_venn_diagram_context_for_classification",
    # Router
    "route_tikz_agent",
    "generate_tikz_with_routing",
    "get_agent_capabilities",
    # MCQ Option Coordinator
    "generate_mcq_options",
    # Checker
    "check_tikz",
    "check_tikz_with_patch",
    "create_tikz_checker_agent",
    "create_tikz_patch_agent",
    "parse_check_result",
    "has_tikz_passed",
    "has_tikz_environment",
]
