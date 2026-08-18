"""Regression tests for compact match-the-column option formatting."""

from importlib import import_module

import pytest

from vbagent.prompts.content_generation.converter import get_format_instructions
from vbagent.prompts.content_generation.mcq_format import (
    MATCH_OPTION_FORMAT_RULES,
    MATCH_OPTION_FORMAT_RULES_UNMARKED,
)
from vbagent.prompts.content_generation.scanner import (
    biology as biology_scanner,
    chemistry as chemistry_scanner,
    mathematics as mathematics_scanner,
    physics as physics_scanner,
)


MARKED_OPTION = (
    r"\task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ "
    r"R\rightarrow I,\ S\rightarrow IV}$ \ans"
)
UNMARKED_OPTION = (
    r"\task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ "
    r"R\rightarrow I,\ S\rightarrow IV}$"
)


def test_shared_match_rules_use_one_math_expression_and_two_columns():
    """The shared examples preserve the exact final and problem-only contracts."""
    assert r"\begin{tasks}(2)" in MATCH_OPTION_FORMAT_RULES
    assert MARKED_OPTION in MATCH_OPTION_FORMAT_RULES
    assert r"outside the closing `$`" in MATCH_OPTION_FORMAT_RULES

    assert r"\begin{tasks}(2)" in MATCH_OPTION_FORMAT_RULES_UNMARKED
    assert UNMARKED_OPTION in MATCH_OPTION_FORMAT_RULES_UNMARKED
    assert MARKED_OPTION not in MATCH_OPTION_FORMAT_RULES_UNMARKED


@pytest.mark.parametrize(
    "prompt_getter",
    [
        physics_scanner.get_prompt,
        chemistry_scanner.get_prompt,
        mathematics_scanner.get_prompt,
        biology_scanner.get_prompt,
    ],
)
def test_full_match_scanners_include_marked_compact_option_rule(prompt_getter):
    """Every full scanner emits one compact math block and marks it afterward."""
    prompt = prompt_getter("match")
    assert MATCH_OPTION_FORMAT_RULES.strip() in prompt
    assert MARKED_OPTION in prompt
    assert r"\task $\mathrm{a\rightarrow" in prompt


@pytest.mark.parametrize("subject", ["physics", "chemistry", "mathematics", "biology"])
def test_problem_only_match_scanners_include_unmarked_compact_option_rule(subject):
    """The two-stage scanner uses the same typography without pre-marking answers."""
    module = import_module(
        f"vbagent.prompts.content_generation.scanner.{subject}.problem_only"
    )
    prompt = module.get_problem_prompt("match")

    assert MATCH_OPTION_FORMAT_RULES_UNMARKED.strip() in prompt
    assert UNMARKED_OPTION in prompt
    assert MARKED_OPTION not in prompt
    assert "Match the Following - Problem Extraction" in prompt


def test_converter_match_instructions_include_marked_compact_option_rule():
    """Format conversion follows the same match-option output contract."""
    instructions = get_format_instructions("match")
    assert MATCH_OPTION_FORMAT_RULES.strip() in instructions
    assert MARKED_OPTION in instructions
    assert r"\task $\mathrm{a\rightarrow" in instructions
