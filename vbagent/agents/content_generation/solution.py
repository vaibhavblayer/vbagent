"""Solution generation agent for creating detailed solutions.

Stage 2 of the content generation pipeline:
- Takes scanned problem as input
- Generates step-by-step solution
- Identifies diagram requirements
- Uses subject-specific and type-specific prompts
"""

from typing import TYPE_CHECKING, Optional, Dict, List

if TYPE_CHECKING:
    from agents import Agent

from vbagent.agents.base import (
    create_agent,
    run_agent_sync,
)
from vbagent.config import get_config
from vbagent.prompts.content_generation.solution import (
    get_solution_prompt,
    get_user_template,
)
from vbagent.references.context import get_context_prompt_section
from vbagent.utils.latex import clean_latex_output


class DiagramRequirement:
    """Represents a diagram needed in the solution with rich context."""
    
    def __init__(
        self,
        diagram_id: str,
        diagram_type: str,
        description: str,
        location: str = "inline",
        # Rich context from solution agent
        context: Optional[str] = None,
        values: Optional[Dict[str, str]] = None,
        labels: Optional[List[str]] = None,
    ):
        self.diagram_id = diagram_id
        self.diagram_type = diagram_type
        self.description = description
        self.location = location
        
        # Rich context for diagram generation
        self.context = context  # Detailed explanation
        self.values = values or {}  # Variable values
        self.labels = labels or []  # Labels needed
    
    def __repr__(self):
        return f"DiagramRequirement(id={self.diagram_id}, type={self.diagram_type})"
    
    @classmethod
    def from_comment(cls, comment_text: str) -> "DiagramRequirement":
        """Parse diagram requirement from LaTeX comment.
        
        Expects format:
        % DIAGRAM_REQUIREMENT: {"id": "...", "type": "...", ...}
        
        Args:
            comment_text: LaTeX comment text
            
        Returns:
            DiagramRequirement instance
        """
        import json
        import re
        
        # Extract JSON from comment
        match = re.search(r'DIAGRAM_REQUIREMENT:\s*(\{.*?\})', comment_text, re.DOTALL)
        if not match:
            raise ValueError("Invalid diagram requirement format")
        
        # Parse JSON (handle multi-line)
        json_str = match.group(1)
        # Remove comment markers if present
        json_str = re.sub(r'%\s*', '', json_str)
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in diagram requirement: {json_str}")
        
        return cls(
            diagram_id=data["id"],
            diagram_type=data["type"],
            description=data["description"],
            location=data.get("location", "inline"),
            context=data.get("context"),
            values=data.get("values"),
            labels=data.get("labels"),
        )
    
    def get_enhanced_description(self) -> str:
        """Get enhanced description with all context for diagram agent.
        
        Returns:
            Enhanced description string
        """
        parts = [self.description]
        
        if self.context:
            parts.append(f"\n\n**Context:** {self.context}")
        
        if self.values:
            values_str = ", ".join([f"{k}={v}" for k, v in self.values.items()])
            parts.append(f"\n\n**Values:** {values_str}")
        
        if self.labels:
            labels_str = ", ".join(self.labels)
            parts.append(f"\n\n**Labels needed:** {labels_str}")
        
        return "".join(parts)


class SolutionResult:
    """Result from solution generation."""
    
    def __init__(
        self,
        solution_latex: str,
        diagram_requirements: List[DiagramRequirement],
        raw_output: str,
    ):
        self.solution_latex = solution_latex
        self.diagram_requirements = diagram_requirements
        self.raw_output = raw_output
    
    def __repr__(self):
        return f"SolutionResult(diagrams={len(self.diagram_requirements)})"


def create_solution_agent(
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
) -> "Agent":
    """Create a solution generation agent with type-specific prompt.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, subjective, etc.)
        use_context: Whether to include reference context in prompt
        subject: Subject override (uses config if not provided)
        
    Returns:
        Configured Agent instance for solution generation with structured output
    """
    from vbagent.models.solution import SolutionOutput
    from agents import AgentOutputSchema
    
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    prompt = get_solution_prompt(question_type, subject)
    
    # Add reference context if enabled
    context = get_context_prompt_section("solution", use_context)
    if context:
        prompt = prompt + "\n" + context
    
    return create_agent(
        name=f"Solution-{question_type}-{subject}",
        instructions=prompt,
        agent_type="content_generation.solution",
        output_type=AgentOutputSchema(SolutionOutput, strict_json_schema=False),  # ← Disable strict mode
    )


