"""Regression tests for composed physics topic solution prompts."""

from importlib import import_module

import pytest

from vbagent.prompts.content_generation.solution.physics.common import (
    build_topic_prompts,
)


TOPIC_MODULES = [
    "atomic_nuclear",
    "current_electricity",
    "electromagnetism",
    "electrostatics",
    "energy_work",
    "gravitation",
    "heat_transfer",
    "magnetism",
    "mechanics",
    "modern_physics",
    "ray_optics",
    "rotational",
    "shm",
    "thermodynamics",
    "wave_optics",
    "waves",
]


@pytest.mark.parametrize("module_name", TOPIC_MODULES)
def test_topic_prompt_selection_preserves_public_variants(module_name):
    """Every migrated topic exposes the same question-type selection contract."""
    module = import_module(
        "vbagent.prompts.content_generation.solution.physics.topics."
        + module_name
    )

    assert module.get_prompt("subjective") is module.SYSTEM_PROMPT_SUBJECTIVE
    assert module.get_prompt("integer") is module.SYSTEM_PROMPT_SUBJECTIVE
    assert module.get_prompt("unknown") is module.SYSTEM_PROMPT_SUBJECTIVE
    assert module.get_prompt("mcq_sc") is module.SYSTEM_PROMPT_MCQ_SC
    assert module.get_prompt("mcq_mc") is module.SYSTEM_PROMPT_MCQ_MC


def test_builder_keeps_topic_guidance_and_custom_diagram_requirement():
    """Composition retains topic content and supports intentional overrides."""
    prompts = build_topic_prompts(
        subjective_intro="Subjective intro",
        mcq_intro="Single-choice intro",
        mcq_mc_intro="Multiple-choice intro",
        topic_concepts="TOPIC CONCEPTS",
        common_patterns="COMMON PATTERNS",
        diagram_guidance="DIAGRAM GUIDANCE",
        typical_mistakes="TYPICAL MISTAKES",
        subjective_diagram_requirements="CUSTOM DIAGRAM REQUIREMENT",
    )

    for prompt in (prompts.subjective, prompts.mcq_sc, prompts.mcq_mc):
        assert "TOPIC CONCEPTS" in prompt
        assert "COMMON PATTERNS" in prompt
        assert "DIAGRAM GUIDANCE" in prompt
        assert "TYPICAL MISTAKES" in prompt

    assert "CUSTOM DIAGRAM REQUIREMENT" in prompts.subjective
    assert "CUSTOM DIAGRAM REQUIREMENT" not in prompts.mcq_sc
    assert "CUSTOM DIAGRAM REQUIREMENT" not in prompts.mcq_mc


def test_topic_prompts_encourage_useful_diagrams_and_bind_requirements_to_markers():
    """A requested specialist diagram must survive the solution handoff."""
    prompts = build_topic_prompts(
        subjective_intro="Subjective intro",
        mcq_intro="Single-choice intro",
        mcq_mc_intro="Multiple-choice intro",
        topic_concepts="TOPIC CONCEPTS",
        common_patterns="COMMON PATTERNS",
        diagram_guidance="DIAGRAM GUIDANCE",
        typical_mistakes="TYPICAL MISTAKES",
    )

    for prompt in (prompts.subjective, prompts.mcq_sc, prompts.mcq_mc):
        assert "materially simplify" in prompt
        assert "include one even if the original problem image has no diagram" in prompt
        assert "% DIAGRAM PLACEHOLDER: <diagram_id>" in prompt
