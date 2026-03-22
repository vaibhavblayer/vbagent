"""Classification agents package.

Multi-agent system for comprehensive question classification.
"""

from .image_classifier import classify_from_image
from .latex_classifier import classify_from_latex
from .diagram_analyzer import analyze_diagram
from .difficulty_assessor import assess_difficulty
from .idea_generator import generate_from_idea
from .problem_combiner import combine_problems
from .taxonomy_classifier import classify_taxonomy, create_taxonomy_classifier_agent, get_taxonomy_classifier_prompt
from .unified_classifier import classify_and_analyze, to_primary, to_diagram_analysis, UnifiedClassificationResult
from vbagent.agents.diagram.tikz_checker import validate_tikz, check_and_fix_tikz

__all__ = [
    # Agent functions
    "classify_from_image",
    "classify_from_latex",
    "analyze_diagram",
    "assess_difficulty",
    "generate_from_idea",
    "combine_problems",
    "validate_tikz",
    "check_and_fix_tikz",
    # Taxonomy
    "classify_taxonomy",
    "create_taxonomy_classifier_agent",
    "get_taxonomy_classifier_prompt",
    # Unified classifier
    "classify_and_analyze",
    "to_primary",
    "to_diagram_analysis",
    "UnifiedClassificationResult",
]
