"""Enhanced classification models for multi-agent pipeline.

Version 2.0 of classification system with support for:
- Multiple input modalities (image, LaTeX, ideas, combinations)
- Detailed diagram analysis
- Context-aware difficulty assessment
- Problem generation and combination
- TikZ validation
"""

from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# Enums
QuestionType = Literal[
    "mcq_sc", "mcq_mc", "subjective",
    "assertion_reason", "passage", "match"
]

Difficulty = Literal["easy", "medium", "hard"]

DiagramCategory = Literal[
    "mechanics", "kinematics", "circuits", "optics", "waves",
    "thermodynamics", "organic", "inorganic", "graphs", "geometry", "none"
]

DiagramComplexity = Literal["simple", "moderate", "complex"]

CognitiveLevel = Literal[
    "remember", "understand", "apply",
    "analyze", "evaluate", "create"
]

CombinationStrategy = Literal["sequential", "parallel", "nested"]


# Agent 1: Primary Classification (Image or LaTeX)
class PrimaryClassification(BaseModel):
    """Output from Agent 1 (Image Classifier) or Agent 4 (LaTeX Classifier)"""
    model_config = ConfigDict(extra='forbid')
    
    subject: str
    question_type: QuestionType
    chapter: str
    topic: str
    subtopic: str
    has_diagram: bool
    num_options: Optional[int] = None
    key_concepts: list[str] = Field(default_factory=list)
    requires_calculus: bool = False
    estimated_marks: int = 4
    time_estimate_minutes: int = 3
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Metadata
    classified_from: Literal["image", "latex"] = "image"
    classified_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Agent 2: Diagram Analysis
class DiagramFeatures(BaseModel):
    """Visual features of the diagram"""
    model_config = ConfigDict(extra='forbid')
    
    has_labels: bool = False
    has_measurements: bool = False
    has_vectors: bool = False
    has_grid: bool = False
    coordinate_system: Optional[str] = None
    num_objects: int = 0


class TikZRequirements(BaseModel):
    """TikZ generation requirements"""
    model_config = ConfigDict(extra='forbid')
    
    libraries: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    complexity_score: int = Field(ge=1, le=10, default=5)


class DiagramAnalysis(BaseModel):
    """Output from Agent 2: Diagram Analyzer"""
    model_config = ConfigDict(extra='forbid')
    
    diagram_type: str
    diagram_category: DiagramCategory
    diagram_complexity: DiagramComplexity
    diagram_elements: list[str] = Field(default_factory=list)
    diagram_features: DiagramFeatures = Field(default_factory=DiagramFeatures)
    tikz_requirements: TikZRequirements = Field(default_factory=TikZRequirements)
    suggested_tikz_agent: str = "generic"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Agent 3: Difficulty Assessment
class DifficultyFactors(BaseModel):
    """Factors contributing to difficulty"""
    model_config = ConfigDict(extra='forbid')
    
    concept_complexity: Literal["low", "moderate", "high"] = "moderate"
    calculation_complexity: Literal["low", "moderate", "high"] = "moderate"
    multi_step: bool = False
    requires_visualization: bool = False
    formula_complexity: Literal["low", "moderate", "high"] = "moderate"
    diagram_complexity: Optional[Literal["low", "moderate", "high"]] = None


class ProblemStructure(BaseModel):
    """Structure of the problem"""
    model_config = ConfigDict(extra='forbid')
    
    has_given_data: bool = False
    has_find_statement: bool = False
    has_constraints: bool = False
    is_multi_part: bool = False


class ExamRelevance(BaseModel):
    """Relevance to different exams"""
    model_config = ConfigDict(extra='forbid')
    
    jee_main: float = Field(ge=0.0, le=1.0, default=0.5)
    jee_advanced: float = Field(ge=0.0, le=1.0, default=0.5)
    neet: float = Field(ge=0.0, le=1.0, default=0.5)


class DifficultyAssessment(BaseModel):
    """Output from Agent 3: Difficulty Assessor"""
    model_config = ConfigDict(extra='forbid')
    
    difficulty: Difficulty
    difficulty_score: float = Field(ge=1.0, le=10.0)
    difficulty_factors: DifficultyFactors = Field(default_factory=DifficultyFactors)
    difficulty_reasoning: str
    expected_solve_time_minutes: int
    expected_error_rate: float = Field(ge=0.0, le=1.0, default=0.3)
    prerequisite_concepts: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    cognitive_level: CognitiveLevel = "apply"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Additional metadata
    solution_approach: list[str] = Field(default_factory=list)
    required_formulas: list[str] = Field(default_factory=list)
    problem_structure: ProblemStructure = Field(default_factory=ProblemStructure)
    exam_relevance: ExamRelevance = Field(default_factory=ExamRelevance)
    learning_objectives: list[str] = Field(default_factory=list)
    tags_auto: list[str] = Field(default_factory=list)
    assessed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Agent 5: Idea Generator
class GeneratedProblem(BaseModel):
    """Output from Agent 5: Idea-to-Problem Generator"""
    model_config = ConfigDict(extra='allow')  # Allow for generation_metadata flexibility
    
    problem_latex: str
    solution_latex: str
    alternate_solution_latex: Optional[str] = None
    idea_latex: str
    diagram_description: Optional[str] = None
    
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Contains: source_ideas, formulas_used, concepts_covered
    
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Agent 6: Problem Combiner
class CombinedProblem(BaseModel):
    """Output from Agent 6: Multi-Problem Combiner"""
    model_config = ConfigDict(extra='allow')  # Allow for combination_metadata flexibility
    
    combined_problem_latex: str
    combined_solution_latex: str
    combined_ideas: list[str] = Field(default_factory=list)
    source_problems: list[int] = Field(default_factory=list)
    
    combination_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Contains: strategy_used, subjects_combined, connection_points, difficulty_justification
    
    combined_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Agent 7: TikZ Validation
