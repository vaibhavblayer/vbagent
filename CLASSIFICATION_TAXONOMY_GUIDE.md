# Classification Taxonomy Guide

## Overview

The classification agent now uses predefined taxonomies of chapters and topics for each subject. This ensures consistency in metadata and makes it easier to query and organize questions.

## Changes Made

### 1. New Taxonomy Module (`vbagent/prompts/subjects/taxonomy.py`)

Created a comprehensive taxonomy system with:
- **Physics**: 27 chapters with 100+ topics
- **Chemistry**: 28 chapters with 120+ topics
- **Mathematics**: 10 chapters with 50+ topics
- **Biology**: 38 chapters with 150+ topics

Each chapter contains a list of related topics.

### 2. Updated Classification Model

**Added `chapter` field** to `ClassificationResult`:
```python
class ClassificationResult(BaseModel):
    question_type: QuestionType
    difficulty: Difficulty
    chapter: str  # NEW: Chapter name from predefined list
    topic: str    # Now from predefined list
    subtopic: str
    has_diagram: bool
    diagram_type: DiagramType | None
    num_options: int | None
    estimated_marks: int
    key_concepts: list[str]
    requires_calculus: bool
    confidence: float
```

### 3. Updated Classifier Prompt

The classifier prompt now:
- Lists available chapters for the subject
- Lists available topics for the subject
- Instructs the agent to choose from these predefined lists
- Provides clear rules for selection

## Usage

### Accessing Taxonomy

```python
from vbagent.prompts.subjects.taxonomy import (
    get_chapters,
    get_topics,
    get_all_topics,
    SUBJECT_TAXONOMY
)

# Get all chapters for physics
chapters = get_chapters("physics")
# ['Kinematics', 'Laws of Motion', 'Work, Energy and Power', ...]

# Get topics for a specific chapter
topics = get_topics("physics", "Kinematics")
# ['motion in a straight line', 'motion in a plane', 'projectile motion', ...]

# Get all topics (flattened)
all_topics = get_all_topics("physics")
# ['motion in a straight line', 'motion in a plane', ..., 'logic gates']
```

### Classification Example

When classifying a question, the agent will now return:

```json
{
    "question_type": "mcq_sc",
    "difficulty": "medium",
    "chapter": "Kinematics",
    "topic": "projectile motion",
    "subtopic": "maximum height and range",
    "has_diagram": true,
    "diagram_type": "graph",
    "num_options": 4,
    "estimated_marks": 4,
    "key_concepts": ["velocity components", "time of flight", "range formula"],
    "requires_calculus": false,
    "confidence": 0.95
}
```

## Taxonomy Structure

### Physics Chapters (27)
1. Kinematics
2. Laws of Motion
3. Work, Energy and Power
4. System of Particles and Rotational Motion
5. Gravitation
6. Mechanical Properties of Solids
7. Mechanical Properties of Fluids
8. Thermal Properties of Matter
9. Thermodynamics
10. Kinetic Theory
11. Oscillations
12. Waves
13. Electric Charges and Fields
14. Electrostatic Potential and Capacitance
15. Current Electricity
16. Moving Charges and Magnetism
17. Magnetism and Matter
18. Electromagnetic Induction
19. Alternating Current
20. Electromagnetic Waves
21. Ray Optics and Optical Instruments
22. Wave Optics
23. Dual Nature of Radiation and Matter
24. Atoms
25. Nuclei
26. Semiconductor Electronics
27. Communication Systems

### Chemistry Chapters (28)
1. Some Basic Concepts of Chemistry
2. Structure of Atom
3. Classification of Elements and Periodicity
4. Chemical Bonding and Molecular Structure
5. States of Matter
6. Thermodynamics
7. Equilibrium
8. Redox Reactions
9. Hydrogen
10. s-Block Elements
11. p-Block Elements
12. Organic Chemistry - Basic Principles
13. Hydrocarbons
14. Environmental Chemistry
15. Solid State
16. Solutions
17. Electrochemistry
18. Chemical Kinetics
19. Surface Chemistry
20. d and f Block Elements
21. Coordination Compounds
22. Haloalkanes and Haloarenes
23. Alcohols, Phenols and Ethers
24. Aldehydes, Ketones and Carboxylic Acids
25. Amines
26. Biomolecules
27. Polymers
28. Chemistry in Everyday Life

### Mathematics Chapters (10)
1. Sets and Functions
2. Algebra
3. Coordinate Geometry
4. Calculus
5. Vectors and 3D Geometry
6. Linear Programming
7. Probability
8. Trigonometry
9. Matrices and Determinants
10. Statistics

### Biology Chapters (38)
1. The Living World
2. Biological Classification
3. Plant Kingdom
4. Animal Kingdom
5. Morphology of Flowering Plants
6. Anatomy of Flowering Plants
7. Structural Organisation in Animals
8. Cell: The Unit of Life
9. Biomolecules
10. Cell Cycle and Cell Division
... (and 28 more)

## Benefits

1. **Consistency**: All questions are classified using the same chapter/topic names
2. **Queryability**: Easy to filter questions by chapter or topic
3. **Organization**: Clear hierarchical structure for question banks
4. **Validation**: Agent must choose from predefined lists, reducing errors
5. **Scalability**: Easy to add new chapters/topics as needed

## Extending the Taxonomy

To add new chapters or topics:

1. Edit `vbagent/prompts/subjects/taxonomy.py`
2. Add to the appropriate `*_TAXONOMY` list:
```python
PHYSICS_TAXONOMY.append(
    ChapterTopics(
        chapter="New Chapter Name",
        topics=["topic1", "topic2", "topic3"]
    )
)
```
3. The changes will automatically be reflected in the classifier prompt

## Integration with Metadata System

The chapter and topic fields are now part of the metadata system:

```python
from vbagent.metadata.store import QuestionMetadata

metadata = QuestionMetadata(
    file_path="/path/to/question.tex",
    chapter="Kinematics",  # From taxonomy
    topic="projectile motion",  # From taxonomy
    subtopic="maximum height",
    difficulty="medium",
    question_type="mcq_sc",
    # ... other fields
)
```

## Testing

All classification tests have been updated to include the `chapter` field:

```bash
pytest tests/test_classification.py -v
```

All 5 tests passing ✓