def extract_diagram_requirements(latex: str) -> List[DiagramRequirement]:
    """Extract diagram requirements from LaTeX with rich context.
    
    Looks for two patterns:
    1. Rich format: % DIAGRAM_REQUIREMENT: {...json...}
    2. Simple format: % PLACEHOLDER: diagram_id (fallback)
    
    Args:
        latex: LaTeX string with diagram requirements
        
    Returns:
        List of DiagramRequirement objects
    """
    import re
    
    requirements = []
    
    # Pattern 1: Rich format with JSON
    # % DIAGRAM_REQUIREMENT: {...}
    rich_pattern = r'%\s*DIAGRAM_REQUIREMENT:\s*(\{[^}]*\})'
    rich_matches = re.finditer(rich_pattern, latex, re.DOTALL)
    
    for match in rich_matches:
        try:
            comment_text = match.group(0)
            req = DiagramRequirement.from_comment(comment_text)
            requirements.append(req)
        except Exception as e:
            # Skip invalid formats
            continue
    
    # Pattern 2: Simple placeholder format (fallback)
    # % PLACEHOLDER: diagram_id
    if not requirements:
        placeholder_pattern = r'%\s*PLACEHOLDER:\s*(\w+)'
        placeholder_matches = re.finditer(placeholder_pattern, latex)
        
        for match in placeholder_matches:
            diagram_id = match.group(1)
            # Try to infer type from ID
            diagram_type = infer_diagram_type(diagram_id, "")
            
            requirements.append(DiagramRequirement(
                diagram_id=diagram_id,
                diagram_type=diagram_type,
                description=f"Diagram {diagram_id}",
                location="inline"
            ))
    
    return requirements


def infer_diagram_type(diagram_id: str, description: str) -> str:
    """Infer diagram type from ID or description.
    
    Args:
        diagram_id: The diagram placeholder ID
        description: The diagram description
        
    Returns:
        Inferred diagram type (fbd, circuit, graph, etc.)
    """
    # Check ID first
    id_lower = diagram_id.lower()
    if "fbd" in id_lower or "force" in id_lower:
        return "fbd"
    elif "circuit" in id_lower:
        return "circuit"
    elif "graph" in id_lower or "plot" in id_lower:
        return "graph"
    elif "optics" in id_lower or "ray" in id_lower:
        return "optics"
    elif "vector" in id_lower:
        return "vector"
    
    # Check description
    desc_lower = description.lower()
    if "free body" in desc_lower or "forces" in desc_lower:
        return "fbd"
    elif "circuit" in desc_lower or "resistor" in desc_lower or "capacitor" in desc_lower:
        return "circuit"
    elif "graph" in desc_lower or "plot" in desc_lower or " vs " in desc_lower:
        return "graph"
    elif "ray" in desc_lower or "lens" in desc_lower or "mirror" in desc_lower:
        return "optics"
    elif "vector" in desc_lower:
        return "vector"
    elif "structure" in desc_lower or "molecule" in desc_lower:
        return "organic_structure"
    elif "orbital" in desc_lower:
        return "orbital"
    elif "energy diagram" in desc_lower:
        return "energy_diagram"
    
    # Default to generic
    return "generic"


