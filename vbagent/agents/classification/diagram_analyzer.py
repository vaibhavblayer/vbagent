"""Compatibility aliases for the renamed diagram classifier."""

from .diagram_classifier import (
    classify_diagram_description,
    classify_diagram_image,
    create_diagram_classifier,
)

create_diagram_analyzer_agent = create_diagram_classifier
analyze_diagram = classify_diagram_image
analyze_diagram_from_description = classify_diagram_description

__all__ = [
    "create_diagram_analyzer_agent",
    "analyze_diagram",
    "analyze_diagram_from_description",
]
