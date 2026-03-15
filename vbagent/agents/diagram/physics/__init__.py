"""Physics-specific diagram agents.

Specialized agents for physics diagrams:
- FBD: Free body diagrams
- Circuit: Electrical circuits
- Graph: Function plots and data visualization
- Optics: Ray diagrams and optical systems
"""

from .fbd import generate_fbd, create_fbd_agent, validate_fbd_output, get_fbd_context_for_classification
from .circuit import generate_circuit, create_circuit_agent, validate_circuit_output, get_circuit_context_for_classification
from .graph import generate_graph, create_graph_agent, validate_graph_output, get_graph_context_for_classification
from .optics import generate_optics, create_optics_agent, validate_optics_output, get_optics_context_for_classification

__all__ = [
    # FBD
    "generate_fbd",
    "create_fbd_agent",
    "validate_fbd_output",
    "get_fbd_context_for_classification",
    # Circuit
    "generate_circuit",
    "create_circuit_agent",
    "validate_circuit_output",
    "get_circuit_context_for_classification",
    # Graph
    "generate_graph",
    "create_graph_agent",
    "validate_graph_output",
    "get_graph_context_for_classification",
    # Optics
    "generate_optics",
    "create_optics_agent",
    "validate_optics_output",
    "get_optics_context_for_classification",
]
