"""Regression tests for construction-first TikZ coordinate prompts."""

from importlib import import_module

import pytest

from vbagent.agents.diagram import base as diagram_base
from vbagent.agents.diagram.base import DiagramAgent, DiagramAgentConfig
from vbagent.agents.diagram.mathematics.function_graph import (
    validate_function_graph_output,
)
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


def test_mathematics_style_agent_receives_forwarded_solution_context(monkeypatch):
    """Simple-reference agents must still receive exact diagram requirements."""
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(diagram_base, "create_agent", fake_create_agent)
    agent = DiagramAgent(
        DiagramAgentConfig(
            name="MathContextProbe",
            agent_type="tikz",
            system_prompt="MATH PROMPT",
            user_template="{description}",
            user_template_from_problem="{problem}",
            has_rich_context=False,
        )
    )

    agent.create_agent(
        use_context=False,
        problem_text=r"Plot $f(x)=x+1$.",
        solution_context="Show its intercept and domain.",
        values={"function": "x+1", "x_intercept": "-1"},
        labels=[r"$f(x)=x+1$", r"$(-1,0)$"],
    )

    instructions = captured["instructions"]
    assert r"Plot $f(x)=x+1$." in instructions
    assert "Show its intercept and domain." in instructions
    assert "function=x+1" in instructions
    assert "x_intercept=-1" in instructions
    assert r"$f(x)=x+1$" in instructions
    assert r"$(-1,0)$" in instructions


@pytest.mark.parametrize("labels", [[], None])
def test_empty_labels_are_an_explicit_preference_not_missing_context(monkeypatch, labels):
    monkeypatch.setattr(diagram_base, "create_agent", lambda **kwargs: kwargs)
    agent = DiagramAgent(DiagramAgentConfig(
        name="LabelProbe", agent_type="tikz", system_prompt="MATH PROMPT",
        user_template="Draw.", user_template_from_problem="{problem}",
    ))

    output = agent.create_agent(use_context=False, values={"minimum": "(0,1)"}, labels=labels)

    assert "not requests to label every value" in output["instructions"]
    assert ("## Visible Labels" in output["instructions"]) == (labels is not None)


def test_image_input_does_not_drop_the_solution_diagram_description():
    agent = DiagramAgent(DiagramAgentConfig(
        name="ImageProbe", agent_type="tikz", system_prompt="MATH PROMPT",
        user_template="Draw using the image.", user_template_from_problem="{problem}",
    ))

    message = agent._build_user_message(
        image_path="source.png", description="Mark the minimum using exact axis ticks."
    )

    assert "Draw using the image." in message
    assert "Mark the minimum using exact axis ticks." in message


def test_tikz_checker_enforces_same_coordinate_discipline():
    """Post-generation review must preserve the generation prompt's geometry rules."""
    checklist = get_review_checklist("mathematics")
    assert "relative `++(dx,dy)`" in checklist
    assert "named-path intersections" in checklist
    assert "Do NOT round actual graph data" in checklist
    assert r"($(A)!0.5!(B)$)" in checklist


def test_shared_rule_structures_independent_panels_outside_tikz_canvas():
    assert "Independent Labeled Panels" in STYLE_DISCIPLINE
    assert r"\def\DiagramOne" in STYLE_DISCIPLINE
    assert r"\Diagram_1" in STYLE_DISCIPLINE
    assert r"\begin{multicols}{2}" in STYLE_DISCIPLINE
    assert r"\begin{enumerate}" in STYLE_DISCIPLINE
    assert "nesting level determine" in STYLE_DISCIPLINE
    assert "do not draw `(i)` or `(a)` as TikZ" in STYLE_DISCIPLINE
    assert "scope[shift=...]" in STYLE_DISCIPLINE


def test_function_graph_prompt_calls_out_independent_panel_collections():
    prompt = import_module(
        "vbagent.prompts.diagram.mathematics.function_graph"
    ).SYSTEM_PROMPT

    assert "Collections of Independent Graph Panels" in prompt
    assert "one oversized `tikzpicture`" in prompt
    assert "`multicols` + `enumerate`" in prompt


def test_function_graph_validator_accepts_plain_tikz_panel_plots():
    code = r"""\begingroup
\def\DiagramOne{\begin{tikzpicture}
\draw[thick] plot[domain=-1:1] (\x,{\x*\x});
\end{tikzpicture}}
\DiagramOne
\endgroup"""

    valid, error = validate_function_graph_output(code)

    assert valid is True
    assert error == ""


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
