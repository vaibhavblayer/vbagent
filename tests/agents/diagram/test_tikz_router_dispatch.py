"""Focused tests for registry-based TikZ generator dispatch."""

from types import SimpleNamespace
from typing import get_args

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


def test_simple_dispatch_only_forwards_supported_arguments(monkeypatch):
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
        problem_text="not supported",
        solution_context="not supported",
        values={"x": 2},
        labels=["x"],
        mcq_options=True,
    )

    assert received == {
        "image_path": None,
        "description": "x > 2",
        "use_context": False,
        "show_spinner": True,
    }


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
