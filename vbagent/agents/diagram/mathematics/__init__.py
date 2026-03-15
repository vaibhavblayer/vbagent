"""Mathematics-specific diagram agents.

Specialized agents for mathematics diagrams:
- Function Graph: Function plots, calculus, tangents, normals
- Coordinate Geometry: Lines, circles, conics, analytical geometry
- Geometric Figure: Triangles, polygons, pure geometry
- Number Line: Number lines, inequalities, intervals
- Venn Diagram: Set theory, Venn diagrams, set operations
"""

from .function_graph import (
    generate_function_graph,
    create_function_graph_agent,
    validate_function_graph_output,
    get_function_graph_context_for_classification,
)
from .coordinate_geometry import (
    generate_coordinate_geometry,
    create_coordinate_geometry_agent,
    validate_coordinate_geometry_output,
    get_coordinate_geometry_context_for_classification,
)
from .geometric_figure import (
    generate_geometric_figure,
    create_geometric_figure_agent,
    validate_geometric_figure_output,
    get_geometric_figure_context_for_classification,
)
from .number_line import (
    generate_number_line,
    create_number_line_agent,
    validate_number_line_output,
    get_number_line_context_for_classification,
)
from .venn_diagram import (
    generate_venn_diagram,
    create_venn_diagram_agent,
    validate_venn_diagram_output,
    get_venn_diagram_context_for_classification,
)

__all__ = [
    # Function Graph
    "generate_function_graph",
    "create_function_graph_agent",
    "validate_function_graph_output",
    "get_function_graph_context_for_classification",
    # Coordinate Geometry
    "generate_coordinate_geometry",
    "create_coordinate_geometry_agent",
    "validate_coordinate_geometry_output",
    "get_coordinate_geometry_context_for_classification",
    # Geometric Figure
    "generate_geometric_figure",
    "create_geometric_figure_agent",
    "validate_geometric_figure_output",
    "get_geometric_figure_context_for_classification",
    # Number Line
    "generate_number_line",
    "create_number_line_agent",
    "validate_number_line_output",
    "get_number_line_context_for_classification",
    # Venn Diagram
    "generate_venn_diagram",
    "create_venn_diagram_agent",
    "validate_venn_diagram_output",
    "get_venn_diagram_context_for_classification",
]
