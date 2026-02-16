"""Agent 4: LaTeX Classifier.

Classifies questions from LaTeX text for batch processing.
"""

from typing import Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import PrimaryClassification
from vbagent.prompts.subjects import get_subject_config
from vbagent.prompts.classification.taxonomy import get_chapters, get_all_topics


def get_latex_classifier_prompt(subject: str = "physics") -> str:
    """Get LaTeX classifier prompt."""
    config = get_subject_config(subject)
    chapters = get_chapters(subject)
    all_topics = get_all_topics(subject)
    
    chapters_str = ", ".join(f'"{c}"' for c in chapters[:10])
    if len(chapters) > 10:
        chapters_str += f", ... ({len(chapters)} total)"
    
    topics_str = ", ".join(f'"{t}"' for t in all_topics[:15])
    if len(all_topics) > 15:
        topics_str += f", ... ({len(all_topics)} total)"
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided LaTeX content and extract structured metadata.

You MUST respond with ONLY a valid JSON object:

{{
    "subject": "{subject}",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "chapter": "<from list below>",
    "topic": "<from list below>",
    "subtopic": "<specific subtopic>",
    "has_diagram": true | false,
    "num_options": <number if MCQ, else null>,
    "key_concepts": ["<concept1>", "<concept2>"],
    "requires_calculus": true | false,
    "estimated_marks": <typical marks: 1-10>,
    "time_estimate_minutes": <typical solve time: 1-30>,
    "confidence": <0.0 to 1.0>,
    "classified_from": "latex"
}}

**Available Chapters:** {chapters_str}
**Available Topics:** {topics_str}

Question types:
- mcq_sc: Single correct MCQ (look for \\ans marker)
- mcq_mc: Multiple correct MCQ
- subjective: Open-ended/numerical (look for \\ansint{{}})
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing context
- match: Match the following

Diagram detection:
- has_diagram: true if contains \\includegraphics, \\begin{{tikzpicture}}, \\begin{{circuitikz}}, etc.

Rules:
1. Choose chapter and topic from lists above
2. Analyze LaTeX structure and content
3. Detect question type from LaTeX markers
4. Do NOT assess difficulty - that happens later

Respond with ONLY the JSON object."""


def create_latex_classifier_agent(subject: Optional[str] = None):
    """Create LaTeX classifier agent."""
    if subject is None:
        subject = get_config().subject
    
    prompt = get_latex_classifier_prompt(subject)
    
    return create_agent(
        name=f"LaTeXClassifier-{subject}",
        instructions=prompt,
        output_type=PrimaryClassification,
        agent_type="classifier",
    )


def classify_from_latex(latex_content: str, subject: Optional[str] = None) -> PrimaryClassification:
    """Classify question from LaTeX (Agent 4).
    
    Args:
        latex_content: LaTeX content to classify
        subject: Subject override
        
    Returns:
        PrimaryClassification without difficulty
    """
    if subject is None:
        subject = get_config().subject
    
    agent = create_latex_classifier_agent(subject)
    
    context = f"""Classify this {subject} question from LaTeX.

**LaTeX Content:**
```latex
{latex_content}
```

Analyze the content and provide classification."""
    
    result = run_agent_sync(agent, context)
    return result
