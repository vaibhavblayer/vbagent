"""Idea Combiner Agent.

Receives N candidate ideas with lens tags, selects the best subset,
and designs a combined problem framed through requested math lenses.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.ideas.models import Idea, difficulty_label
from vbagent.prompts.classification.idea_combiner import get_idea_combiner_prompt


class CombinedProblemOutput(BaseModel):
    """Structured output from the IdeaCombiner agent."""

    model_config = ConfigDict(extra="allow")

    selected_idea_ids: list[str] = Field(default_factory=list)
    combination_strategy: str = "parallel"
    combination_rationale: str = ""
    problem_latex: str = ""
    solution_latex: str = ""
    idea_latex: str = ""
    diagram_description: str = ""
    difficulty_breakdown: dict[str, int] = Field(default_factory=dict)
    lenses_applied: list[str] = Field(default_factory=list)
    generation_metadata: dict = Field(default_factory=dict)


def create_idea_combiner_agent(subject: Optional[str] = None):
    """Create the idea combiner agent."""
    if subject is None:
        subject = get_config().subject

    prompt = get_idea_combiner_prompt(subject)

    from agents import AgentOutputSchema

    return create_agent(
        name=f"IdeaCombiner-{subject}",
        instructions=prompt,
        output_type=AgentOutputSchema(CombinedProblemOutput, strict_json_schema=False),
        agent_type="idea",
    )


def combine_ideas(
    ideas: list[Idea],
    lenses: list[str] | None = None,
    difficulty: int = 5,
    question_type: str = "mcq_sc",
    concepts_context: str = "",
    subject: Optional[str] = None,
) -> CombinedProblemOutput:
    """Combine multiple ideas into a single problem.

    Args:
        ideas: Candidate ideas (agent will select best subset)
        lenses: Requested math lenses (None = agent picks)
        difficulty: 1-10 difficulty level
        question_type: mcq_sc, mcq_mc, integer, etc.
        concepts_context: Optional concepts.tex content for extra context
        subject: Subject override

    Returns:
        CombinedProblemOutput with complete problem
    """
    if subject is None:
        subject = get_config().subject

    agent = create_idea_combiner_agent(subject)

    # Format ideas for context
    ideas_block = ""
    for idea in ideas:
        formulas_str = ", ".join(idea.formulas) if idea.formulas else "none"
        natural = ", ".join(idea.natural_lenses) if idea.natural_lenses else "none"
        compat = ", ".join(idea.compatible_lenses) if idea.compatible_lenses else "none"
        ideas_block += f"""
**Idea {idea.id}** — {idea.text}
  Topic: {idea.topic} / {idea.subtopic}
  Formulas: {formulas_str}
  Natural lenses: {natural}
  Compatible lenses: {compat}
  LaTeX: {idea.idea_latex[:200] if idea.idea_latex else 'N/A'}
"""

    # Lens instruction
    if lenses:
        lens_instruction = f"Frame the problem through these mathematical lenses: {', '.join(lenses)}"
    else:
        lens_instruction = "Choose the most appropriate mathematical lens(es) based on the ideas and difficulty level."

    # Difficulty description
    diff_desc = difficulty_label(difficulty)

    context = f"""Combine ideas into a single original {subject} problem.

**Candidate Ideas ({len(ideas)} total — select the best 2–4):**
{ideas_block}

**Target Specifications:**
- Difficulty: {difficulty}/10 — {diff_desc}
- Question Type: {question_type}
- {lens_instruction}

"""

    if concepts_context:
        # Truncate if too long
        ctx = concepts_context[:2000] if len(concepts_context) > 2000 else concepts_context
        context += f"""**Additional Concepts Context:**
{ctx}

"""

    context += "Design a natural, well-integrated combined problem. Respond with ONLY the JSON object."

    return run_agent_sync(agent, context)
