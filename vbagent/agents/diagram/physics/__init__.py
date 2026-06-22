"""Physics-specific diagram agents.

Specialized agents for physics diagrams:
- FBD: Free body diagrams
- Circuit: Electrical circuits
- Gates: Digital logic circuits
- Graph: Function plots and data visualization
- Optics: Ray diagrams and optical systems
- Mechanics: Pulley systems, springs, inclines, rotational systems
- Wave: Wave propagation, reflection, transmission, standing waves
- Setup: Problem-side physical scene (apparatus/geometry, NO force vectors)
"""

from .fbd import generate_fbd, create_fbd_agent, validate_fbd_output, get_fbd_context_for_classification
from .setup import generate_setup, create_setup_agent, validate_setup_output, get_setup_context_for_classification
from .circuit import generate_circuit, create_circuit_agent, validate_circuit_output, get_circuit_context_for_classification
from .gates import generate_gates, create_gates_agent, validate_gates_output, get_gates_context_for_classification
from .graph import generate_graph, create_graph_agent, validate_graph_output, get_graph_context_for_classification
from .optics import generate_optics, create_optics_agent, validate_optics_output, get_optics_context_for_classification
from .mechanics import generate_mechanics, create_mechanics_agent, validate_mechanics_output, get_mechanics_context_for_classification
from .wave import generate_wave, create_wave_agent, validate_wave_output, get_wave_context_for_classification

__all__ = [
    # FBD
    "generate_fbd",
    "create_fbd_agent",
    "validate_fbd_output",
    "get_fbd_context_for_classification",
    # Setup (problem scene, no forces)
    "generate_setup",
    "create_setup_agent",
    "validate_setup_output",
    "get_setup_context_for_classification",
    # Circuit
    "generate_circuit",
    "create_circuit_agent",
    "validate_circuit_output",
    "get_circuit_context_for_classification",
    # Gates
    "generate_gates",
    "create_gates_agent",
    "validate_gates_output",
    "get_gates_context_for_classification",
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
    # Mechanics
    "generate_mechanics",
    "create_mechanics_agent",
    "validate_mechanics_output",
    "get_mechanics_context_for_classification",
    # Wave
    "generate_wave",
    "create_wave_agent",
    "validate_wave_output",
    "get_wave_context_for_classification",
]
