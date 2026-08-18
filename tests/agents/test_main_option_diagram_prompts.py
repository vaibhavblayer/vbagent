"""Prompt contracts for separating main and option diagrams."""

from vbagent.prompts.classification.question_classifier import (
    get_question_classifier_prompt,
)
from vbagent.prompts.content_generation.scanner._shared import DIAGRAM_PLACEHOLDER
from vbagent.prompts.content_generation.scanner._shared import options_with_diagrams
from vbagent.agents.diagram.mcq_option_coordinator import _build_option_description


def test_classifier_prompt_defines_all_four_diagram_states():
    prompt = get_question_classifier_prompt("physics")

    assert "Option diagrams only: has_diagram=false, has_option_diagrams=true" in prompt
    assert "Both main and option diagrams: has_diagram=true, has_option_diagrams=true" in prompt
    assert "Option diagrams do not make this true" in prompt


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
