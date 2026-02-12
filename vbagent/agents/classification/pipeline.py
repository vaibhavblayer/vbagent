"""Classification pipeline orchestrator.

Coordinates multiple specialized agents for comprehensive classification.
"""

from pathlib import Path
from typing import Optional, Literal

from vbagent.models.classification_v2 import (
    ClassificationResult,
    PrimaryClassification,
    DiagramAnalysis,
    DifficultyAssessment,
)


class ClassificationPipeline:
    """Orchestrates multi-agent classification pipeline.
    
    Supports multiple input modalities:
    - image: Question images
    - latex: LaTeX text files
    - idea: Generate from concepts
    - multi_problem: Combine multiple problems
    """
    
    def __init__(self):
        """Initialize pipeline with lazy agent loading."""
        self._image_classifier = None
        self._latex_classifier = None
        self._diagram_analyzer = None
        self._difficulty_assessor = None
        self._idea_generator = None
        self._problem_combiner = None
        self._tikz_checker = None
    
    @property
    def image_classifier(self):
        """Lazy load image classifier"""
        if self._image_classifier is None:
            from .image_classifier import create_image_classifier_agent
            from vbagent.config import get_config
            self._image_classifier = create_image_classifier_agent(get_config().subject)
        return self._image_classifier
    
    @property
    def latex_classifier(self):
        """Lazy load LaTeX classifier"""
        if self._latex_classifier is None:
            from .latex_classifier import create_latex_classifier_agent
            from vbagent.config import get_config
            self._latex_classifier = create_latex_classifier_agent(get_config().subject)
        return self._latex_classifier
    
    @property
    def diagram_analyzer(self):
        """Lazy load diagram analyzer"""
        if self._diagram_analyzer is None:
            from .diagram_analyzer import create_diagram_analyzer_agent
            from vbagent.config import get_config
            self._diagram_analyzer = create_diagram_analyzer_agent(get_config().subject)
        return self._diagram_analyzer
    
    @property
    def difficulty_assessor(self):
        """Lazy load difficulty assessor"""
        if self._difficulty_assessor is None:
            from .difficulty_assessor import create_difficulty_assessor_agent
            from vbagent.config import get_config
            self._difficulty_assessor = create_difficulty_assessor_agent(get_config().subject)
        return self._difficulty_assessor
    
    @property
    def idea_generator(self):
        """Lazy load idea generator"""
        if self._idea_generator is None:
            from .idea_generator import create_idea_generator_agent
            from vbagent.config import get_config
            self._idea_generator = create_idea_generator_agent(get_config().subject)
        return self._idea_generator
    
    @property
    def problem_combiner(self):
        """Lazy load problem combiner"""
        if self._problem_combiner is None:
            from .problem_combiner import create_problem_combiner_agent
            self._problem_combiner = create_problem_combiner_agent()
        return self._problem_combiner
    
    def classify_from_image(
        self,
        image_path: str,
        subject: Optional[str] = None
    ) -> PrimaryClassification:
        """Step 1: Classify from image (Agent 1)"""
        from .image_classifier import classify_from_image
        return classify_from_image(image_path, subject)
    
    def classify_from_latex(
        self,
        latex_content: str,
        subject: Optional[str] = None
    ) -> PrimaryClassification:
        """Step 1: Classify from LaTeX (Agent 4)"""
        from .latex_classifier import classify_from_latex
        return classify_from_latex(latex_content, subject)
    
    def analyze_diagram(
        self,
        image_path: Optional[str],
        latex_content: Optional[str],
        primary: PrimaryClassification
    ) -> Optional[DiagramAnalysis]:
        """Step 2: Analyze diagram (Agent 2) - Conditional"""
        if not primary.has_diagram:
            return None
        
        if not image_path:
            return None
        
        from .diagram_analyzer import analyze_diagram
        return analyze_diagram(image_path, primary)
    
    def assess_difficulty(
        self,
        image_path: Optional[str],
        latex_content: str,
        primary: PrimaryClassification,
        diagram: Optional[DiagramAnalysis],
        tikz_code: Optional[str] = None
    ) -> DifficultyAssessment:
        """Step 3: Assess difficulty (Agent 3) - After scan"""
        from .difficulty_assessor import assess_difficulty
        return assess_difficulty(latex_content, primary, diagram, tikz_code)
    
    def process(
        self,
        input_data: str,
        input_type: Literal["image", "latex", "idea", "multi_problem"] = "image",
        subject: Optional[str] = None,
        latex_content: Optional[str] = None,
        tikz_code: Optional[str] = None
    ) -> ClassificationResult:
        """Complete classification pipeline.
        
        Args:
            input_data: Path to image/latex file, or data for generation
            input_type: Type of input
            subject: Subject override
            latex_content: LaTeX content (for difficulty assessment)
            tikz_code: TikZ code (for difficulty assessment)
        
        Returns:
            Complete ClassificationResult
        """
        # Step 1: Primary classification
        if input_type == "image":
            primary = self.classify_from_image(input_data, subject)
        elif input_type == "latex":
            with open(input_data) as f:
                latex_text = f.read()
            primary = self.classify_from_latex(latex_text, subject)
        elif input_type == "idea":
            # TODO: Generate problem from idea
            raise NotImplementedError("Idea generator not yet implemented")
        elif input_type == "multi_problem":
            # TODO: Combine problems
            raise NotImplementedError("Problem combiner not yet implemented")
        else:
            raise ValueError(f"Unknown input type: {input_type}")
        
        # Step 2: Diagram analysis (conditional)
        diagram = None
        if primary.has_diagram and input_type == "image":
            diagram = self.analyze_diagram(input_data, latex_content, primary)
        
        # Step 3: Difficulty assessment (if latex_content provided)
        difficulty = None
        if latex_content:
            difficulty = self.assess_difficulty(
                input_data if input_type == "image" else None,
                latex_content,
                primary,
                diagram,
                tikz_code
            )
        
        # Combine results
        return ClassificationResult.from_agents(primary, diagram, difficulty)


# Global pipeline instance
_pipeline = None


def get_pipeline() -> ClassificationPipeline:
    """Get global pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = ClassificationPipeline()
    return _pipeline
