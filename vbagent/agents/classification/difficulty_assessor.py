"""Agent 3: Difficulty Assessor.

Assesses difficulty AFTER LaTeX extraction and TikZ generation.
Provides detailed reasoning and metadata.
"""

from typing import Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification_v2 import (
    DifficultyAssessment,
    PrimaryClassification,
    DiagramAnalysis,
)


def get_difficulty_assessor_prompt(subject: str = "physics") -> str:
    """Get difficulty assessor prompt."""
    return f"""You are an expert {subject} difficulty assessor. Analyze the problem and assess its difficulty with detailed reasoning.

You MUST respond with ONLY a valid JSON object:

{{
    "difficulty": "easy" | "medium" | "hard",
    "difficulty_score": <1.0-10.0>,
    "difficulty_factors": {{
        "concept_complexity": "low" | "moderate" | "high",
        "calculation_complexity": "low" | "moderate" | "high",
        "multi_step": true | false,
        "requires_visualization": true | false,
        "formula_complexity": "low" | "moderate" | "high",
        "diagram_complexity": "low" | "moderate" | "high" | null
    }},
    "difficulty_reasoning": "<detailed explanation>",
    "expected_solve_time_minutes": <realistic time>,
    "expected_error_rate": <0.0-1.0>,
    "prerequisite_concepts": ["<concept1>", "<concept2>"],
    "common_mistakes": ["<mistake1>", "<mistake2>"],
    "cognitive_level": "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create",
    "solution_approach": ["<step1>", "<step2>"],
    "required_formulas": ["<formula1>", "<formula2>"],
    "problem_structure": {{
        "has_given_data": true | false,
        "has_find_statement": true | false,
        "has_constraints": true | false,
        "is_multi_part": true | false
    }},
    "exam_relevance": {{
        "jee_main": <0.0-1.0>,
        "jee_advanced": <0.0-1.0>,
        "neet": <0.0-1.0>
    }},
    "learning_objectives": ["<objective1>", "<objective2>"],
    "tags_auto": ["<tag1>", "<tag2>"],
    "confidence": <0.0-1.0>
}}

Difficulty mapping:
- easy (1.0-3.5): Direct application, single concept, standard formula
- medium (3.5-7.0): Multiple steps, concept combination, moderate calculation
- hard (7.0-10.0): Complex reasoning, multiple concepts, non-standard approach

Cognitive levels (Bloom's Taxonomy):
- remember: Recall facts, formulas
- understand: Explain concepts
- apply: Use formulas, solve standard problems
- analyze: Break down complex problems
- evaluate: Judge solutions, compare approaches
- create: Design new solutions, combine concepts

Exam relevance (0.0-1.0):
- 0.0-0.3: Rarely appears
- 0.3-0.7: Occasionally appears
- 0.7-1.0: Frequently appears

Expected error rate:
- 0.0-0.2: Most students solve correctly
- 0.2-0.5: Moderate error rate
- 0.5-1.0: High error rate, tricky problem

Provide detailed reasoning explaining WHY this difficulty was assigned.

Respond with ONLY the JSON object."""


def create_difficulty_assessor_agent(subject: Optional[str] = None):
    """Create difficulty assessor agent."""
    if subject is None:
        subject = get_config().subject
    
    prompt = get_difficulty_assessor_prompt(subject)
    
    return create_agent(
        name=f"DifficultyAssessor-{subject}",
        instructions=prompt,
        output_type=DifficultyAssessment,
        agent_type="difficulty_assessor",  # Use dedicated agent type
    )


def assess_difficulty(
    latex_content: str,
    primary: PrimaryClassification,
    diagram: Optional[DiagramAnalysis] = None,
    tikz_code: Optional[str] = None,
    subject: Optional[str] = None,
    show_spinner: bool = True
) -> DifficultyAssessment:
    """Assess difficulty after LaTeX extraction (Agent 3).
    
    Args:
        latex_content: Extracted LaTeX content
        primary: Primary classification
        diagram: Diagram analysis (if available)
        tikz_code: Generated TikZ code (if available)
        subject: Subject override
        show_spinner: Whether to show animated spinner
        
    Returns:
        DifficultyAssessment with detailed metadata
    """
    if subject is None:
        subject = primary.subject
    
    agent = create_difficulty_assessor_agent(subject)
    
    # Build context
    context = f"""Assess the difficulty of this {subject} problem.

**Question Type:** {primary.question_type}
**Topic:** {primary.topic}
**Subtopic:** {primary.subtopic}
**Key Concepts:** {', '.join(primary.key_concepts)}
**Requires Calculus:** {primary.requires_calculus}
"""
    
    if diagram:
        context += f"""
**Has Diagram:** Yes
**Diagram Type:** {diagram.diagram_type}
**Diagram Complexity:** {diagram.diagram_complexity}
**Diagram Elements:** {', '.join(diagram.diagram_elements)}
"""
    
    context += f"""

**LaTeX Content:**
```latex
{latex_content}
```
"""
    
    if tikz_code:
        context += f"""

**TikZ Diagram:**
```latex
{tikz_code}
```
"""
    
    context += """

Analyze the problem thoroughly and provide detailed difficulty assessment with reasoning."""
    
    result = run_agent_sync(agent, context, show_spinner=show_spinner)
    return result
