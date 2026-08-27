"""Idea-to-problem generator.

Generates complete problems from physics/chemistry ideas and concepts.
"""

from typing import List, Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import GeneratedProblem
from vbagent.prompts.content_generation.idea_generator import (
    get_idea_generator_prompt,
)


def create_idea_generator_agent(subject: Optional[str] = None):
    """Create idea generator agent."""
    if subject is None:
        subject = get_config().subject

    prompt = get_idea_generator_prompt(subject)
    prompt += (
        "\n\nThe caller may explicitly request only selected components. "
        "Follow include_solution/include_idea instructions in the request: "
        "return empty strings for omitted fields, do not generate hidden solutions "
        "or move omitted content into metadata. The question is always required."
    )

    # Import AgentOutputSchema to disable strict schema
    from agents import AgentOutputSchema

    return create_agent(
        name=f"IdeaGenerator-{subject}",
        instructions=prompt,
        output_type=AgentOutputSchema(GeneratedProblem, strict_json_schema=False),
        agent_type="idea",
    )


def generate_from_idea(
    ideas: List[str],
    concepts: List[str],
    topic: str,
    difficulty: str = "medium",
    question_type: str = "mcq_sc",
    subject: Optional[str] = None,
    exam: Optional[str] = None,
    exam_pattern_description: Optional[str] = None,
    chapter: Optional[str] = None,
    chapter_description: Optional[str] = None,
    syllabus_topic: Optional[str] = None,
    syllabus_topic_description: Optional[str] = None,
    difficulty_score: Optional[int] = None,
    cognitive_level: Optional[str] = None,
    reasoning_lens: Optional[str] = None,
    representation: Optional[str] = None,
    construction_family: Optional[str] = None,
    diagram_policy: Optional[str] = None,
    forbidden_concepts: Optional[List[str]] = None,
    tone: Optional[str] = None,
    random_seed: Optional[int] = None,
    retry_feedback: Optional[str] = None,
    passage_question_count: Optional[int] = None,
    include_solution: bool = True,
    include_idea: bool = True,
) -> GeneratedProblem:
    """Generate a problem from ideas.

    Args:
        ideas: List of physics/chemistry ideas
        concepts: List of concepts to cover
        topic: Topic for the problem
        difficulty: Target difficulty
        question_type: Target question type
        subject: Subject override
        exam: Exact target exam, when authoring from a syllabus
        exam_pattern_description: Versioned response-format rule for the target exam
        chapter: Exact target syllabus chapter
        chapter_description: Official/custom chapter scope statement
        syllabus_topic: Exact target syllabus topic statement
        syllabus_topic_description: Additional official/custom topic scope
        difficulty_score: Anchored 1-10 target difficulty
        cognitive_level: Requested cognitive operation
        reasoning_lens: Requested solution/construction lens
        representation: Requested problem representation
        construction_family: Requested construction family
        diagram_policy: required, optional, or forbidden
        forbidden_concepts: Concepts that must not enter the problem
        tone: Optional authoring tone instruction
        random_seed: Stable creative seed from the immutable item specification
        retry_feedback: Evidence from a prior rejected attempt that must be corrected
        passage_question_count: Exact number of passage subquestions when applicable
        include_solution: Whether to generate the solution component now
        include_idea: Whether to generate an idea component

    Returns:
        GeneratedProblem with complete content
    """
    if subject is None:
        subject = get_config().subject

    agent = create_idea_generator_agent(subject)

    ideas_str = "\n".join(f"- {idea}" for idea in ideas)
    concepts_str = "\n".join(f"- {concept}" for concept in concepts)

    specifications = [
        f"- Exam: {exam or 'not specified'}",
        (
            f"- Exam response format: {exam_pattern_description}"
            if exam_pattern_description
            else ""
        ),
        f"- Subject: {subject}",
        f"- Chapter: {chapter or 'not specified'}",
        f"- Chapter scope: {chapter_description}" if chapter_description else "",
        f"- Exact syllabus topic: {syllabus_topic or topic}",
        (
            f"- Exact topic scope: {syllabus_topic_description}"
            if syllabus_topic_description
            else ""
        ),
        f"- Working topic: {topic}",
        f"- Difficulty band: {difficulty}",
        f"- Difficulty score: {difficulty_score}/10" if difficulty_score else "",
        f"- Question Type: {question_type}",
        f"- Cognitive level: {cognitive_level}" if cognitive_level else "",
        f"- Reasoning lens: {reasoning_lens}" if reasoning_lens else "",
        f"- Representation: {representation}" if representation else "",
        f"- Construction family: {construction_family}" if construction_family else "",
        f"- Diagram policy: {diagram_policy}" if diagram_policy else "",
        f"- Tone: {tone}" if tone else "",
        f"- Creative seed: {random_seed}" if random_seed is not None else "",
        (
            f"- Passage subquestion count: exactly {passage_question_count}"
            if question_type == "passage" and passage_question_count
            else ""
        ),
    ]
    if forbidden_concepts:
        specifications.append(f"- Forbidden concepts: {', '.join(forbidden_concepts)}")
    if retry_feedback:
        specifications.append(f"- Prior-attempt rejection to correct: {retry_feedback}")
    specifications_text = "\n".join(line for line in specifications if line)

    diagram_instruction = ""
    if diagram_policy == "required":
        diagram_instruction = (
            "\nA problem diagram is REQUIRED. Return a precise non-empty diagram_description "
            "and put \\input{diagram} at the intended location in problem_latex."
        )
    elif diagram_policy == "forbidden":
        diagram_instruction = (
            "\nA diagram is FORBIDDEN. Keep diagram_description empty and do not include "
            "TikZ, image, or diagram placeholders."
        )

    context = f"""Generate a {subject} problem from these ideas and concepts.

**Target Specifications:**
{specifications_text}

**Ideas:**
{ideas_str}

**Concepts to Cover:**
{concepts_str}

The exact exam, chapter, and syllabus topic are hard constraints. Do not drift
to a neighbouring chapter merely because it is related. Apply the requested
cognitive level, reasoning lens, representation, and construction family in
the actual problem rather than mentioning them as labels.{diagram_instruction}

Requested components override the default full-content recipe:
- Always return the complete question in problem_latex.
- solution_latex: {'provide a complete solution' if include_solution else 'return an empty string; the author explicitly deferred solutions'}.
- idea_latex: {'provide a concise conceptual idea, not a worked solution' if include_idea else 'return an empty string; no idea component was requested'}.
- alternate_solution_latex: {'optional when useful' if include_solution else 'return an empty string'}.
Do not include omitted components in the question or metadata instead."""

    return run_agent_sync(agent, context)
