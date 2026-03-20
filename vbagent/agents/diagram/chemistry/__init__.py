"""Chemistry-specific diagram agents.

Specialized agents for chemistry diagrams:
- Organic Structure: Molecular structures using chemfig (general)
- Organic Orchestrator: Intelligent routing for organic diagrams
- Organic Simple: Simple molecules specialist
- Organic Mechanism: Reaction mechanisms specialist
- Organic Stereo: Stereochemistry specialist
- Organic Complex: Complex molecules specialist
- Organic Functional: Functional group transformations specialist
- Organic MultiStep: Multi-step syntheses specialist
- Reaction Mechanism: Reaction mechanisms with arrow-pushing
- Orbital: Atomic and molecular orbital diagrams
- Lewis Structure: Lewis structures with lone pairs
- Chemical Equation: Chemical equations using mhchem
- Energy Diagram: Thermodynamics and reaction coordinate diagrams
"""

from .organic_structure import (
    generate_organic_structure,
    create_organic_structure_agent,
    validate_organic_structure_output,
    get_organic_structure_context_for_classification,
)
from .organic_orchestrator import (
    generate_organic_orchestrated,
    OrganicChemistryOrchestrator,
)
from .organic_simple import generate_simple_molecule
from .organic_mechanism import generate_mechanism
from .organic_stereo import generate_stereochemistry
from .organic_complex import generate_complex_molecule
from .organic_functional import generate_functional_group_transformation
from .organic_multistep import generate_multi_step_synthesis
from .reaction_mechanism import (
    generate_reaction_mechanism,
    create_reaction_mechanism_agent,
    validate_reaction_mechanism_output,
    get_reaction_mechanism_context_for_classification,
)
from .orbital import (
    generate_orbital,
    create_orbital_agent,
    validate_orbital_output,
    get_orbital_context_for_classification,
)
from .lewis_structure import (
    generate_lewis_structure,
    create_lewis_structure_agent,
    validate_lewis_structure_output,
    get_lewis_structure_context_for_classification,
)
from .chemical_equation import (
    generate_chemical_equation,
    create_chemical_equation_agent,
    validate_chemical_equation_output,
    get_chemical_equation_context_for_classification,
)
from .energy_diagram import (
    generate_energy_diagram,
    create_energy_diagram_agent,
    validate_energy_diagram_output,
    get_energy_diagram_context_for_classification,
)

__all__ = [
    # Organic Structure
    "generate_organic_structure",
    "create_organic_structure_agent",
    "validate_organic_structure_output",
    "get_organic_structure_context_for_classification",
    # Organic Orchestrator
    "generate_organic_orchestrated",
    "OrganicChemistryOrchestrator",
    # Organic Specialists
    "generate_simple_molecule",
    "generate_mechanism",
    "generate_stereochemistry",
    "generate_complex_molecule",
    "generate_functional_group_transformation",
    "generate_multi_step_synthesis",
    # Reaction Mechanism
    "generate_reaction_mechanism",
    "create_reaction_mechanism_agent",
    "validate_reaction_mechanism_output",
    "get_reaction_mechanism_context_for_classification",
    # Orbital
    "generate_orbital",
    "create_orbital_agent",
    "validate_orbital_output",
    "get_orbital_context_for_classification",
    # Lewis Structure
    "generate_lewis_structure",
    "create_lewis_structure_agent",
    "validate_lewis_structure_output",
    "get_lewis_structure_context_for_classification",
    # Chemical Equation
    "generate_chemical_equation",
    "create_chemical_equation_agent",
    "validate_chemical_equation_output",
    "get_chemical_equation_context_for_classification",
    # Energy Diagram
    "generate_energy_diagram",
    "create_energy_diagram_agent",
    "validate_energy_diagram_output",
    "get_energy_diagram_context_for_classification",
]
