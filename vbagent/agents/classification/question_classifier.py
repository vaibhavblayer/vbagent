"""Canonical question-image classifier.

Classifies the question, curriculum topic, and diagram requirements in one
vision request.
"""

from dataclasses import replace
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vbagent.agents.base import (
    create_agent,
    create_cacheable_image_message,
    create_image_message,
    run_agent_sync_grouped,
)
from vbagent.config import get_config, get_model, get_model_settings
from vbagent.models.classification import (
    PrimaryClassification,
    DiagramAnalysis,
    DiagramFeatures,
    QuestionType,
    Subject,
    DiagramCategory,
    DiagramComplexity,
)
from vbagent.prompts.classification.question_classifier import (
    get_question_classifier_prompt,
)


class QuestionClassification(BaseModel):
    """Complete classification of one question image."""
    model_config = ConfigDict(extra="forbid")

    # Classification
    subject: Subject
    question_type: QuestionType
    has_diagram: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    # Topic classification
    chapter: Optional[str] = None
    topic: Optional[str] = None

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

    _DIAGRAM_TYPES_BY_SUBJECT: ClassVar[dict[str, set[str]]] = {
        "physics": {
            "circuit", "gates", "graph", "optics", "mechanics", "wave", "fbd",
        },
        "chemistry": {
            "organic_structure", "reaction_mechanism", "chemical_equation",
            "energy_diagram", "orbital", "lewis_structure",
        },
        "mathematics": {
            "number_line", "function_graph", "coordinate_geometry",
            "geometric_figure", "venn_diagram",
        },
        "biology": {"generic"},
    }

    _DIAGRAM_TYPE_ALIASES_BY_SUBJECT: ClassVar[dict[str, dict[str, str]]] = {
        "mathematics": {
            "graph": "function_graph",
        },
    }

    @model_validator(mode="before")
    @classmethod
    def canonicalize_subject_diagram_aliases(cls, data):
        """Normalize unambiguous model aliases before strict validation."""
        if not isinstance(data, dict):
            return data

        aliases = cls._DIAGRAM_TYPE_ALIASES_BY_SUBJECT.get(data.get("subject"), {})
        if not aliases:
            return data

        normalized = dict(data)
        for field_name in ("diagram_type", "suggested_tikz_agent"):
            value = normalized.get(field_name)
            normalized[field_name] = aliases.get(value, value)
        return normalized

    @model_validator(mode="after")
    def validate_main_diagram_contract(self) -> "QuestionClassification":
        """Keep a positive main-diagram flag from degrading to generic data."""
        if self.question_type == "subjective" and self.has_option_diagrams:
            raise ValueError(
                "subjective questions cannot contain MCQ option diagrams"
            )
        if not self.has_diagram:
            return self

        missing = []
        for field_name in (
            "diagram_type",
            "diagram_category",
            "diagram_complexity",
            "suggested_tikz_agent",
        ):
            if getattr(self, field_name) is None:
                missing.append(field_name)
        if not self.diagram_elements:
            missing.append("diagram_elements")
        if missing:
            raise ValueError(
                "has_diagram=true requires complete main-diagram metadata; "
                f"missing: {', '.join(missing)}"
            )

        allowed_types = self._DIAGRAM_TYPES_BY_SUBJECT[self.subject]
        if self.diagram_type not in allowed_types:
            raise ValueError(
                f"diagram_type={self.diagram_type!r} is invalid for {self.subject}"
            )
        if self.suggested_tikz_agent != self.diagram_type:
            raise ValueError(
                "suggested_tikz_agent must match diagram_type for a main diagram"
            )
        if self.subject != "biology" and self.diagram_category == "none":
            raise ValueError(
                "diagram_category cannot be 'none' when has_diagram=true"
            )
        return self


def _initial_subject(subject: Optional[str]) -> str:
    """Use an explicit subject or the configured default for the first pass."""
    return subject or get_config().subject


