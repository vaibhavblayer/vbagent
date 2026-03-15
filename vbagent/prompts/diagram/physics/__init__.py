"""Physics-specific diagram prompts.

Specialized prompts for physics diagrams:
- FBD: Free body diagrams
- Circuit: Electrical circuits
- Graph: Function plots and data visualization
- Optics: Ray diagrams and optical systems
"""

from .fbd import SYSTEM_PROMPT as FBD_PROMPT
from .circuit import SYSTEM_PROMPT as CIRCUIT_PROMPT
from .graph import SYSTEM_PROMPT as GRAPH_PROMPT
from .optics import SYSTEM_PROMPT as OPTICS_PROMPT

__all__ = [
    "FBD_PROMPT",
    "CIRCUIT_PROMPT",
    "GRAPH_PROMPT",
    "OPTICS_PROMPT",
]
