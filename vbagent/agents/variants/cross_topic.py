"""Cross-topic variant agent for physics problems.

Multi-stage pipeline that creates variants by integrating complementary
physics topics into existing problems:

Stage 1: Topic Analyzer — picks the best topic to integrate and why
Stage 2: Cross-Topic Generator — creates the intermixed variant

Example: An electrostatics problem gets mechanics integrated →
a charged particle in an electric field also subject to gravity,
creating a parabolic trajectory problem.
"""

from typing import Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.content import IdeaResult, CrossTopicAnalysis
from vbagent.utils.latex import clean_latex_output
from vbagent.prompts.variants.cross_topic import (
    ANALYZER_SYSTEM_PROMPT,
    ANALYZER_USER_TEMPLATE,
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_TEMPLATE,
)


def _create_analyzer_agent():
    """Create the topic analyzer agent (Stage 1)."""
    return create_agent(
        name="CrossTopicAnalyzer",
        instructions=ANALYZER_SYSTEM_PROMPT,
        output_type=CrossTopicAnalysis,
        agent_type="variant",
    )


def _create_generator_agent(use_context: bool = True):
    """Create the cross-topic generator agent (Stage 2)."""
    from vbagent.references.context import get_context_prompt_section

    prompt = GENERATOR_SYSTEM_PROMPT
    context = get_context_prompt_section("variants", use_context)
    if context:
        prompt = prompt + "\n" + context

    return create_agent(
        name="CrossTopicGenerator",
        instructions=prompt,
        agent_type="variant",
    )


def analyze_cross_topic(
    source_latex: str,
    subject: str = "physics",
    topic: Optional[str] = None,
    question_type: str = "subjective",
    has_diagram: bool = False,
    key_concepts: Optional[list[str]] = None,
) -> CrossTopicAnalysis:
    """Stage 1: Analyze the source problem and pick the best integration topic.

    Args:
        source_latex: The source problem in LaTeX format
        subject: Subject of the problem
        topic: Known topic (from classification), or "unknown"
        question_type: Question type from classification
        has_diagram: Whether the source has a diagram
        key_concepts: Key concepts from classification or ideas

    Returns:
        CrossTopicAnalysis with the chosen integration topic and reasoning
    """
    agent = _create_analyzer_agent()

    message = ANALYZER_USER_TEMPLATE.format(
        source_latex=source_latex,
        subject=subject,
        topic=topic or "unknown",
        question_type=question_type,
        has_diagram=has_diagram,
        key_concepts=", ".join(key_concepts) if key_concepts else "not available",
    )

    return run_agent_sync(agent, message)


def generate_cross_topic_variant(
    source_latex: str,
    analysis: CrossTopicAnalysis,
    use_context: bool = True,
) -> str:
    """Stage 2: Generate the cross-topic variant using the analysis.

    Args:
        source_latex: The source problem in LaTeX format
        analysis: CrossTopicAnalysis from Stage 1
        use_context: Whether to include reference context

    Returns:
        The generated cross-topic variant in LaTeX format
    """
    agent = _create_generator_agent(use_context)

    message = GENERATOR_USER_TEMPLATE.format(
        source_latex=source_latex,
        source_topic=analysis.source_topic,
        integration_topic=analysis.integration_topic,
        integration_reasoning=analysis.integration_reasoning,
        integration_approach=analysis.integration_approach,
        difficulty_delta=analysis.difficulty_delta,
    )

    raw = run_agent_sync(agent, message)
    return clean_latex_output(raw)
