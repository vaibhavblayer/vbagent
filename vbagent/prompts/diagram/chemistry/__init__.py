"""Chemistry-specific diagram prompts.

Specialized prompts for chemistry diagrams:
- Organic Structure: Molecular structures using chemfig (general)
- Organic Simple: Simple molecules (chains, rings, functional groups)
- Organic Mechanism: Reaction mechanisms with electron movement
- Organic Stereo: Stereochemistry with wedge-dash bonds
- Organic Complex: Complex molecules (steroids, natural products)
- Organic Functional: Functional group transformations
- Organic MultiStep: Multi-step syntheses
- Reaction Mechanism: Reaction mechanisms with arrow-pushing
- Orbital: Atomic and molecular orbital diagrams
- Lewis Structure: Lewis structures with lone pairs
- Chemical Equation: Chemical equations using mhchem
- Energy Diagram: Thermodynamics and reaction coordinate diagrams
"""

from .organic_structure import SYSTEM_PROMPT as ORGANIC_STRUCTURE_PROMPT
from .reaction_mechanism import SYSTEM_PROMPT as REACTION_MECHANISM_PROMPT
from .orbital import SYSTEM_PROMPT as ORBITAL_PROMPT
from .lewis_structure import SYSTEM_PROMPT as LEWIS_STRUCTURE_PROMPT
from .chemical_equation import SYSTEM_PROMPT as CHEMICAL_EQUATION_PROMPT
from .energy_diagram import SYSTEM_PROMPT as ENERGY_DIAGRAM_PROMPT

# Organic chemistry specialist prompts
from . import organic_simple
from . import organic_mechanism
from . import organic_stereo
from . import organic_complex
from . import organic_functional
from . import organic_multistep

__all__ = [
    "ORGANIC_STRUCTURE_PROMPT",
    "REACTION_MECHANISM_PROMPT",
    "ORBITAL_PROMPT",
    "LEWIS_STRUCTURE_PROMPT",
    "CHEMICAL_EQUATION_PROMPT",
    "ENERGY_DIAGRAM_PROMPT",
    "organic_simple",
    "organic_mechanism",
    "organic_stereo",
    "organic_complex",
    "organic_functional",
    "organic_multistep",
]
