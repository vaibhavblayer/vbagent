"""Question, subject, diagram, taxonomy, and difficulty classifiers."""

from .question_classifier import (
    QuestionClassification,
    classify_primary_image,
    classify_question_image,
    create_question_classifier,
    to_diagram_analysis,
    to_primary_classification,
)
from .latex_classifier import classify_from_latex
from .diagram_classifier import (
    classify_diagram_description,
    classify_diagram_image,
)
from .difficulty_assessor import assess_difficulty
from .taxonomy_classifier import (
    classify_taxonomy,
    create_taxonomy_classifier_agent,
    get_taxonomy_classifier_prompt,
)

# Compatibility exports retained for existing library callers.
from .image_classifier import classify_from_image
from vbagent.agents.content_generation.idea_generator import generate_from_idea
from vbagent.agents.content_generation.problem_combiner import combine_problems
from vbagent.agents.diagram.tikz_checker import check_and_fix_tikz, validate_tikz

__all__ = [
    # Canonical question classification
    "QuestionClassification",
    "create_question_classifier",
    "classify_question_image",
    "classify_primary_image",
    "to_primary_classification",
    "to_diagram_analysis",
    # Specialized classifiers
    "classify_from_latex",
    "classify_diagram_image",
    "classify_diagram_description",
    "assess_difficulty",
    "classify_taxonomy",
    "create_taxonomy_classifier_agent",
    "get_taxonomy_classifier_prompt",
    # Compatibility exports
    "classify_from_image",
    "generate_from_idea",
    "combine_problems",
    "validate_tikz",
    "check_and_fix_tikz",
]
