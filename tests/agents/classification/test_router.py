"""Tests for TikZ router."""

import pytest

from vbagent.agents.diagram.tikz_router import (
    route_tikz_agent,
    get_agent_capabilities,
)
from vbagent.models.classification import (
    DiagramAnalysis,
    PrimaryClassification,
)


def test_route_with_agent_suggestion():
    """Test routing with Agent 2 suggestion."""
    diagram = DiagramAnalysis(
        diagram_type="free_body",
        diagram_category="mechanics",
        diagram_complexity="simple",
        suggested_tikz_agent="fbd"
    )
    
    agent = route_tikz_agent(diagram=diagram)
    assert agent == "fbd"


def test_route_with_circuit_suggestion():
    """Test routing with circuit suggestion."""
    diagram = DiagramAnalysis(
        diagram_type="circuit_diagram",
        diagram_category="circuits",
        diagram_complexity="moderate",
        suggested_tikz_agent="circuit"
    )
    
    agent = route_tikz_agent(diagram=diagram)
    assert agent == "circuit"


def test_route_with_optics_suggestion():
    """Test routing with optics suggestion."""
    diagram = DiagramAnalysis(
        diagram_type="ray_diagram",
        diagram_category="optics",
        diagram_complexity="simple",
        suggested_tikz_agent="optics"
    )
    
    agent = route_tikz_agent(diagram=diagram)
    assert agent == "optics"


def test_route_from_primary():
    """Test routing from primary classification (simplified)."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True
    )
    
    agent = route_tikz_agent(primary=primary)
    assert agent == "generic"


def test_route_default():
    """Test default routing."""
    agent = route_tikz_agent()
    assert agent == "generic"


@pytest.mark.parametrize(
    ("diagram_type", "expected"),
    [
        ("apparatus_setup", "setup"),
        ("logic_gate", "gates"),
        ("number_line", "number_line"),
        ("venn_set", "venn_diagram"),
        ("calculus_function", "function_graph"),
        ("coordinate_conic", "coordinate_geometry"),
        ("geometric_triangle", "geometric_figure"),
        ("organic_structure", "organic_structure"),
        ("reaction_mechanism", "reaction_mechanism"),
        ("orbital", "orbital"),
        ("lewis", "lewis_structure"),
        ("chemical_equation", "chemical_equation"),
        ("enthalpy", "energy_diagram"),
        ("force", "fbd"),
        ("circuit", "circuit"),
        ("incline", "mechanics"),
        ("standing_wave", "wave"),
        ("plot", "graph"),
        ("ray", "optics"),
    ],
)
def test_manual_diagram_type_routes(diagram_type, expected):
    assert route_tikz_agent(diagram_type=diagram_type) == expected


def test_problem_context_redirects_fbd_to_setup():
    assert route_tikz_agent(diagram_type="fbd", diagram_context="problem") == "setup"


def test_get_agent_capabilities():
    """Test agent capabilities retrieval."""
    caps = get_agent_capabilities("fbd")
    
    assert caps["name"] == "Free Body Diagram Agent"
    assert "forces" in caps["best_for"]
    assert len(caps["specializes_in"]) > 0


def test_priority_order():
    """Test that Agent 2 suggestion takes priority."""
    diagram = DiagramAnalysis(
        diagram_type="circuit_diagram",  # Would route to circuit
        diagram_category="circuits",
        diagram_complexity="simple",
        suggested_tikz_agent="generic"  # But suggestion is generic
    )
    
    agent = route_tikz_agent(diagram=diagram)
    assert agent == "generic"  # Suggestion wins


def test_all_agent_types():
    """Test all supported agent types."""
    agents = ["fbd", "circuit", "graph", "optics", "generic"]
    
    for agent_type in agents:
        caps = get_agent_capabilities(agent_type)
        assert "name" in caps
        assert "best_for" in caps
