"""Prompt contracts for separating main and option diagrams."""

import pytest
from pydantic import ValidationError

from vbagent.agents.classification.question_classifier import (
    QuestionClassification,
    QuestionRoutingClassification,
    classification_fingerprint,
    to_diagram_analysis,
)
from vbagent.prompts.classification.question_classifier import (
    get_question_classifier_prompt,
)
from vbagent.prompts.classification.question_router import (
    get_question_router_prompt,
)
from vbagent.prompts.content_generation.scanner._shared import DIAGRAM_PLACEHOLDER
from vbagent.prompts.content_generation.scanner._shared import options_with_diagrams
from vbagent.agents.diagram.mcq_option_coordinator import _build_option_description


def test_classifier_prompt_defines_all_four_diagram_states():
    prompt = get_question_classifier_prompt("physics")

    assert "Option diagrams only: has_diagram=false, has_option_diagrams=true" in prompt
    assert "Both main and option diagrams: has_diagram=true, has_option_diagrams=true" in prompt
    assert "Option diagrams do not make this true" in prompt


def test_generic_router_outputs_only_subject_and_question_type():
    prompt = get_question_router_prompt()

    assert '"subject"' in prompt
    assert '"question_type"' in prompt
    assert '"has_diagram"' not in prompt
    assert '"chapter"' not in prompt
    assert '"diagram_type"' not in prompt
    assert "stem are objects the student must inspect" in prompt
    assert "classify it as `subjective`" in prompt
    assert "separate selectable answer" in prompt

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        QuestionRoutingClassification(
            subject="mathematics",
            question_type="subjective",
            has_diagram=True,
        )


def test_subject_analyzer_does_not_reclassify_routing_fields():
    prompt = get_question_classifier_prompt("mathematics")

    assert '"subject":' not in prompt
    assert '"question_type":' not in prompt
    assert "subject-neutral routing stage has already fixed" in prompt


def test_classifier_prompt_keeps_stem_panel_collections_out_of_option_fields():
    prompt = get_question_classifier_prompt("mathematics")

    assert "roman-labeled collection such as (i)--(x)" in prompt
    assert "has_diagram=true`, `has_option_diagrams=false" in prompt
    assert "EVERY main-diagram field must be populated" in prompt
    assert 'diagram_type: "function_graph"' in prompt


def test_main_diagram_classification_requires_complete_specific_metadata():
    with pytest.raises(ValidationError, match="complete main-diagram metadata"):
        QuestionClassification(
            subject="mathematics",
            question_type="subjective",
            has_diagram=True,
        )


def test_subjective_classification_rejects_option_diagrams():
    with pytest.raises(
        ValidationError,
        match="subjective questions cannot contain MCQ option diagrams",
    ):
        QuestionClassification(
            subject="mathematics",
            question_type="subjective",
            has_diagram=False,
            has_option_diagrams=True,
            num_option_diagrams=10,
            option_diagram_type="function_graph",
        )


def test_complete_panel_collection_routes_without_generic_fallback():
    classification = QuestionClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=True,
        diagram_type="function_graph",
        diagram_category="graphs",
        diagram_complexity="complex",
        diagram_elements=["10 roman-labeled Cartesian graph panels"],
        diagram_features={
            "has_labels": True,
            "has_measurements": False,
            "has_vectors": False,
            "has_grid": False,
            "coordinate_system": "cartesian",
            "num_objects": 10,
        },
        suggested_tikz_agent="function_graph",
    )

    analysis = to_diagram_analysis(classification)

    assert analysis is not None
    assert analysis.diagram_type == "function_graph"
    assert analysis.suggested_tikz_agent == "function_graph"
    assert analysis.diagram_features.num_objects == 10


def test_mathematics_graph_alias_routes_to_function_graph():
    classification = QuestionClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=True,
        diagram_type="graph",
        diagram_category="graphs",
        diagram_complexity="complex",
        diagram_elements=["10 roman-labeled Cartesian graph panels"],
        suggested_tikz_agent="graph",
    )

    assert classification.diagram_type == "function_graph"
    assert classification.suggested_tikz_agent == "function_graph"


def test_physics_graph_type_is_not_rewritten():
    classification = QuestionClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=True,
        diagram_type="graph",
        diagram_category="graphs",
        diagram_complexity="moderate",
        diagram_elements=["position-time graph"],
        suggested_tikz_agent="graph",
    )

    assert classification.diagram_type == "graph"
    assert classification.suggested_tikz_agent == "graph"


def test_classification_fingerprint_is_deterministic_and_content_sensitive():
    base = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
    )
    same = base.model_copy(deep=True)
    changed = base.model_copy(update={"question_type": "subjective"})

    assert classification_fingerprint(base) == classification_fingerprint(same)
    assert classification_fingerprint(base) != classification_fingerprint(changed)


def test_main_diagram_agent_must_match_diagram_type():
    with pytest.raises(ValidationError, match="must match diagram_type"):
        QuestionClassification(
            subject="mathematics",
            question_type="subjective",
            has_diagram=True,
            diagram_type="function_graph",
            diagram_category="graphs",
            diagram_complexity="complex",
            diagram_elements=["graph panels"],
            suggested_tikz_agent="generic",
        )


def test_physics_main_diagram_keeps_specific_type_during_conversion():
    classification = QuestionClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=True,
        diagram_type="mechanics",
        diagram_category="mechanics",
        diagram_complexity="moderate",
        diagram_elements=["block and pulley"],
        suggested_tikz_agent="mechanics",
    )

    analysis = to_diagram_analysis(classification)

    assert analysis is not None
    assert analysis.diagram_type == "mechanics"
    assert analysis.suggested_tikz_agent == "mechanics"


def test_scanner_prompt_does_not_use_main_placeholder_for_option_only_question():
    assert "For an options-only question, do NOT emit" in DIAGRAM_PLACEHOLDER
    assert "If the image contains BOTH a main diagram and option diagrams" in DIAGRAM_PLACEHOLDER


def test_option_agent_defines_macros_and_scanner_uses_them_in_tasks():
    option_prompt = _build_option_description(None, 4)
    scanner_prompt = options_with_diagrams()

    assert r"\def\OptionA" in option_prompt
    assert r"\begin{tikzpicture}" in option_prompt
    assert "Output ALL 4 definitions consecutively with NO other text" in option_prompt
    assert r"\task \OptionA" in scanner_prompt
    assert r"\task \OptionD" in scanner_prompt
