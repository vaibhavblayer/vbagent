"""Agent 5: Idea-to-Problem Generator.

Generates complete problems from physics/chemistry ideas and concepts.
"""

from typing import Optional, List

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification_v2 import GeneratedProblem


def get_idea_generator_prompt(subject: str = "physics") -> str:
    """Get idea generator prompt."""
    return f"""You are an expert {subject} problem generator. Generate a complete, well-structured problem from the given ideas and concepts.

You MUST respond with ONLY a valid JSON object:

{{
    "problem_latex": "<complete LaTeX problem with \\\\item>",
    "solution_latex": "<detailed LaTeX solution>",
    "alternate_solution_latex": "<alternative approach (optional)>",
    "idea_latex": "<core concepts and ideas>",
    "diagram_description": "<description if diagram needed>",
    "generation_metadata": {{
        "source_ideas": ["<idea1>", "<idea2>"],
        "formulas_used": ["<formula1>", "<formula2>"],
        "concepts_covered": ["<concept1>", "<concept2>"]
    }}
}}

Problem generation guidelines:
1. Create realistic, exam-style problems
2. Include clear given data and find statement
3. Use appropriate difficulty level
4. Include numerical values where appropriate
5. Ensure solution is complete and correct
6. Add alternate solution if multiple approaches exist
7. If diagram needed, provide detailed description

LaTeX formatting:
- Use \\item for problem statement
- Use \\SI{{}}{{}} for units (siunitx)
- Use proper math environments
- Include \\ans or \\ansint{{}} markers

Quality standards:
- Problem should be solvable
- Solution should be step-by-step
- Concepts should be clearly applied
- Numerical values should be realistic

Respond with ONLY the JSON object."""


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
    subject: Optional[str] = None
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
    
    result = run_agent_sync(agent, context)
    return result
