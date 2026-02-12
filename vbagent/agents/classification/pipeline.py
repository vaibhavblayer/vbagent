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
            from vbagent.agents.classifier import create_classifier_agent
            from vbagent.config import get_config
            self._image_classifier = create_classifier_agent(get_config().subject)
        return self._image_classifier
    
    @property
    def latex_classifier(self):
        """Lazy load LaTeX classifier"""
        if self._latex_classifier is None:
            # TODO: Implement LaTeX classifier
            pass
        return self._latex_classifier
    
    @property
    def diagram_analyzer(self):
        """Lazy load diagram analyzer"""
        if self._diagram_analyzer is None:
            # TODO: Implement diagram analyzer
            pass
        return self._diagram_analyzer
    
    @property
    def difficulty_assessor(self):
        """Lazy load difficulty assessor"""
        if self._difficulty_assessor is None:
            # TODO: Implement difficulty assessor
            pass
        return self._difficulty_assessor
    
    def classify_from_image(
        self,
        image_path: str,
        subject: Optional[str] = None
    ) -> PrimaryClassification:
        """Step 1: Classify from image (Agent 1)"""
        from vbagent.agents.classifier import classify
        
        result = classify(image_path, subject)
        
        # Convert to PrimaryClassification
        return PrimaryClassification(
            subject=result.subject if hasattr(result, 'subject') else subject or "physics",
            question_type=result.question_type,
            chapter=result.chapter,
            topic=result.topic,
            subtopic=result.subtopic,
            has_diagram=result.has_diagram,
            num_options=result.num_options,
            key_concepts=result.key_concepts,
            requires_calculus=result.requires_calculus,
            confidence=result.confidence,
            classified_from="image"
        )
    
    def classify_from_latex(
        self,
        latex_content: str,
        subject: Optional[str] = None
    ) -> PrimaryClassification:
        """Step 1: Classify from LaTeX (Agent 4)"""
        # TODO: Implement LaTeX classification
        raise NotImplementedError("LaTeX classifier not yet implemented")
    
    def analyze_diagram(
        self,
        image_path: Optional[str],
        latex_content: Optional[str],
        primary: PrimaryClassification
    ) -> Optional[DiagramAnalysis]:
        """Step 2: Analyze diagram (Agent 2) - Conditional"""
        if not primary.has_diagram:
            return None
        
        # TODO: Implement diagram analyzer
        raise NotImplementedError("Diagram analyzer not yet implemented")
    
    def assess_difficulty(
        self,
        image_path: Optional[str],
        latex_content: str,
        primary: PrimaryClassification,
        diagram: Optional[DiagramAnalysis],
        tikz_code: Optional[str] = None
    ) -> DifficultyAssessment:
        """Step 3: Assess difficulty (Agent 3) - After scan"""
        # TODO: Implement difficulty assessor
        raise NotImplementedError("Difficulty assessor not yet implemented")
    
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
        if primary.has_diagram:
            try:
                diagram = self.analyze_diagram(
                    input_data if input_type == "image" else None,
                    latex_content,
                    primary
                )
            except NotImplementedError:
                # Diagram analyzer not ready yet
                pass
        
        # Step 3: Difficulty assessment (if latex_content provided)
        difficulty = None
        if latex_content:
            try:
                difficulty = self.assess_difficulty(
                    input_data if input_type == "image" else None,
                    latex_content,
                    primary,
                    diagram,
                    tikz_code
                )
            except NotImplementedError:
                # Difficulty assessor not ready yet
                pass
        
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
