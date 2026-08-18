"""Format converter agent for physics questions.

Uses openai-agents SDK to convert questions between different formats:
- MCQ (single/multiple correct)
- Subjective
- Integer type
"""

from typing import Literal

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.utils.latex import clean_latex_output
from vbagent.prompts.content_generation.converter import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    get_format_instructions,
)
from vbagent.agents.content_generation.scanner import _has_required_match_options


# Valid format types
FormatType = Literal["mcq_sc", "mcq_mc", "subjective", "integer", "match", "passage"]

VALID_FORMATS = {"mcq_sc", "mcq_mc", "subjective", "integer", "match", "passage"}


# Create the format converter agent
converter_agent = create_agent(
    name="FormatConverter",
    instructions=SYSTEM_PROMPT,
    agent_type="converter",
)


def convert_format(
    source_latex: str,
    source_format: FormatType,
    target_format: FormatType,
) -> str:
    """Convert a physics question from one format to another.
    
    Converts questions between MCQ (single/multiple correct),
    subjective, and integer type formats while preserving the
    core physics content and difficulty level.
    
    Args:
        source_latex: The source question in LaTeX format
        source_format: The format of the source question
        target_format: The desired target format
        
    Returns:
        Converted question in LaTeX format with solution
        
    Raises:
        ValueError: If source_latex is empty or formats are invalid
    """
    if not source_latex.strip():
        raise ValueError("Source LaTeX cannot be empty")
    
    if source_format not in VALID_FORMATS:
        raise ValueError(
            f"Invalid source format: {source_format}. "
            f"Must be one of: {', '.join(VALID_FORMATS)}"
        )
    
    if target_format not in VALID_FORMATS:
        raise ValueError(
            f"Invalid target format: {target_format}. "
            f"Must be one of: {', '.join(VALID_FORMATS)}"
        )
    
    # Get format-specific instructions for the target
    format_instructions = get_format_instructions(target_format)
    
    # Format the user message
    message = USER_TEMPLATE.format(
        source_format=source_format,
        target_format=target_format,
        source_latex=source_latex,
        format_specific_instructions=format_instructions,
    )
    
    raw_result = run_agent_sync(converter_agent, message)
    converted = clean_latex_output(raw_result)

    if target_format == "match" and not _has_required_match_options(converted):
        retry_message = (
            f"{message}\n\n"
            "The previous conversion was invalid because it omitted the "
            "mandatory four match-code options. Return the complete corrected "
            "match question with exactly four distinct options inside "
            "\\begin{tasks}(2)...\\end{tasks}, even if the source had no "
            "options. For one-to-many mappings, keep grouped targets on the "
            "same arrow, such as P\\rightarrow\\{I,III\\}.\n\n"
            f"Previous invalid output:\n{converted}"
        )
        raw_result = run_agent_sync(converter_agent, retry_message)
        converted = clean_latex_output(raw_result)
        if not _has_required_match_options(converted):
            raise ValueError(
                "Match conversion is missing the mandatory four-option tasks block"
            )

    return converted
