"""Agent 2: Diagram Analyzer.

Analyzes diagrams in detail and determines TikZ requirements.
Routes to specialized TikZ agents based on diagram type.
"""

from typing import Optional

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import DiagramAnalysis, PrimaryClassification
from vbagent.prompts.classification.diagram_analyzer import get_diagram_analyzer_prompt


def create_diagram_analyzer_agent(subject: Optional[str] = None):
    """Create diagram analyzer agent."""
    if subject is None:
        subject = get_config().subject

    prompt = get_diagram_analyzer_prompt(subject)

    return create_agent(
        name=f"DiagramAnalyzer-{subject}",
        instructions=prompt,
        output_type=DiagramAnalysis,
        agent_type="classifier",
    )


def analyze_diagram(
    image_path: str,
    primary: PrimaryClassification,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> DiagramAnalysis:
    """Analyze diagram in detail (Agent 2).

    Args:
        image_path: Path to question image
        primary: Primary classification result
        subject: Subject override
        show_spinner: Whether to show animated spinner

    Returns:
        DiagramAnalysis with TikZ requirements
    """
    if subject is None:
        subject = primary.subject

    agent = create_diagram_analyzer_agent(subject)

    context = f"""Analyze the diagram in this {subject} question.
Question type: {primary.question_type}
Has diagram: {primary.has_diagram}

Focus on diagram structure, elements, and TikZ generation requirements."""

    message = create_image_message(image_path, context)
    return run_agent_sync(agent, message, show_spinner=show_spinner)


def analyze_diagram_from_description(
    description: str,
    primary: PrimaryClassification,
    subject: Optional[str] = None,
) -> DiagramAnalysis:
    """Analyze diagram from text description (for generated problems).

    Args:
        description: Text description of the diagram
        primary: Primary classification result
        subject: Subject override

    Returns:
        DiagramAnalysis with TikZ requirements
    """
    if subject is None:
        subject = primary.subject

    agent = create_diagram_analyzer_agent(subject)

    context = f"""Analyze this diagram based on its description.

**Question Context:**
- Type: {primary.question_type}
- Has diagram: {primary.has_diagram}

**Diagram Description:**
{description}

Provide diagram analysis including type, elements, complexity, and TikZ requirements."""

    return run_agent_sync(agent, context, show_spinner=False)
