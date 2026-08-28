"""Regression coverage for consistent teaching, fraction, and graph prompts."""

import re
from importlib import import_module
from pathlib import Path

import pytest

from vbagent.prompts.content_generation.idea_generator import get_idea_generator_prompt
from vbagent.prompts.content_generation.scanner import get_scanner_prompt
from vbagent.prompts.content_generation.solution import get_solution_prompt
from vbagent.prompts.latex_style import (
    DIAGRAM_SPECIFICATION_RULES,
    DISPLAY_FRACTION_RULES,
    GRAPH_CLARITY_RULES,
    MATHEMATICS_REASONING_RULES,
    SOLUTION_EXPLANATION_RULES,
)

SUBJECTS = ("physics", "chemistry", "mathematics", "biology")
QUESTION_TYPES = (
    "mcq_sc",
    "mcq_mc",
    "subjective",
    "match",
    "passage",
    "assertion_reason",
)


@pytest.mark.parametrize("subject", SUBJECTS)
@pytest.mark.parametrize("question_type", QUESTION_TYPES)
@pytest.mark.parametrize("getter", (get_scanner_prompt, get_solution_prompt))
def test_all_subject_type_routes_share_the_teaching_contract(
    getter, subject, question_type
):
    prompt = getter(question_type, subject)

    assert DISPLAY_FRACTION_RULES in prompt
    assert SOLUTION_EXPLANATION_RULES in prompt
    assert DIAGRAM_SPECIFICATION_RULES in prompt
    assert GRAPH_CLARITY_RULES in prompt
    if subject == "mathematics":
        assert MATHEMATICS_REASONING_RULES in prompt
    assert not re.search(
        r"show all (?:steps|work)|don't skip.*(?:algebra|obvious|calculations)|explain each step",
        prompt,
        re.IGNORECASE,
    )
    # Legacy fraction names are allowed only in the explicit prohibition.
    without_rule = prompt.replace(DISPLAY_FRACTION_RULES, "")
    assert not re.search(r"\\(?:frac|tfrac)(?![A-Za-z])", without_rule)


@pytest.mark.parametrize("subject", SUBJECTS)
def test_direct_scanner_exports_have_the_same_rules(subject):
    module = import_module(f"vbagent.prompts.content_generation.scanner.{subject}")
    for prompt in module.SCANNER_PROMPTS.values():
        assert SOLUTION_EXPLANATION_RULES in prompt
        assert GRAPH_CLARITY_RULES in prompt


@pytest.mark.parametrize("subject", ("physics", "chemistry", "mathematics"))
@pytest.mark.parametrize("question_type", QUESTION_TYPES)
def test_solution_only_scanners_share_rules_without_changing_ocr_scope(
    subject, question_type
):
    module = import_module(
        f"vbagent.prompts.content_generation.scanner.{subject}.solution_only"
    )
    prompt = module.get_solution_prompt(question_type)

    assert SOLUTION_EXPLANATION_RULES in prompt
    assert "preserve the source's reasoning" in prompt
    assert DISPLAY_FRACTION_RULES in prompt


@pytest.mark.parametrize("subject", SUBJECTS)
def test_authoring_and_format_repair_share_the_contract(subject):
    from vbagent.prompts.quality.format_checker import get_system_prompt

    for prompt in (get_idea_generator_prompt(subject), get_system_prompt(subject)):
        assert SOLUTION_EXPLANATION_RULES in prompt
        assert DISPLAY_FRACTION_RULES in prompt
        assert GRAPH_CLARITY_RULES in prompt


def test_converter_alternate_and_solution_repair_share_the_contract():
    for module_name in (
        "content_generation.converter",
        "content_generation.alternate",
        "quality.solution_checker",
    ):
        prompt = import_module(f"vbagent.prompts.{module_name}").SYSTEM_PROMPT
        assert SOLUTION_EXPLANATION_RULES in prompt
        assert DISPLAY_FRACTION_RULES in prompt
        assert GRAPH_CLARITY_RULES in prompt


