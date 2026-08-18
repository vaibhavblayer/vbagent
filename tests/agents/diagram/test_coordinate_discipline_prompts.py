"""Regression tests for construction-first TikZ coordinate prompts."""

from importlib import import_module

import pytest

from vbagent.agents.diagram import base as diagram_base
from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.prompts.diagram._style_discipline import STYLE_DISCIPLINE
from vbagent.prompts.diagram.tikz_checker import get_review_checklist


PHYSICS_PROMPT_MODULES = [
    "circuit",
    "fbd",
    "gates",
    "generic",
    "graph",
    "mechanics",
    "optics",
    "setup",
    "wave",
]

MATHEMATICS_PROMPT_MODULES = [
    "coordinate_geometry",
    "function_graph",
    "geometric_figure",
    "number_line",
    "venn_diagram",
]


def test_shared_rule_prefers_relative_simple_and_calculated_coordinates():
    """The global diagram contract states the complete coordinate hierarchy."""
    assert "Coordinate Discipline — Build Geometry, Do Not Guess It" in STYLE_DISCIPLINE
    assert r"\draw (O) -- ++(1,0);" in STYLE_DISCIPLINE
    assert r"\draw (O) -- ++(0,1);" in STYLE_DISCIPLINE
    assert r"($(A)!0.5!(B)$)" in STYLE_DISCIPLINE
    assert "named-path intersections" in STYLE_DISCIPLINE.lower()
    assert "actual problem data" in STYLE_DISCIPLINE
    assert "0.145" in STYLE_DISCIPLINE and "2.347" in STYLE_DISCIPLINE


def test_diagram_agent_appends_coordinate_discipline(monkeypatch):
    """The runtime agent receives the rule in addition to its full subject prompt."""
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(diagram_base, "create_agent", fake_create_agent)
    agent = DiagramAgent(
        DiagramAgentConfig(
            name="PromptProbe",
            agent_type="tikz",
            system_prompt="SUBJECT PROMPT WITH ALL EXISTING EXAMPLES",
            user_template="{description}",
            user_template_from_problem="{problem}",
        )
    )

    agent.create_agent(use_context=False)

    instructions = captured["instructions"]
    assert "SUBJECT PROMPT WITH ALL EXISTING EXAMPLES" in instructions
    assert STYLE_DISCIPLINE in instructions


def test_tikz_checker_enforces_same_coordinate_discipline():
    """Post-generation review must preserve the generation prompt's geometry rules."""
    checklist = get_review_checklist("mathematics")
    assert "relative `++(dx,dy)`" in checklist
    assert "named-path intersections" in checklist
    assert "Do NOT round actual graph data" in checklist
    assert r"($(A)!0.5!(B)$)" in checklist


@pytest.mark.parametrize("module_name", PHYSICS_PROMPT_MODULES)
def test_physics_prompt_families_keep_substantial_examples(module_name):
    """Every Physics diagram family retains its detailed source prompt."""
    module = import_module(f"vbagent.prompts.diagram.physics.{module_name}")
    assert len(module.SYSTEM_PROMPT) > 2_000
    assert "```latex" in module.SYSTEM_PROMPT


@pytest.mark.parametrize("module_name", MATHEMATICS_PROMPT_MODULES)
def test_mathematics_prompt_families_keep_substantial_examples(module_name):
    """Every Mathematics diagram family retains its detailed source prompt."""
    module = import_module(f"vbagent.prompts.diagram.mathematics.{module_name}")
    assert len(module.SYSTEM_PROMPT) > 2_000
    assert "```latex" in module.SYSTEM_PROMPT


def test_physics_examples_construct_derived_geometry():
    """Key Physics examples use polar vectors, intersections, and relative moves."""
    mechanics = import_module("vbagent.prompts.diagram.physics.mechanics").SYSTEM_PROMPT
    optics = import_module("vbagent.prompts.diagram.physics.optics").SYSTEM_PROMPT
    circuit = import_module("vbagent.prompts.diagram.physics.circuit").SYSTEM_PROMPT

    assert r"++(45:2)" in mechanics
    assert "name intersections" in mechanics
    assert r"by=imageTop" in optics
    assert r"(imageTop |- O)" in optics
    assert "-1.125" not in optics
    assert r"(dl) -- ++(1,1) coordinate (P)" in circuit
    assert "4.375" not in circuit


def test_mathematics_examples_keep_exact_values_without_rounded_points():
    """Calculated mathematical points remain exact and reusable."""
    coordinate = import_module(
        "vbagent.prompts.diagram.mathematics.coordinate_geometry"
    ).SYSTEM_PROMPT
    functions = import_module(
        "vbagent.prompts.diagram.mathematics.function_graph"
    ).SYSTEM_PROMPT
    geometry = import_module(
        "vbagent.prompts.diagram.mathematics.geometric_figure"
    ).SYSTEM_PROMPT

    assert r"($(A)!0.5!(B)$)" in coordinate
    assert r"{-sqrt(5)}" in coordinate
    assert "2.236" not in coordinate
    assert r"\pgfmathsetmacro{\px}{3*sqrt(3)/2}" in coordinate
    assert "2.598" not in coordinate
    assert r"\pgfmathsetmacro{\xa}{1-sqrt(2)}" in functions
    assert "-0.414" not in functions
    assert r"({3/2},{3*sqrt(3)/2})" in geometry
