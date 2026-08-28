"""Focused tests for registry-based TikZ generator dispatch."""

from types import SimpleNamespace
from typing import get_args

import pytest

from vbagent.agents.diagram import tikz_router


def test_every_agent_type_has_a_dispatch_path():
    special_agents = {"organic_structure", "biology_image"}

    assert set(get_args(tikz_router.AgentType)) == (
        set(tikz_router._GENERATOR_REGISTRY) | special_agents
    )


def test_physics_dispatch_forwards_rich_context(monkeypatch):
    received = {}

    def generate_fbd(**kwargs):
        received.update(kwargs)
        return "fbd output"

    monkeypatch.setattr(
        tikz_router,
        "import_module",
        lambda module: SimpleNamespace(generate_fbd=generate_fbd),
    )

    result = tikz_router._invoke_registered_generator(
        "fbd",
        image_path="problem.png",
        description="block on incline",
        use_context=True,
        show_spinner=False,
        problem_text="problem",
        solution_context="solution",
        values={"m": 2},
        labels=["m"],
        mcq_options=False,
    )

    assert result == "fbd output"
    assert received == {
        "image_path": "problem.png",
        "description": "block on incline",
        "use_context": True,
        "show_spinner": False,
        "problem_text": "problem",
        "solution_context": "solution",
        "values": {"m": 2},
        "labels": ["m"],
    }


def test_mathematics_dispatch_forwards_rich_context(monkeypatch):
    received = {}

    def generate_number_line(**kwargs):
        received.update(kwargs)
        return "number line"

    monkeypatch.setattr(
        tikz_router,
        "import_module",
        lambda module: SimpleNamespace(generate_number_line=generate_number_line),
    )

    tikz_router._invoke_registered_generator(
        "number_line",
        image_path=None,
        description="x > 2",
        use_context=False,
        show_spinner=True,
        problem_text="solve the inequality",
        solution_context="solution set has two rays",
        values={"x": 2},
        labels=["x"],
        mcq_options=True,
    )

    assert received == {
        "image_path": None,
        "description": "x > 2",
        "use_context": False,
        "show_spinner": True,
        "problem_text": "solve the inequality",
        "solution_context": "solution set has two rays",
        "values": {"x": 2},
        "labels": ["x"],
    }


def test_every_mathematics_generator_accepts_rich_context():
    mathematics_agents = {
        "function_graph",
        "coordinate_geometry",
        "geometric_figure",
        "number_line",
        "venn_diagram",
    }

    for agent_type in mathematics_agents:
        assert (
            tikz_router._GENERATOR_REGISTRY[agent_type].forwards
            == tikz_router._RICH_CONTEXT_FORWARDS
        )


def test_generic_dispatch_supplies_default_description(monkeypatch):
    received = {}

    def generate_tikz(**kwargs):
        received.update(kwargs)
        return "generic output"

    monkeypatch.setattr(
        tikz_router,
        "import_module",
        lambda module: SimpleNamespace(generate_tikz=generate_tikz),
    )

    tikz_router._invoke_registered_generator(
        "generic",
        image_path=None,
        description=None,
        use_context=True,
        show_spinner=False,
        problem_text=None,
        solution_context=None,
        values=None,
        labels=None,
        mcq_options=False,
    )

    assert received["description"] == "Diagram"


def test_chemistry_context_is_parsed_once():
    context = tikz_router._parse_chemistry_context(
        "show_lone_pairs | mechanism_step: proton transfer | "
        "reaction_conditions: heat"
    )

    assert context == {
        "show_lone_pairs": "yes",
        "mechanism_step": "proton transfer",
        "reaction_conditions": "heat",
    }


def test_chemistry_context_preserves_explicit_no_and_colons_in_setting_values():
    context = tikz_router._parse_chemistry_context(
        "Construction context (not visible prose):\nUse the given data.\n\n"
        "Chemistry settings and construction data:\n"
        "show_lone_pairs: no\nshow_charges: yes\n"
        "mechanism_step: Step 1: proton transfer\n\n"
        "Required drawing actions (follow the requested representation):\n- Mark atoms."
    )

    assert context == {
        "show_lone_pairs": "no", "show_charges": "yes",
        "mechanism_step": "Step 1: proton transfer",
    }


@pytest.mark.parametrize("agent_type", ["generic", "energy_diagram", "chemical_equation"])
def test_generators_without_context_arguments_still_receive_the_drawing_spec(monkeypatch, agent_type):
    received = {}

    def generate(**kwargs):
        received.update(kwargs)
        return "DIAGRAM"

    function = tikz_router._GENERATOR_REGISTRY[agent_type].function
    monkeypatch.setattr(tikz_router, "import_module", lambda _: SimpleNamespace(**{function: generate}))
    tikz_router._invoke_registered_generator(
        agent_type, image_path=None, description="Purpose", use_context=False,
        show_spinner=False, problem_text="PROBLEM", solution_context="DRAWING ACTIONS",
        values={"exact_value": "11/3"}, labels=[], mcq_options=False,
    )

    assert "Purpose" in received["description"]
    assert "PROBLEM" in received["description"]
    assert "DRAWING ACTIONS" in received["description"]
    assert "exact_value: 11/3" in received["description"]
    assert "No additional text labels requested" in received["description"]