def test_math_rules_preserve_the_two_domain_range_learning_points():
    assert (
        "minimum and unboundedness alone do not rule out gaps"
        in MATHEMATICS_REASONING_RULES
    )
    assert "overlap/gaps between branch ranges" in MATHEMATICS_REASONING_RULES
    assert "endpoint inclusion" in MATHEMATICS_REASONING_RULES
    assert "exact attainable values of the inner" in MATHEMATICS_REASONING_RULES
    assert "need not make the composition increasing" in MATHEMATICS_REASONING_RULES
    assert "positivity and the range in one calculation" in MATHEMATICS_REASONING_RULES


def test_no_active_prompt_or_reference_teaches_legacy_fraction_commands():
    root = Path(__file__).resolve().parents[3] / "vbagent"
    paths = list((root / "prompts").rglob("*.py"))
    paths += list((root / "references" / "samples").rglob("*.tex"))
    for path in paths:
        if path.name == "latex_style.py":
            continue
        assert not re.search(r"\\(?:frac|tfrac)(?![A-Za-z])", path.read_text()), path


def test_graph_generation_and_all_repair_modes_share_clarity_rules():
    from vbagent.agents.diagram.tikz_checker import _STRUCTURED_CHECKER_PROMPT
    from vbagent.prompts.diagram._style_discipline import STYLE_DISCIPLINE
    from vbagent.prompts.diagram.tikz_checker import (
        SYSTEM_PROMPT,
        build_patch_system_prompt,
        get_review_checklist,
    )

    prompts = [STYLE_DISCIPLINE, SYSTEM_PROMPT, _STRUCTURED_CHECKER_PROMPT]
    for subject in (*SUBJECTS, None):
        prompts.extend(
            (build_patch_system_prompt(subject), get_review_checklist(subject))
        )
    for name in ("mathematics.function_graph", "physics.graph"):
        prompts.append(import_module(f"vbagent.prompts.diagram.{name}").SYSTEM_PROMPT)
    for prompt in prompts:
        assert GRAPH_CLARITY_RULES in prompt
        assert DISPLAY_FRACTION_RULES in prompt


def test_graph_rule_removes_clutter_without_deleting_semantics():
    assert 'Do not write "open" or "closed" beside every marker' in GRAPH_CLARITY_RULES
    assert "Default to no grid" in GRAPH_CLARITY_RULES
    assert "Preserve labels/data explicitly required" in GRAPH_CLARITY_RULES
    assert "Allow room for display-style fractions" in GRAPH_CLARITY_RULES
    assert "Never connect a jump" in GRAPH_CLARITY_RULES
    assert "do not remove it for brevity" in GRAPH_CLARITY_RULES
    assert "only marks, mark=*, mark options={fill=white}" in GRAPH_CLARITY_RULES


def test_solver_diagram_specs_distinguish_construction_data_from_visible_labels():
    from vbagent.models.solution import DiagramRequirement, SolutionOutput
    from vbagent.prompts.content_generation.solution.mathematics.examples import (
        LOG_DOMAIN_RANGE_EXAMPLE,
    )

    result = SolutionOutput.model_validate(LOG_DOMAIN_RANGE_EXAMPLE)
    spec = result.diagram_requirements[0]
    assert spec.values["function"] == "ln(3*x^2-4*x+5)"
    assert spec.values["minimum_x"] == "2/3"
    assert spec.values["minimum_y"] == "ln(11/3)"
    assert spec.labels == []
    assert len(spec.annotations) == 1
    assert spec.diagram_id in result.solution_latex
    properties = DiagramRequirement.model_json_schema()["properties"]
    assert "not a request to label every value" in properties["values"]["description"]
    assert "Minimal indispensable" in properties["labels"]["description"]
    assert "Only essential drawing actions" in properties["annotations"]["description"]


def test_mathematics_examples_are_complete_valid_json_with_concise_answer_keys():
    import json

    from vbagent.models.solution import SolutionOutput
    from vbagent.prompts.content_generation.solution.mathematics.examples import (
        FACTORING_EXAMPLE_JSON,
        LOG_DOMAIN_RANGE_EXAMPLE_JSON,
    )

    for example in (FACTORING_EXAMPLE_JSON, LOG_DOMAIN_RANGE_EXAMPLE_JSON):
        output = SolutionOutput.model_validate(json.loads(example))
        assert output.final_answer_latex
        assert r"\begin{solution}" in output.solution_latex
        assert r"\begin{{solution}}" not in output.solution_latex
