"""Idea extraction agent for problems across subjects.

Uses openai-agents SDK to analyze problems and solutions,
extracting core concepts, formulas, techniques, and difficulty factors.
Subject-aware: adapts prompts for physics, chemistry, mathematics.
"""

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.content import IdeaResult
from vbagent.prompts.content_generation.idea import (
    get_system_prompt_json,
    get_system_prompt_latex,
    USER_TEMPLATE,
    USER_TEMPLATE_JSON,
)
from vbagent.utils.latex import clean_latex_output


def _get_subject() -> str:
    """Get configured subject."""
    from vbagent.config import get_config
    return get_config().subject


def _create_idea_agent_json(subject: str | None = None) -> "Agent":
    """Create idea agent with subject-aware prompt."""
    subject = subject or _get_subject()
    return create_agent(
        name="IdeaJSON",
        instructions=get_system_prompt_json(subject),
        output_type=IdeaResult,
        agent_type="idea",
    )


def _create_idea_agent_latex(subject: str | None = None) -> "Agent":
    """Create idea agent for LaTeX output."""
    subject = subject or _get_subject()
    return create_agent(
        name="IdeaLaTeX",
        instructions=get_system_prompt_latex(subject),
        agent_type="idea",
    )


def extract_ideas(
    problem_latex: str,
    solution_latex: str,
    subject: str | None = None,
) -> IdeaResult:
    """Extract core concepts and techniques from a problem (JSON output).
    
    Args:
        problem_latex: The problem statement in LaTeX format
        solution_latex: The solution in LaTeX format
        subject: Subject override (physics/chemistry/mathematics)
        
    Returns:
        IdeaResult with extracted concepts, formulas, techniques,
        and difficulty factors
    """
    if not problem_latex.strip() and not solution_latex.strip():
        raise ValueError("Both problem and solution cannot be empty")
    
    agent = _create_idea_agent_json(subject)
    message = USER_TEMPLATE_JSON.format(
        problem=problem_latex,
        solution=solution_latex,
    )
    return run_agent_sync(agent, message)


def generate_idea_latex(
    full_content: str,
    subject: str | None = None,
) -> str:
    """Generate idea extraction in LaTeX format for appending to files.
    
    Args:
        full_content: Full LaTeX file content
        subject: Subject override
        
    Returns:
        LaTeX string with idea environment
    """
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    
    agent = _create_idea_agent_latex(subject)
    message = USER_TEMPLATE.replace('{full_content}', full_content)
    raw_result = run_agent_sync(agent, message)
    return clean_latex_output(raw_result)


def has_idea_environment(content: str) -> bool:
    """Check if content already has an idea environment."""
    return r'\begin{idea}' in content


def count_idea_environments(content: str) -> int:
    """Count the number of idea environments in content."""
    return content.count(r'\begin{idea}')
