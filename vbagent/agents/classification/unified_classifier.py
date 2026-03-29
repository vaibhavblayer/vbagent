"""Unified Classifier — single API call for classification + diagram analysis.

Merges Agent 1 (PrimaryClassification) and Agent 2 (DiagramAnalysis) into
one vision call, saving an API round-trip on every image.
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from vbagent.agents.base import create_agent, create_image_message, run_agent_sync
from vbagent.config import get_config
from vbagent.models.classification import (
    PrimaryClassification,
    DiagramAnalysis,
    DiagramFeatures,
    QuestionType,
    Subject,
    DiagramCategory,
    DiagramComplexity,
)
from vbagent.agents.classification.subject_detector import detect_subject_from_image
from vbagent.prompts.classification.unified_classifier import get_unified_classifier_prompt


class UnifiedClassificationResult(BaseModel):
    """Combined output from the unified classifier."""
    model_config = ConfigDict(extra="forbid")

    # Classification
    subject: Subject
    question_type: QuestionType
    has_diagram: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    # Diagram analysis — only populated when has_diagram=True
    diagram_type: Optional[str] = None
    diagram_category: Optional[DiagramCategory] = None
    diagram_complexity: Optional[DiagramComplexity] = None
    diagram_elements: list[str] = Field(default_factory=list)
    diagram_features: DiagramFeatures = Field(default_factory=DiagramFeatures)
    suggested_tikz_agent: Optional[str] = None

    # MCQ option diagrams
    has_option_diagrams: bool = False
    num_option_diagrams: int = 0
    option_diagram_type: str = ""
    option_diagram_descriptions: list[str] = Field(default_factory=list)


def _resolve_subject(image_path: str, subject: Optional[str]) -> str:
    """Resolve subject from config or auto-detection."""
    if subject:
        return subject
    try:
        return detect_subject_from_image(image_path)
    except (ValueError, TimeoutError):
        return get_config().subject


def create_unified_classifier_agent(subject: str = "physics"):
    """Create the unified classifier agent."""
    prompt = get_unified_classifier_prompt(subject)
    return create_agent(
        name=f"UnifiedClassifier-{subject}",
        instructions=prompt,
        output_type=UnifiedClassificationResult,
        agent_type="classifier",
    )


def classify_and_analyze(
    image_path: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> UnifiedClassificationResult:
    """Classify question and analyze diagram in a single API call.

    If the classifier returns a different subject than what was initially
    detected/provided, re-runs with the correct subject-specific prompt
    so diagram types and agent routing are accurate.

    Args:
        image_path: Path to question image
        subject: Subject override (auto-detected if None)
        show_spinner: Whether to show spinner

    Returns:
        UnifiedClassificationResult with both classification and diagram data
    """
    initial_subject = _resolve_subject(image_path, subject)
    agent = create_unified_classifier_agent(initial_subject)
    message = create_image_message(image_path, f"Classify and analyze this {initial_subject} question.")
    result = run_agent_sync(agent, message, show_spinner=show_spinner, timeout=90)

    # If classifier corrected the subject, re-run with the right prompt
    # so diagram_type and suggested_tikz_agent use the correct valid types.
    # Skip re-run if subject was explicitly provided by the caller.
    if not subject and result.subject != initial_subject:
        corrected = result.subject
        agent = create_unified_classifier_agent(corrected)
        message = create_image_message(image_path, f"Classify and analyze this {corrected} question.")
        result = run_agent_sync(agent, message, show_spinner=show_spinner, timeout=90)

    return result


def to_primary(result: UnifiedClassificationResult) -> PrimaryClassification:
    """Extract PrimaryClassification from unified result."""
    return PrimaryClassification(
        subject=result.subject,
        question_type=result.question_type,
        has_diagram=result.has_diagram,
        confidence=result.confidence,
        classified_from="image",
    )


def to_diagram_analysis(result: UnifiedClassificationResult) -> Optional[DiagramAnalysis]:
    """Extract DiagramAnalysis from unified result (None if no diagram)."""
    if not result.has_diagram and not result.has_option_diagrams:
        return None

    return DiagramAnalysis(
        diagram_type=result.diagram_type or "generic",
        diagram_category=result.diagram_category or "none",
        diagram_complexity=result.diagram_complexity or "simple",
        diagram_elements=result.diagram_elements,
        diagram_features=result.diagram_features,
        suggested_tikz_agent=result.suggested_tikz_agent or "generic",
        confidence=result.confidence,
        has_option_diagrams=result.has_option_diagrams,
        num_option_diagrams=result.num_option_diagrams,
        option_diagram_type=result.option_diagram_type,
        option_diagram_descriptions=result.option_diagram_descriptions,
    )
