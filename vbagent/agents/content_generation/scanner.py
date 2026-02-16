"""Scanner agent for extracting LaTeX from question images.

Uses openai-agents SDK to analyze question images and extract
LaTeX code using type-specific and subject-specific prompts.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agents import Agent

from vbagent.agents.base import (
    create_agent,
    create_image_message,
    run_agent_sync,
)
from vbagent.config import get_config
from vbagent.models.classification import ClassificationResult
from vbagent.models.content import ScanResult
from vbagent.prompts.content_generation.scanner import get_scanner_prompt, get_user_template
from vbagent.references.context import get_context_prompt_section
from vbagent.utils.latex import clean_latex_output


def create_scanner_agent(
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
) -> "Agent":
    """Create a scanner agent with type-specific prompt.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)
        use_context: Whether to include reference context in prompt
        subject: Subject override (uses config if not provided)
        
    Returns:
        Configured Agent instance for scanning that question type
    """
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    prompt = get_scanner_prompt(question_type, subject)
    
    # Add reference context if enabled
    context = get_context_prompt_section("latex", use_context)
    if context:
        prompt = prompt + "\n" + context
    
    return create_agent(
        name=f"Scanner-{question_type}-{subject}",
        instructions=prompt,
        agent_type="scanner",
    )


def scan(
    image_path: str,
    classification: ClassificationResult,
    use_context: bool = True,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> ScanResult:
    """Extract LaTeX from a question image.
    
    Uses the classification result to select the appropriate prompt
    for the question type.
    
    Args:
        image_path: Path to the image file to scan
        classification: Classification result with question type info
        use_context: Whether to include reference context in prompt
        subject: Subject override (uses config if not provided)
        show_spinner: Whether to show animated spinner (default: True)
        
    Returns:
        ScanResult with extracted LaTeX and diagram info
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    agent = create_scanner_agent(classification.question_type, use_context, subject)
    user_template = get_user_template(subject)
    message = create_image_message(image_path, user_template)
    raw_latex = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    # Clean up markdown artifacts from LLM output
    latex = clean_latex_output(raw_latex)
    
    return ScanResult(
        latex=latex,
        has_diagram=classification.has_diagram,
        raw_diagram_description=classification.diagram_type,
    )


def scan_with_type(
    image_path: str,
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
) -> ScanResult:
    """Extract LaTeX from a question image with explicit type.
    
    Bypasses classification and uses the provided question type directly.
    
    Args:
        image_path: Path to the image file to scan
        question_type: The type of question (mcq_sc, mcq_mc, etc.)
        use_context: Whether to include reference context in prompt
        subject: Subject override (uses config if not provided)
        
    Returns:
        ScanResult with extracted LaTeX
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    agent = create_scanner_agent(question_type, use_context, subject)
    user_template = get_user_template(subject)
    message = create_image_message(image_path, user_template)
    raw_latex = run_agent_sync(agent, message)
    
    # Clean up markdown artifacts from LLM output
    latex = clean_latex_output(raw_latex)
    
    return ScanResult(
        latex=latex,
        has_diagram=False,  # Unknown without classification
        raw_diagram_description=None,
    )



def scan_problem(
    image_path: str,
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> str:
    r"""Extract ONLY the problem statement from an image (no solution).
    
    Uses problem-only scanner to extract:
    - \item statement
    - Diagram placeholder (if present)
    - Options (for MCQ)
    
    Does NOT extract solution.
    
    Args:
        image_path: Path to the image file
        question_type: Type of question (mcq_sc, mcq_mc, subjective, etc.)
        use_context: Whether to include reference context
        subject: Subject override (uses config if not provided)
        show_spinner: Whether to show animated spinner
        
    Returns:
        LaTeX string with problem statement only
    """
    from vbagent.prompts.scanner.problem_only import get_problem_prompt, USER_TEMPLATE
    
    if subject is None:
        subject = get_config().subject
    
    # Get problem-only prompt
    system_prompt = get_problem_prompt(question_type)
    
    # Add context if requested
    if use_context:
        context_section = get_context_prompt_section(question_type, subject)
        if context_section:
            system_prompt = system_prompt + "\n\n" + context_section
    
    # Create agent
    agent = create_agent(
        name=f"ProblemScanner-{question_type}",
        instructions=system_prompt,
        agent_type="scanner",
    )
    
    # Run agent
    message = create_image_message(image_path, USER_TEMPLATE)
    raw_latex = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    # Clean output
    return clean_latex_output(raw_latex)


def scan_solution(
    image_path: str,
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> str:
    r"""Extract ONLY the solution from an image (no problem statement).
    
    Uses solution-only scanner to extract:
    - \begin{solution}...\end{solution} block
    
    Assumes problem statement already exists.
    
    Args:
        image_path: Path to the image file
        question_type: Type of question (mcq_sc, mcq_mc, subjective, etc.)
        use_context: Whether to include reference context
        subject: Subject override (uses config if not provided)
        show_spinner: Whether to show animated spinner
        
    Returns:
        LaTeX string with solution block only
    """
    from vbagent.prompts.scanner.solution_only import get_solution_prompt, USER_TEMPLATE
    
    if subject is None:
        subject = get_config().subject
    
    # Get solution-only prompt
    system_prompt = get_solution_prompt(question_type)
    
    # Add context if requested
    if use_context:
        context_section = get_context_prompt_section(question_type, subject)
        if context_section:
            system_prompt = system_prompt + "\n\n" + context_section
    
    # Create agent
    agent = create_agent(
        name=f"SolutionScanner-{question_type}",
        instructions=system_prompt,
        agent_type="scanner",
    )
    
    # Run agent
    message = create_image_message(image_path, USER_TEMPLATE)
    raw_latex = run_agent_sync(agent, message, show_spinner=show_spinner)
    
    # Clean output
    return clean_latex_output(raw_latex)
