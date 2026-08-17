"""Regression tests for canonical classifier names and compatibility aliases."""

from vbagent.agents.classification import question_classifier
from vbagent.agents.classification import unified_classifier
from vbagent.agents.classification.diagram_analyzer import (
    analyze_diagram_from_description,
)
from vbagent.agents.classification.diagram_classifier import (
    classify_diagram_description,
)
from vbagent.agents.classification.idea_generator import (
    generate_from_idea as legacy_generate_from_idea,
)
from vbagent.agents.content_generation.idea_generator import generate_from_idea
from vbagent.config import VBAgentConfig


def test_legacy_classifier_names_alias_canonical_objects():
    """Renamed public objects remain compatible during the transition."""
    assert (
        unified_classifier.UnifiedClassificationResult
        is question_classifier.QuestionClassification
    )
    assert (
        unified_classifier.create_unified_classifier_agent
        is question_classifier.create_question_classifier
    )
    assert (
        unified_classifier.classify_and_analyze
        is question_classifier.classify_question_image
    )
    assert (
        unified_classifier.to_primary
        is question_classifier.to_primary_classification
    )


def test_relocated_agent_names_alias_canonical_objects():
    """Old module paths still resolve to relocated implementations."""
    assert analyze_diagram_from_description is classify_diagram_description
    assert legacy_generate_from_idea is generate_from_idea


def test_legacy_config_agent_names_migrate_to_canonical_names():
    """Existing configuration files retain their model overrides."""
    config = VBAgentConfig.from_dict(
        {
            "agents": {
                "image_classifier": {
                    "model": "legacy-question-model",
                    "reasoning_effort": "low",
                },
                "diagram_analyzer": {
                    "model": "legacy-diagram-model",
                    "reasoning_effort": "medium",
                },
            }
        }
    )

    assert config.agents["classifier"].model == "legacy-question-model"
    assert config.agents["diagram_classifier"].model == "legacy-diagram-model"
    assert "image_classifier" not in config.agents
    assert "diagram_analyzer" not in config.agents


def test_canonical_config_names_win_over_legacy_duplicates():
    """A new config value takes precedence if both names are present."""
    config = VBAgentConfig.from_dict(
        {
            "agents": {
                "diagram_analyzer": {"model": "legacy-model"},
                "diagram_classifier": {"model": "canonical-model"},
            }
        }
    )

    assert config.agents["diagram_classifier"].model == "canonical-model"
