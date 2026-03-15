"""Mathematics-specific diagram prompts.

Specialized prompts for mathematics diagrams:
- Function Graph: Function plots, calculus, tangents, normals
- Coordinate Geometry: Lines, circles, conics, analytical geometry
- Geometric Figure: Triangles, polygons, pure geometry
- Number Line: Number lines, inequalities, intervals
- Venn Diagram: Set theory, Venn diagrams, set operations
"""

from .function_graph import SYSTEM_PROMPT as FUNCTION_GRAPH_PROMPT
from .coordinate_geometry import SYSTEM_PROMPT as COORDINATE_GEOMETRY_PROMPT
from .geometric_figure import SYSTEM_PROMPT as GEOMETRIC_FIGURE_PROMPT
from .number_line import SYSTEM_PROMPT as NUMBER_LINE_PROMPT
from .venn_diagram import SYSTEM_PROMPT as VENN_DIAGRAM_PROMPT

__all__ = [
    "FUNCTION_GRAPH_PROMPT",
    "COORDINATE_GEOMETRY_PROMPT",
    "GEOMETRIC_FIGURE_PROMPT",
    "NUMBER_LINE_PROMPT",
    "VENN_DIAGRAM_PROMPT",
]
