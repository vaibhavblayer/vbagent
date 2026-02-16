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
    """Test routing from primary classification."""
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        chapter="Mechanics",
        topic="Forces and Motion",
        subtopic="FBD",
        has_diagram=True
    )
    
    agent = route_tikz_agent(primary=primary)
    assert agent == "fbd"


def test_route_default():
    """Test default routing."""
    agent = route_tikz_agent()
    assert agent == "generic"


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
