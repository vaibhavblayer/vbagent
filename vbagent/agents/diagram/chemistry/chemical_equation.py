"""Chemical equation agent using mhchem.

Generates chemical equations for reactions, equilibria, kinetics, and thermodynamics.
"""

from typing import Optional

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.prompts.diagram.chemistry.chemical_equation import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    USER_TEMPLATE_FROM_PROBLEM,
)
from vbagent.references.store import ReferenceStore
from vbagent.utils.latex import clean_latex_output


def create_chemical_equation_agent(use_context: bool = True) -> "Agent":
    """Create a chemical equation generation agent.
    
    Args:
        use_context: Whether to include reference context
        
    Returns:
        Configured Agent instance
    """
    prompt = SYSTEM_PROMPT
    
    if use_context:
        context = get_chemical_equation_context_for_classification()
        if context:
            prompt = prompt + "\n\n" + context
    
    return create_agent(
        name="ChemicalEquation",
        instructions=prompt,
        agent_type="tikz",
    )


def generate_chemical_equation(
    image_path: Optional[str] = None,
    description: Optional[str] = None,
    use_context: bool = True,
    show_spinner: bool = True,
) -> str:
    """Generate mhchem code for a chemical equation.
    
    Args:
        image_path: Path to equation image (optional)
        description: Text description of equation (optional)
        use_context: Whether to include reference context
        show_spinner: Whether to show animated spinner
        
    Returns:
        mhchem code as string
    """
    if not image_path and not description:
        raise ValueError("Either image_path or description must be provided")
    
    agent = create_chemical_equation_agent(use_context)
    
    if image_path:
        message = create_image_message(image_path, USER_TEMPLATE)
    else:
        message = [{"role": "user", "content": USER_TEMPLATE_FROM_PROBLEM.format(problem=description)}]
    
    raw_output = run_agent_sync(agent, message, show_spinner=show_spinner)
    return clean_latex_output(raw_output)


def validate_chemical_equation_output(mhchem_code: str) -> tuple[bool, str]:
    """Validate mhchem code for chemical equations.
    
    Args:
        mhchem_code: The mhchem code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not mhchem_code or not mhchem_code.strip():
        return False, "Empty mhchem code"
    
    # Check for \ce command
    if "\\ce{" not in mhchem_code:
        return False, "Missing \\ce{} command"
    
    # Check for balanced braces
    open_count = mhchem_code.count("{")
    close_count = mhchem_code.count("}")
    if open_count != close_count:
        return False, f"Unbalanced braces: {open_count} open, {close_count} close"
    
    # Check for reaction arrow
    has_arrow = any(arrow in mhchem_code for arrow in ["->", "<=>", "<->", "<<=>"])
    if not has_arrow:
        # Might be just a formula, which is okay
        pass
    
    return True, ""


def get_chemical_equation_context_for_classification() -> str:
    """Get reference context for chemical equation generation.
    
    Returns:
        Context string with relevant examples
    """
    store = ReferenceStore()
    
    results = store.search(
        query="chemical equation reaction mhchem equilibrium redox",
        file_types=["sty", "tex", "pdf"],
        max_results=3
    )
    
    if not results:
        return ""
    
    context = "\n\n## Reference Examples\n\n"
    context += "Here are some similar chemical equations from our reference library:\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"### Example {i}\n"
        context += f"```latex\n{result.content}\n```\n\n"
    
    return context