def generate_solution(
    problem: str,
    question_type: str,
    options: Optional[List[str]] = None,
    use_context: bool = True,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> SolutionResult:
    """Generate a detailed solution for a problem.
    
    Args:
        problem: The problem statement (LaTeX)
        question_type: Type of question (mcq_sc, subjective, etc.)
        options: List of options for MCQ (optional)
        use_context: Whether to include reference context
        subject: Subject override (uses config if not provided)
        show_spinner: Whether to show animated spinner
        
    Returns:
        SolutionResult with solution LaTeX and diagram requirements
    """
    from vbagent.models.solution import SolutionOutput
    
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    # Create agent with structured output
    agent = create_solution_agent(question_type, use_context, subject)
    
    # Format user message
    user_template = get_user_template(subject)
    options_text = ""
    if options:
        options_text = "Options:\n" + "\n".join(options)
    
    user_message = user_template.format(
        problem=problem,
        options=options_text
    )
    
    # Generate solution - returns SolutionOutput model
    output: SolutionOutput = run_agent_sync(agent, user_message, show_spinner=show_spinner)
    
    # Convert to SolutionResult
    diagram_requirements = []
    for req in output.diagram_requirements:
        diagram_requirements.append(DiagramRequirement(
            diagram_id=f"diagram_{len(diagram_requirements) + 1}",
            diagram_type=req.diagram_type,
            description=req.description,
            location=req.location,
            context=req.context,
            values=req.values,
            labels=req.labels,
        ))
    
    return SolutionResult(
        solution_latex=output.solution_latex,
        diagram_requirements=diagram_requirements,
        raw_output=output.model_dump_json(indent=2),
    )


__all__ = [
    "create_solution_agent",
    "generate_solution",
    "DiagramRequirement",
    "SolutionResult",
    "extract_diagram_requirements",
    "infer_diagram_type",
]



def generate_diagram_with_context(
    requirement: DiagramRequirement,
    original_image_path: str,
    problem_text: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> str:
    """Generate diagram with rich context from solution.
    
    Args:
        requirement: DiagramRequirement with rich context
        original_image_path: Path to original problem image (visual reference)
        problem_text: Scanned problem text for context
        subject: Subject for routing (uses config if not provided)
        show_spinner: Whether to show animated spinner
        
    Returns:
        TikZ code for the diagram
    """
    from vbagent.config import get_config
    from vbagent.agents.diagram.tikz_router import generate_tikz_with_routing
    
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    # Generate with routing to appropriate agent
    tikz_code, agent_used = generate_tikz_with_routing(
        image_path=original_image_path,  # Visual reference
        description=requirement.description,  # Brief description
        subject=subject,
        diagram_type=requirement.diagram_type,
        show_spinner=show_spinner,
        # NEW: Pass rich context
        problem_text=problem_text,
        solution_context=requirement.context,
        values=requirement.values,
        labels=requirement.labels,
    )
    
    return tikz_code


def generate_complete_solution(
    image_path: str,
    classification,
    problem_text: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> str:
    """Complete pipeline: solution → diagrams → assembly.
    
    Note: Expects problem_text to be already scanned.
    
    Args:
        image_path: Path to original problem image
        classification: ClassificationResult
        problem_text: Already scanned problem text (LaTeX)
        subject: Subject override (uses config if not provided)
        show_spinner: Whether to show animated spinner
        
    Returns:
        Complete solution LaTeX with diagrams
    """
    from vbagent.config import get_config
    
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    # Stage 1: Generate solution with diagram requirements
    solution_result = generate_solution(
        problem=problem_text,
        question_type=classification.question_type,
        subject=subject,
        show_spinner=show_spinner,
    )
    
    # Stage 2: Generate diagrams with rich context
    final_solution = solution_result.solution_latex
    
    for req in solution_result.diagram_requirements:
        tikz_code = generate_diagram_with_context(
            requirement=req,
            original_image_path=image_path,  # Visual reference
            problem_text=problem_text,  # Problem context
            subject=subject,
            show_spinner=show_spinner,
        )
        
        # Replace placeholder
        # Try both formats: "% DIAGRAM PLACEHOLDER:" and "% PLACEHOLDER:"
        placeholder1 = f"% DIAGRAM PLACEHOLDER: {req.diagram_id}"
        placeholder2 = f"% PLACEHOLDER: {req.diagram_id}"
        
        # Wrap TikZ code in center environment
        tikz_with_center = f"\n\\begin{{center}}\n{tikz_code}\n\\end{{center}}\n"
        
        if placeholder1 in final_solution:
            final_solution = final_solution.replace(placeholder1, tikz_with_center)
        elif placeholder2 in final_solution:
            final_solution = final_solution.replace(placeholder2, tikz_with_center)
    
    return final_solution


__all__ = [
    "create_solution_agent",
    "generate_solution",
    "DiagramRequirement",
    "SolutionResult",
    "extract_diagram_requirements",
    "infer_diagram_type",
    "generate_diagram_with_context",
    "generate_complete_solution",
]