def create_question_classifier(subject: str = "physics"):
    """Create the canonical question classifier agent."""
    prompt = get_question_classifier_prompt(subject)
    model = get_model("classifier")
    model_settings = get_model_settings("classifier")
    if _uses_explicit_prompt_cache(model):
        model_settings = replace(
            model_settings,
            prompt_cache_options={"mode": "explicit", "ttl": "30m"},
        )
    return create_agent(
        name=f"QuestionClassifier-{subject}",
        instructions=prompt,
        model=model,
        model_settings=model_settings,
        output_type=QuestionClassification,
        agent_type="classifier",
    )


def _classification_cache_group(subject: str) -> str:
    """Return the stable cache group for one version of a subject prompt."""
    return f"vbagent:question-classifier:v4:{subject}"


def _uses_explicit_prompt_cache(model: str) -> bool:
    """Return whether this is an official GPT-5.6 Responses request."""
    normalized = model.removeprefix("openai/").lower()
    return get_config().base_url is None and normalized.startswith("gpt-5.6")


def _classification_message(image_path: str, subject: str, model: str):
    text = f"Classify and analyze this {subject} question."
    if _uses_explicit_prompt_cache(model):
        return create_cacheable_image_message(
            image_path,
            text,
            "Apply the stable classifier instructions above to the following question image.",
        )
    return create_image_message(image_path, text)


def classify_question_image(
    image_path: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> QuestionClassification:
    """Classify a question image and its diagram in one API call.

    If the classifier returns a different subject than what was initially
    detected/provided, re-runs with the correct subject-specific prompt
    so diagram types and agent routing are accurate.

    Args:
        image_path: Path to question image
        subject: Subject override (auto-detected if None)
        show_spinner: Whether to show spinner

    Returns:
        Complete question classification and diagram data
    """
    initial_subject = _initial_subject(subject)
    agent = create_question_classifier(initial_subject)
    message = _classification_message(image_path, initial_subject, str(agent.model))
    result = run_agent_sync_grouped(
        agent,
        message,
        _classification_cache_group(initial_subject),
        show_spinner=show_spinner,
        timeout=90,
    )

    # If classifier corrected the subject, re-run with the right prompt
    # so diagram_type and suggested_tikz_agent use the correct valid types.
    # Skip re-run if subject was explicitly provided by the caller.
    if not subject and result.subject != initial_subject:
        corrected = result.subject
        agent = create_question_classifier(corrected)
        message = _classification_message(image_path, corrected, str(agent.model))
        result = run_agent_sync_grouped(
            agent,
            message,
            _classification_cache_group(corrected),
            show_spinner=show_spinner,
            timeout=90,
        )

    return result


def to_primary_classification(
    result: QuestionClassification,
) -> PrimaryClassification:
    """Extract the compact primary-classification view."""
    return PrimaryClassification(
        subject=result.subject,
        question_type=result.question_type,
        has_diagram=result.has_diagram,
        chapter=result.chapter,
        topic=result.topic,
        confidence=result.confidence,
        classified_from="image",
    )


def classify_primary_image(
    image_path: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
) -> PrimaryClassification:
    """Classify an image and return only the compact primary view."""
    result = classify_question_image(
        image_path,
        subject=subject,
        show_spinner=show_spinner,
    )
    return to_primary_classification(result)


def to_diagram_analysis(
    result: QuestionClassification,
) -> Optional[DiagramAnalysis]:
    """Extract the standalone diagram-analysis view, if one is needed."""
    if not result.has_diagram and not result.has_option_diagrams:
        return None

    main = result.has_diagram
    return DiagramAnalysis(
        diagram_type=result.diagram_type if main else "generic",
        diagram_category=result.diagram_category if main else "none",
        diagram_complexity=result.diagram_complexity if main else "simple",
        diagram_elements=result.diagram_elements if main else [],
        diagram_features=result.diagram_features if main else DiagramFeatures(),
        suggested_tikz_agent=result.suggested_tikz_agent if main else "generic",
        confidence=result.confidence,
        has_option_diagrams=result.has_option_diagrams,
        num_option_diagrams=result.num_option_diagrams,
        option_diagram_type=result.option_diagram_type,
        option_diagram_descriptions=result.option_diagram_descriptions,
    )


__all__ = [
    "QuestionClassification",
    "create_question_classifier",
    "classify_question_image",
    "classify_primary_image",
    "to_primary_classification",
    "to_diagram_analysis",
]
