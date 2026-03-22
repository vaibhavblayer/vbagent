"""Enhanced classification models for multi-agent pipeline.

Version 2.0 of classification system with support for:
- Multiple input modalities (image, LaTeX, ideas, combinations)
- Detailed diagram analysis
- Context-aware difficulty assessment
- Problem generation and combination
- TikZ validation
"""

from typing import Literal, Optional, Dict, Any, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

from .diagram import TikZRequirements, TikZError, TikZFix, TikZValidation


# Enums
QuestionType = Literal[
    "mcq_sc", "mcq_mc", "subjective",
    "assertion_reason", "passage", "match"
]

Subject = Literal["physics", "chemistry", "mathematics", "biology"]

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
    """Output from Agent 1 (Image Classifier) or Agent 4 (LaTeX Classifier)
    
    Simplified to 3 core fields for classification.
    """
    model_config = ConfigDict(extra='forbid')
    
    subject: Subject
    question_type: QuestionType
    has_diagram: bool
    
    # Metadata
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    classified_from: Literal["image", "latex"] = "image"
    classified_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @field_validator('classified_at', mode='before')
    @classmethod
    def fix_classified_at(cls, v):
        """Ensure classified_at is a timestamp, not a string like 'image'"""
        if v in ["image", "latex", "generated", "combined"]:
            return datetime.now().isoformat()
        return v


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
    
    # MCQ option diagrams detection
    has_option_diagrams: bool = Field(
        default=False,
        description="Whether this MCQ has diagrams in the answer options"
    )
    num_option_diagrams: int = Field(
        default=0,
        description="Number of options that contain diagrams (typically 4)"
    )
    option_diagram_type: str = Field(
        default="",
        description="Type of diagrams in the options (e.g., organic_structure, circuit, graph)"
    )
    option_diagram_descriptions: list[str] = Field(
        default_factory=list,
        description="Brief description of what each option diagram shows"
    )
    
    # Valid diagram types per subject (ClassVar to avoid Pydantic field annotation error)
    VALID_TYPES: ClassVar[Dict[str, list[str]]] = {
        "physics": ["fbd", "circuit", "graph", "optics", "generic"],
        "chemistry": ["organic_structure", "reaction_mechanism", "chemical_equation", 
                     "energy_diagram", "orbital", "lewis_structure", "generic"],
        "mathematics": ["number_line", "function_graph", "coordinate_geometry", 
                       "geometric_figure", "venn_diagram", "generic"],
    }
    
    # Mapping of common variations to correct types (ClassVar)
    TYPE_CORRECTIONS: ClassVar[Dict[str, str]] = {
        "reaction_scheme": "reaction_mechanism",
        "free_body": "fbd",
        "ray_diagram": "optics",
        "geometry": "geometric_figure",
        "coordinate_plane": "coordinate_geometry",
        "graph_plot": "function_graph",
        "molecular_structure": "organic_structure",
    }
    
    @field_validator('diagram_type')
    @classmethod
    def validate_diagram_type(cls, v: str) -> str:
        """Validate and correct diagram type"""
        # Apply corrections for common variations
        corrected = cls.TYPE_CORRECTIONS.get(v, v)
        
        # If it was corrected, return the corrected value
        if corrected != v:
            return corrected
        
        # Check if it's a valid type for any subject
        all_valid = set()
        for types in cls.VALID_TYPES.values():
            all_valid.update(types)
        
        if v not in all_valid:
            # If not valid, default to generic
            return "generic"
        
        return v


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


# Complete Classification Result (combines all agents)
class ClassificationResult(BaseModel):
    """Complete classification result combining Agents 1 and 2.
    
    Core classification + diagram analysis. Difficulty and taxonomy
    are stored separately via their own models.
    """
    
    # From Agent 1/4: Primary Classification
    subject: Subject
    question_type: QuestionType
    has_diagram: bool
    
    # From Agent 2: Diagram Analysis (optional)
    diagram_type: Optional[str] = None
    diagram_category: Optional[DiagramCategory] = None
    diagram_complexity: Optional[DiagramComplexity] = None
    diagram_elements: list[str] = Field(default_factory=list)
    diagram_features: Optional[DiagramFeatures] = None
    tikz_requirements: Optional[TikZRequirements] = None
    suggested_tikz_agent: Optional[str] = None
    
    # MCQ option diagrams
    has_option_diagrams: bool = False
    num_option_diagrams: int = 0
    option_diagram_type: str = ""
    option_diagram_descriptions: list[str] = Field(default_factory=list)
    
    # Metadata
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    classification_version: str = "2.0"
    classified_from: Literal["image", "latex", "generated", "combined"] = "image"
    classified_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @field_validator('classified_at', mode='before')
    @classmethod
    def fix_classified_at(cls, v):
        """Ensure classified_at is a timestamp, not a string like 'image'"""
        if v in ["image", "latex", "generated", "combined"]:
            return datetime.now().isoformat()
        return v
    
    @classmethod
    def from_primary(cls, primary: PrimaryClassification) -> "ClassificationResult":
        """Create from primary classification only"""
        return cls(
            subject=primary.subject,
            question_type=primary.question_type,
            has_diagram=primary.has_diagram,
            confidence=primary.confidence,
            classified_from=primary.classified_from,
        )
    
    @classmethod
    def from_agents(
        cls,
        primary: PrimaryClassification,
        diagram: Optional[DiagramAnalysis] = None,
    ) -> "ClassificationResult":
        """Combine results from primary + diagram agents"""
        result = cls.from_primary(primary)
        
        if diagram:
            result.diagram_type = diagram.diagram_type
            result.diagram_category = diagram.diagram_category
            result.diagram_complexity = diagram.diagram_complexity
            result.diagram_elements = diagram.diagram_elements
            result.diagram_features = diagram.diagram_features
            result.tikz_requirements = diagram.tikz_requirements
            result.suggested_tikz_agent = diagram.suggested_tikz_agent
            result.has_option_diagrams = diagram.has_option_diagrams
            result.num_option_diagrams = diagram.num_option_diagrams
            result.option_diagram_type = diagram.option_diagram_type
            result.option_diagram_descriptions = diagram.option_diagram_descriptions
        
        return result
