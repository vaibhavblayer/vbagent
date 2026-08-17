"""Regression tests for lowercase, plain MCQ answer labels in prompts."""

import pytest

from vbagent.prompts.content_generation.converter import get_format_instructions
from vbagent.prompts.content_generation.mcq_format import MCQ_ANSWER_FORMAT_RULES
from vbagent.prompts.content_generation.scanner import (
    biology as biology_scanner,
    chemistry as chemistry_scanner,
    mathematics as mathematics_scanner,
    physics as physics_scanner,
)
from vbagent.prompts.content_generation.solution import (
    biology as biology_solution,
    chemistry as chemistry_solution,
    mathematics as mathematics_solution,
    physics as physics_solution,
)
from vbagent.prompts.quality.format_checker import get_system_prompt
from vbagent.prompts.quality.solution_checker import SYSTEM_PROMPT as SOLUTION_CHECKER_PROMPT


EXPECTED_RULES = MCQ_ANSWER_FORMAT_RULES.strip()


def test_shared_rule_requires_lowercase_plain_labels():
    """The shared rule explicitly covers case, formatting, and intertext output."""
    assert "`(a)`, `(b)`, `(c)`, and `(d)`" in EXPECTED_RULES
    assert "Never use uppercase labels" in EXPECTED_RULES
    assert "do not bold, italicize, underline" in EXPECTED_RULES
    assert r"\intertext{Therefore, the correct option is (a).}" in EXPECTED_RULES


@pytest.mark.parametrize(
    "prompt_getter",
    [
        physics_solution.get_prompt,
        chemistry_solution.get_prompt,
        mathematics_solution.get_prompt,
        biology_solution.get_prompt,
        physics_scanner.get_prompt,
        chemistry_scanner.get_prompt,
        mathematics_scanner.get_prompt,
        biology_scanner.get_prompt,
    ],
)
@pytest.mark.parametrize("question_type", ["mcq_sc", "mcq_mc", "match"])
def test_composed_mcq_prompts_include_shared_label_rule(prompt_getter, question_type):
    """Every subject/type route carries the same mandatory label instruction."""
    prompt = prompt_getter(question_type)
    assert EXPECTED_RULES in prompt


def test_converter_and_quality_prompts_include_shared_label_rule():
    """Conversion and post-generation checks enforce the same output contract."""
    assert EXPECTED_RULES in get_format_instructions("mcq_sc")
    assert EXPECTED_RULES in get_format_instructions("mcq_mc")
    assert EXPECTED_RULES in get_system_prompt("physics")
    assert EXPECTED_RULES in get_system_prompt("chemistry")
    assert EXPECTED_RULES in get_system_prompt("biology")
    assert EXPECTED_RULES in SOLUTION_CHECKER_PROMPT
