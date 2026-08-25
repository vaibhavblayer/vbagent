"""Scanner agent for extracting LaTeX from question images.

Uses openai-agents SDK to analyze question images and extract
LaTeX code using type-specific and subject-specific prompts.
"""

import re
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
from vbagent.prompts.content_generation.table_format import TABLE_FORMAT_RULES
from vbagent.references.context import get_context_prompt_section
from vbagent.utils.latex import clean_latex_output, use_plain_enumerates


_MATCH_OPTIONS_RETRY = r"""
Your previous extraction was invalid because every match-type question must
contain exactly four code options, even when the source image contains only the
two columns. Re-extract the complete question. If code options are absent or
incomplete in the source, infer the correct complete matching and synthesize
four distinct options in \begin{tasks}(2)...\end{tasks}; include the correct
matching exactly once. Keep each option in one $\mathrm{...}$ expression. For
one-to-many mappings use grouped targets such as P\rightarrow\{I,III\}. Return
only the required LaTeX.
"""

_SUBJECTIVE_STRUCTURE_RETRY = r"""
Your previous extraction was invalid because this question is classified as
subjective. A subjective question must not contain an OPTIONS_DIAGRAMS marker,
an OptionA/OptionB macro reference, a tasks environment, or any \task command.
Roman-labeled figures such as (i)--(x) that the student must compare or classify
form one standalone/main diagram collection in the question stem; they are not
answer options. Re-extract the complete subjective question using exactly one
main `\input{diagram}` placeholder and no option structure. Preserve genuine
textual subparts with plain `\begin{enumerate}` and let nesting determine their
labels. Do not add label options or counter commands. Return only the required
LaTeX.
"""


_FORBIDDEN_SUBJECTIVE_STRUCTURE_RE = re.compile(
    r"OPTIONS_DIAGRAMS|\\begin\{tasks\}|\\end\{tasks\}|"
    r"\\task\b|\\Option[A-Z]\b",
    flags=re.IGNORECASE,
)


def _has_forbidden_subjective_structure(latex: Optional[str]) -> bool:
    """Return whether subjective LaTeX leaked MCQ option structure."""
    if not latex:
        return False
    return bool(_FORBIDDEN_SUBJECTIVE_STRUCTURE_RE.search(latex))


def _has_required_match_options(latex: str) -> bool:
    """Return whether a match extraction has one four-option tasks block."""
    blocks = re.findall(
        r"\\begin\{tasks\}\(2\)(.*?)\\end\{tasks\}",
        latex,
        flags=re.DOTALL,
    )
    return any(len(re.findall(r"\\task\b", block)) == 4 for block in blocks)


def _scan_with_structure_gate(
    agent,
    image_path: str,
    user_template: str,
    question_type: str,
    show_spinner: bool,
) -> str:
    """Run a scan and retry once when its type-level structure is invalid."""
    message = create_image_message(image_path, user_template)
    raw_latex = run_agent_sync(agent, message, show_spinner=show_spinner)
    latex = clean_latex_output(raw_latex)
    if question_type == "subjective":
        latex = use_plain_enumerates(latex)

    if question_type == "subjective" and _has_forbidden_subjective_structure(latex):
        retry_message = create_image_message(
            image_path,
            f"{user_template}\n\n{_SUBJECTIVE_STRUCTURE_RETRY}",
        )
        raw_latex = run_agent_sync(
            agent,
            retry_message,
            show_spinner=show_spinner,
        )
        latex = clean_latex_output(raw_latex)
        latex = use_plain_enumerates(latex)
        if _has_forbidden_subjective_structure(latex):
            raise ValueError(
                "Subjective extraction contains forbidden MCQ option structure"
            )
        return latex

    if question_type != "match" or _has_required_match_options(latex):
        return latex
    retry_message = create_image_message(
        image_path,
        f"{user_template}\n\n{_MATCH_OPTIONS_RETRY}",
    )
    raw_latex = run_agent_sync(agent, retry_message, show_spinner=show_spinner)
    latex = clean_latex_output(raw_latex)
    if not _has_required_match_options(latex):
        raise ValueError(
            "Match extraction is missing the mandatory four-option tasks block"
        )
    return latex


def create_scanner_agent(
    question_type: str,
    use_context: bool = True,
    subject: Optional[str] = None,
    sample_reference: Optional[str] = None,
) -> "Agent":
    """Create a scanner agent with type-specific prompt.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, etc.)
        use_context: Whether to include reference context in prompt
        subject: Subject override (uses config if not provided)
        sample_reference: Optional golden sample .tex for formatting reference
        
    Returns:
        Configured Agent instance for scanning that question type
    """
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    prompt = get_scanner_prompt(question_type, subject)
    
    # Add golden sample as formatting reference
    if sample_reference:
        prompt = prompt + "\n\n## Formatting Reference (Golden Sample)\n\nYour output MUST match this exact formatting style:\n\n```latex\n" + sample_reference + "\n```\n"
    
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
    sample_reference: Optional[str] = None,
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
        sample_reference: Optional golden sample .tex for formatting reference
        
    Returns:
        ScanResult with extracted LaTeX and diagram info
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    # Get subject from config if not provided
    if subject is None:
        subject = get_config().subject
    
    agent = create_scanner_agent(classification.question_type, use_context, subject, sample_reference=sample_reference)
    user_template = get_user_template(subject)
    latex = _scan_with_structure_gate(
        agent,
        image_path,
        user_template,
        classification.question_type,
        show_spinner,
    )
    
    return ScanResult(
        latex=latex,
        has_diagram=classification.has_diagram,
        raw_diagram_description=getattr(classification, 'diagram_type', None),
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
    latex = _scan_with_structure_gate(
        agent,
        image_path,
        user_template,
        question_type,
        True,
    )
    
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
    sample_reference: Optional[str] = None,
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
        sample_reference: Optional golden sample .tex for formatting reference
        
    Returns:
        LaTeX string with problem statement only
    """
    import importlib

    if subject is None:
        subject = get_config().subject

    # Import subject-specific problem_only module
    mod = importlib.import_module(
        f"vbagent.prompts.content_generation.scanner.{subject}.problem_only"
    )
    system_prompt = mod.get_problem_prompt(question_type) + "\n\n" + TABLE_FORMAT_RULES
    user_template = mod.USER_TEMPLATE

    # Add golden sample as formatting reference
    if sample_reference:
        system_prompt += (
            "\n\n## Formatting Reference (Golden Sample)\n\n"
            "Your output MUST match this exact formatting style:\n\n"
            "```latex\n" + sample_reference + "\n```\n"
        )

    # Add context if requested
    if use_context:
        context_section = get_context_prompt_section("latex", use_context)
        if context_section:
            system_prompt += "\n" + context_section

    agent = create_agent(
        name=f"ProblemScanner-{question_type}-{subject}",
        instructions=system_prompt,
        agent_type="scanner",
    )

    return _scan_with_structure_gate(
        agent,
        image_path,
        user_template,
        question_type,
        show_spinner,
    )


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
    from vbagent.prompts.content_generation.scanner.solution_only import get_solution_prompt, USER_TEMPLATE
    
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
