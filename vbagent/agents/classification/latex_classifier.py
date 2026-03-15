"""Agent 4: LaTeX Classifier.

Classifies questions from LaTeX text for batch processing.
"""

from typing import Optional

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import PrimaryClassification
from vbagent.prompts.subjects import get_subject_config
from vbagent.prompts.classification.question_types import get_question_type_guidance
from vbagent.agents.classification.subject_detector import detect_subject_from_latex


def get_latex_classifier_prompt(subject: str = "physics") -> str:
    """Get simplified LaTeX classifier prompt (3 fields only)."""
    config = get_subject_config(subject)
    question_type_guidance = get_question_type_guidance()
    
    return f"""You are an expert {config.display_name.lower()} question classifier. Analyze the provided LaTeX content and extract structured metadata.

You MUST respond with ONLY a valid JSON object:

{{
    "subject": "physics" | "chemistry" | "mathematics" | "biology",
    "question_type": "mcq_sc" | "mcq_mc" | "subjective" | "assertion_reason" | "passage" | "match",
    "has_diagram": true | false,
    "confidence": <0.0 to 1.0>,
    "classified_from": "latex"
}}

Question types:
- mcq_sc: Single correct MCQ (look for \\ans marker)
- mcq_mc: Multiple correct MCQ
- subjective: Open-ended/numerical (look for \\ansint{{}})
- assertion_reason: Assertion-reason format
- passage: Multiple questions sharing context
- match: Match the following

Detailed detection cues:
{question_type_guidance}

Diagram detection:
- has_diagram: true if contains \\includegraphics, \\begin{{tikzpicture}}, \\begin{{circuitikz}}, etc.

Rules:
1. classified_from: always "latex"
2. has_diagram: true if ANY visual element is present in LaTeX

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
        try:
            subject = detect_subject_from_latex(latex_content)
        except (ValueError, TimeoutError):
            subject = get_config().subject
    
    agent = create_latex_classifier_agent(subject)
    
    context = f"""Classify this {subject} question from LaTeX.

**LaTeX Content:**
```latex
{latex_content}
```

Analyze the content and provide classification."""
    
    result = run_agent_sync(agent, context, timeout=30)
    return result
