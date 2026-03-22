"""Agent 5: Idea-to-Problem Generator.

Generates complete problems from physics/chemistry ideas and concepts.
"""

from typing import Optional, List

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import GeneratedProblem
from vbagent.prompts.classification.idea_generator import get_idea_generator_prompt


def create_idea_generator_agent(subject: Optional[str] = None):
    """Create idea generator agent."""
    if subject is None:
        subject = get_config().subject

    prompt = get_idea_generator_prompt(subject)

    # Import AgentOutputSchema to disable strict schema
    from agents import AgentOutputSchema

    return create_agent(
        name=f"IdeaGenerator-{subject}",
        instructions=prompt,
        output_type=AgentOutputSchema(GeneratedProblem, strict_json_schema=False),
        agent_type="variant",
    )


def generate_from_idea(
    ideas: List[str],
    concepts: List[str],
    topic: str,
    difficulty: str = "medium",
    question_type: str = "mcq_sc",
    subject: Optional[str] = None,
) -> GeneratedProblem:
    """Generate problem from ideas (Agent 5).

    Args:
        ideas: List of physics/chemistry ideas
        concepts: List of concepts to cover
        topic: Topic for the problem
        difficulty: Target difficulty
        question_type: Target question type
        subject: Subject override

    Returns:
        GeneratedProblem with complete content
    """
    if subject is None:
        subject = get_config().subject

    agent = create_idea_generator_agent(subject)

    ideas_str = "\n".join(f"- {idea}" for idea in ideas)
    concepts_str = "\n".join(f"- {concept}" for concept in concepts)

    context = f"""Generate a {subject} problem from these ideas and concepts.

**Target Specifications:**
- Topic: {topic}
- Difficulty: {difficulty}
- Question Type: {question_type}

**Ideas:**
{ideas_str}

**Concepts to Cover:**
{concepts_str}

Generate a complete, well-structured problem with solution."""

    return run_agent_sync(agent, context)
