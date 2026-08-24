"""Two-stage question routing and subject-specific image analysis."""

import hashlib
import json
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
from vbagent.prompts.classification.question_router import (
    get_question_router_prompt,
)


class QuestionRoutingClassification(BaseModel):
    """Minimal, subject-neutral first-pass routing result."""

    model_config = ConfigDict(extra="forbid")

    subject: Subject
    question_type: QuestionType


class SubjectSpecificQuestionAnalysis(BaseModel):
    """Detailed second-pass analysis after subject and type are fixed."""

    model_config = ConfigDict(extra="forbid")

    has_diagram: bool
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    chapter: Optional[str] = None
    topic: Optional[str] = None
    diagram_type: Optional[str] = None
    diagram_category: Optional[DiagramCategory] = None
    diagram_complexity: Optional[DiagramComplexity] = None
    diagram_elements: list[str] = Field(default_factory=list)
    diagram_features: DiagramFeatures = Field(default_factory=DiagramFeatures)
    suggested_tikz_agent: Optional[str] = None
    has_option_diagrams: bool = False
    num_option_diagrams: int = 0
    option_diagram_type: str = ""
    option_diagram_descriptions: list[str] = Field(default_factory=list)


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


def create_question_router():
    """Create the subject-neutral, minimal first-pass router."""
    model = get_model("classifier")
    model_settings = get_model_settings("classifier")
    if _uses_explicit_prompt_cache(model):
        model_settings = replace(
            model_settings,
            prompt_cache_options={"mode": "explicit", "ttl": "30m"},
        )
    return create_agent(
        name="QuestionRouter",
        instructions=get_question_router_prompt(),
        model=model,
        model_settings=model_settings,
        output_type=QuestionRoutingClassification,
        agent_type="classifier",
    )


def create_question_classifier(subject: str = "physics"):
    """Create the detailed subject-specific second-pass analyzer."""
    prompt = get_question_classifier_prompt(subject)
    model = get_model("classifier")
    model_settings = get_model_settings("classifier")
    if _uses_explicit_prompt_cache(model):
        model_settings = replace(
            model_settings,
            prompt_cache_options={"mode": "explicit", "ttl": "30m"},
        )
    return create_agent(
        name=f"QuestionAnalyzer-{subject}",
        instructions=prompt,
        model=model,
        model_settings=model_settings,
        output_type=SubjectSpecificQuestionAnalysis,
        agent_type="classifier",
    )


def _routing_cache_group() -> str:
    """Return the stable cache group for the generic routing prompt."""
    return "vbagent:question-router:v1"


def _classification_cache_group(subject: str) -> str:
    """Return the stable cache group for one version of a subject prompt."""
    return f"vbagent:question-analyzer:v1:{subject}"


def _uses_explicit_prompt_cache(model: str) -> bool:
    """Return whether this is an official GPT-5.6 Responses request."""
    normalized = model.removeprefix("openai/").lower()
    return get_config().base_url is None and normalized.startswith("gpt-5.6")


def _routing_message(image_path: str, model: str):
    """Build the subject-neutral first-pass image message."""
    text = "Determine only the subject and question type."
    if _uses_explicit_prompt_cache(model):
        return create_cacheable_image_message(
            image_path,
            text,
            "Apply the stable subject-neutral routing instructions above.",
        )
    return create_image_message(image_path, text)


def _classification_message(
    image_path: str,
    subject: str,
    question_type: str,
    model: str,
):
    """Build the detailed subject-specific second-pass image message."""
    text = (
        f"Analyze this routed {subject} {question_type} question. "
        "Return only the detailed analysis fields; subject and question type "
        "were fixed by the routing stage."
    )
    if _uses_explicit_prompt_cache(model):
        return create_cacheable_image_message(
            image_path,
            text,
            "Apply the stable subject-specific analysis instructions above.",
        )
    return create_image_message(image_path, text)


def classify_question_route(
    image_path: str,
    show_spinner: bool = True,
) -> QuestionRoutingClassification:
    """Route an image using only subject and question type."""
    agent = create_question_router()
    message = _routing_message(image_path, str(agent.model))
    return run_agent_sync_grouped(
        agent,
        message,
        _routing_cache_group(),
        show_spinner=show_spinner,
        timeout=90,
    )


def classify_question_image(
    image_path: str,
    subject: Optional[str] = None,
    show_spinner: bool = True,
    routing: Optional[QuestionRoutingClassification] = None,
) -> QuestionClassification:
    """Route an image, then perform its subject-specific detailed analysis.

    Args:
        image_path: Path to question image
        subject: Optional explicit subject override.
        show_spinner: Whether to show spinner
        routing: Optional cached first-pass result.

    Returns:
        Complete question classification and diagram data
    """
    route = routing or classify_question_route(
        image_path,
        show_spinner=show_spinner,
    )
    if subject is not None and route.subject != subject:
        route = route.model_copy(update={"subject": subject})

    agent = create_question_classifier(route.subject)
    message = _classification_message(
        image_path,
        route.subject,
        route.question_type,
        str(agent.model),
    )
    analysis = run_agent_sync_grouped(
        agent,
        message,
        _classification_cache_group(route.subject),
        show_spinner=show_spinner,
        timeout=90,
    )
    return QuestionClassification(
        subject=route.subject,
        question_type=route.question_type,
        **analysis.model_dump(),
    )


def classification_fingerprint(result: QuestionClassification) -> str:
    """Return a deterministic dependency key for downstream cache stages."""
    payload = json.dumps(
        result.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    "QuestionRoutingClassification",
    "SubjectSpecificQuestionAnalysis",
    "QuestionClassification",
    "create_question_router",
    "create_question_classifier",
    "classify_question_route",
    "classify_question_image",
    "classification_fingerprint",
    "classify_primary_image",
    "to_primary_classification",
    "to_diagram_analysis",
]