class TikZError(BaseModel):
    """A single TikZ error"""
    model_config = ConfigDict(extra='forbid')
    
    type: str  # "syntax", "missing_library", "undefined_command"
    line: int
    message: str
    severity: Literal["error", "warning"] = "error"


class TikZFix(BaseModel):
    """A fix applied to TikZ code"""
    model_config = ConfigDict(extra='forbid')
    
    type: str
    description: str
    before: str
    after: str


class TikZValidation(BaseModel):
    """Output from Agent 7: TikZ Checker/Fixer"""
    model_config = ConfigDict(extra='allow')  # Allow for validation_metadata flexibility
    
    is_valid: bool
    compilation_status: Literal["success", "fixed", "failed"]
    fixed_tikz_code: Optional[str] = None
    
    errors_found: list[TikZError] = Field(default_factory=list)
    fixes_applied: list[TikZFix] = Field(default_factory=list)
    
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Contains: libraries_used, packages_required, complexity_score, compilation_time_ms
    
    suggestions: list[str] = Field(default_factory=list)
    validated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# Complete Classification Result (combines all agents)
class ClassificationResult(BaseModel):
    """Complete classification result combining all agents.
    
    This is the unified result that can be built incrementally
    as different agents complete their work.
    """
    
    # From Agent 1/4: Primary Classification
    subject: str
    question_type: QuestionType
    chapter: str
    topic: str
    subtopic: str
    has_diagram: bool
    num_options: Optional[int] = None
    key_concepts: list[str] = Field(default_factory=list)
    requires_calculus: bool = False
    estimated_marks: int = 4
    time_estimate_minutes: int = 3
    
    # From Agent 2: Diagram Analysis (optional)
    diagram_type: Optional[str] = None
    diagram_category: Optional[DiagramCategory] = None
    diagram_complexity: Optional[DiagramComplexity] = None
    diagram_elements: list[str] = Field(default_factory=list)
    diagram_features: Optional[DiagramFeatures] = None
    tikz_requirements: Optional[TikZRequirements] = None
    suggested_tikz_agent: Optional[str] = None
    
    # From Agent 3: Difficulty Assessment (optional, filled after scan)
    difficulty: Optional[Difficulty] = None
    difficulty_score: Optional[float] = None
    difficulty_factors: Optional[DifficultyFactors] = None
    difficulty_reasoning: Optional[str] = None
    expected_solve_time_minutes: Optional[int] = None
    expected_error_rate: Optional[float] = None
    prerequisite_concepts: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    cognitive_level: Optional[CognitiveLevel] = None
    solution_approach: list[str] = Field(default_factory=list)
    required_formulas: list[str] = Field(default_factory=list)
    problem_structure: Optional[ProblemStructure] = None
    exam_relevance: Optional[ExamRelevance] = None
    learning_objectives: list[str] = Field(default_factory=list)
    tags_auto: list[str] = Field(default_factory=list)
    
    # Metadata
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    classification_version: str = "2.0"
    classified_from: Literal["image", "latex", "generated", "combined"] = "image"
    
    @classmethod
    def from_primary(cls, primary: PrimaryClassification) -> "ClassificationResult":
        """Create from primary classification only"""
        return cls(
            subject=primary.subject,
            question_type=primary.question_type,
            chapter=primary.chapter,
            topic=primary.topic,
            subtopic=primary.subtopic,
            has_diagram=primary.has_diagram,
            num_options=primary.num_options,
            key_concepts=primary.key_concepts,
            requires_calculus=primary.requires_calculus,
            estimated_marks=primary.estimated_marks,
            time_estimate_minutes=primary.time_estimate_minutes,
            confidence=primary.confidence,
            classified_from=primary.classified_from,
        )
    
    @classmethod
    def from_agents(
        cls,
        primary: PrimaryClassification,
        diagram: Optional[DiagramAnalysis] = None,
        difficulty: Optional[DifficultyAssessment] = None
    ) -> "ClassificationResult":
        """Combine results from multiple agents"""
        result = cls.from_primary(primary)
        
        if diagram:
            result.diagram_type = diagram.diagram_type
            result.diagram_category = diagram.diagram_category
            result.diagram_complexity = diagram.diagram_complexity
            result.diagram_elements = diagram.diagram_elements
            result.diagram_features = diagram.diagram_features
            result.tikz_requirements = diagram.tikz_requirements
            result.suggested_tikz_agent = diagram.suggested_tikz_agent
        
        if difficulty:
            result.difficulty = difficulty.difficulty
            result.difficulty_score = difficulty.difficulty_score
            result.difficulty_factors = difficulty.difficulty_factors
            result.difficulty_reasoning = difficulty.difficulty_reasoning
            result.expected_solve_time_minutes = difficulty.expected_solve_time_minutes
            result.expected_error_rate = difficulty.expected_error_rate
            result.prerequisite_concepts = difficulty.prerequisite_concepts
            result.common_mistakes = difficulty.common_mistakes
            result.cognitive_level = difficulty.cognitive_level
            result.solution_approach = difficulty.solution_approach
            result.required_formulas = difficulty.required_formulas
            result.problem_structure = difficulty.problem_structure
            result.exam_relevance = difficulty.exam_relevance
            result.learning_objectives = difficulty.learning_objectives
            result.tags_auto = difficulty.tags_auto
        
        return result
