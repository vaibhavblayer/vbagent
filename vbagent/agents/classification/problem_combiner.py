"""Agent 6: Multi-Problem Combiner.

Combines multiple problems into a single comprehensive problem.
"""

from typing import List, Dict

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.models.classification import CombinedProblem
from vbagent.prompts.classification.problem_combiner import get_problem_combiner_prompt


def create_problem_combiner_agent():
    """Create problem combiner agent."""
    prompt = get_problem_combiner_prompt()

    return create_agent(
        name="ProblemCombiner",
        instructions=prompt,
        output_type=CombinedProblem,
        agent_type="variant",
    )


def combine_problems(
    problems: List[Dict[str, str]],
    strategy: str = "sequential",
    target_difficulty: str = "hard",
    cross_subject: bool = False,
) -> CombinedProblem:
    """Combine multiple problems (Agent 6).

    Args:
        problems: List of problem dicts with keys: id, latex, solution, subject, topic
        strategy: Combination strategy (sequential, parallel, nested)
        target_difficulty: Target difficulty for combined problem
        cross_subject: Whether to combine across subjects

    Returns:
        CombinedProblem with integrated content
    """
    agent = create_problem_combiner_agent()

    problems_str = ""
    for i, prob in enumerate(problems, 1):
        problems_str += f"""
**Problem {i}** (ID: {prob.get('id', i)})
Subject: {prob.get('subject', 'physics')}
Topic: {prob.get('topic', 'unknown')}

LaTeX:
```latex
{prob['latex']}
```

Solution:
```latex
{prob.get('solution', 'Not provided')}
```
"""

    subjects = list(set(p.get('subject', 'physics') for p in problems))

    context = f"""Combine these problems into a single comprehensive problem.

**Combination Strategy:** {strategy}
**Target Difficulty:** {target_difficulty}
**Cross-Subject:** {cross_subject}
**Subjects Involved:** {', '.join(subjects)}

{problems_str}

Create a natural, well-integrated combined problem."""

    return run_agent_sync(agent, context)
