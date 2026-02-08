# Curriculum-Based Classification Guide

## Overview

The classification agent now uses predefined curriculum structures for all four subjects (Physics, Chemistry, Mathematics, and Biology). This ensures consistent topic and chapter classification across all questions.

## Key Features

1. **Predefined Curriculum**: Each subject has a structured list of chapters and topics
2. **Automatic Chapter Detection**: The chapter is automatically determined from the selected topic
3. **Constrained Classification**: The agent must choose topics from the predefined list only
4. **Subject-Specific**: Each subject has its own curriculum tailored to standard syllabi

## Curriculum Structure

The curriculum is defined in `vbagent/prompts/subjects/taxonomy.py` and provides comprehensive chapter-topic mappings for all subjects.

### Physics (27 Chapters)
Includes chapters like: Kinematics, Laws of Motion, Work Energy and Power, System of Particles and Rotational Motion, Gravitation, Mechanical Properties of Solids, Mechanical Properties of Fluids, Thermal Properties of Matter, Thermodynamics, Kinetic Theory, Oscillations, Waves, Electric Charges and Fields, Electrostatic Potential and Capacitance, Current Electricity, Moving Charges and Magnetism, Magnetism and Matter, Electromagnetic Induction, Alternating Current, Electromagnetic Waves, Ray Optics and Optical Instruments, Wave Optics, Dual Nature of Radiation and Matter, Atoms, Nuclei, Semiconductor Electronics, Communication Systems

### Chemistry (28 Chapters)
Includes chapters like: Some Basic Concepts of Chemistry, Structure of Atom, Classification of Elements and Periodicity, Chemical Bonding and Molecular Structure, States of Matter, Thermodynamics, Equilibrium, Redox Reactions, Hydrogen, s-Block Elements, p-Block Elements, Organic Chemistry - Basic Principles, Hydrocarbons, Environmental Chemistry, Solid State, Solutions, Electrochemistry, Chemical Kinetics, Surface Chemistry, d and f Block Elements, Coordination Compounds, Haloalkanes and Haloarenes, Alcohols Phenols and Ethers, Aldehydes Ketones and Carboxylic Acids, Amines, Biomolecules, Polymers, Chemistry in Everyday Life

### Mathematics (10 Chapters)
Includes chapters like: Sets and Functions, Algebra, Coordinate Geometry, Calculus, Vectors and 3D Geometry, Linear Programming, Probability, Trigonometry, Matrices and Determinants, Statistics

### Biology (38 Chapters)
Includes chapters like: The Living World, Biological Classification, Plant Kingdom, Animal Kingdom, Morphology of Flowering Plants, Anatomy of Flowering Plants, Structural Organisation in Animals, Cell: The Unit of Life, Biomolecules, Cell Cycle and Cell Division, Transport in Plants, Mineral Nutrition, Photosynthesis in Higher Plants, Respiration in Plants, Plant Growth and Development, Digestion and Absorption, Breathing and Exchange of Gases, Body Fluids and Circulation, Excretory Products and their Elimination, Locomotion and Movement, Neural Control and Coordination, Chemical Coordination and Integration, Reproduction in Organisms, Sexual Reproduction in Flowering Plants, Human Reproduction, Reproductive Health, Principles of Inheritance and Variation, Molecular Basis of Inheritance, Evolution, Human Health and Disease, Strategies for Enhancement in Food Production, Microbes in Human Welfare, Biotechnology: Principles and Processes, Biotechnology and its Applications, Organisms and Populations, Ecosystem, Biodiversity and Conservation, Environmental Issues

## Usage

### Classification with Curriculum

```python
from vbagent.agents.classifier import classify

# Classify a question image
result = classify("question_image.png", subject="physics")

print(f"Topic: {result.topic}")           # e.g., "kinematics"
print(f"Chapter: {result.chapter}")       # e.g., "mechanics" (auto-determined)
print(f"Subtopic: {result.subtopic}")     # e.g., "position-time graphs"
```

### Accessing Curriculum Programmatically

```python
from vbagent.prompts.subjects.taxonomy import (
    get_chapters,
    get_all_topics,
    get_chapter_for_topic
)

# Get all chapters for a subject
chapters = get_chapters("physics")
print(f"Physics has {len(chapters)} chapters")

# Get all topics (flattened list)
topics = get_all_topics("chemistry")
print(f"Total chemistry topics: {len(topics)}")

# Find chapter for a specific topic
chapter = get_chapter_for_topic("mathematics", "differentiation")
print(f"Differentiation belongs to: {chapter}")  # "Calculus"
```

### Metadata Storage

The classification result includes both topic and chapter:

```python
from vbagent.metadata.store import QuestionMetadata, MetadataStore

# Create metadata from classification result
metadata = QuestionMetadata(
    file_path="question.tex",
    chapter=result.chapter,           # Auto-determined from topic
    topic=result.topic,                # From predefined curriculum
    subtopic=result.subtopic,
    difficulty=result.difficulty,
    question_type=result.question_type,
    # ... other fields
)

# Store in database
store = MetadataStore(Path("metadata.db"))
store.upsert(metadata)
```

## Benefits

1. **Consistency**: All questions are classified using the same topic taxonomy
2. **Accuracy**: Agent must choose from predefined list, reducing errors
3. **Searchability**: Standardized topics make querying easier
4. **Organization**: Automatic chapter assignment helps with content organization
5. **Curriculum Alignment**: Topics align with standard educational syllabi

## Customization

To modify the curriculum for your needs:

1. Edit `vbagent/prompts/subjects/taxonomy.py`
2. Update the chapter and topic lists for each subject
3. The changes will automatically be reflected in the classifier prompt

Example:

```python
# Add topics to an existing chapter in Physics
PHYSICS_TAXONOMY.append(
    ChapterTopics(
        chapter="Advanced Mechanics",
        topics=["Lagrangian mechanics", "Hamiltonian mechanics", "chaos theory"]
    )
)
```

## CLI Usage

```bash
# Classify a question image
vbagent classify question.png --subject physics

# The output will include both topic and chapter
# Topic: kinematics
# Chapter: mechanics
# Subtopic: position-time graphs and relative motion
```

## Integration with DPP Builder

The DPP builder can now filter by both chapter and topic:

```bash
# Create DPP with questions from specific chapter
vbagent dpp create -n 10 --chapter mechanics

# Create DPP with questions from specific topic
vbagent dpp create -n 10 --topic kinematics

# Combine filters
vbagent dpp create -n 15 --chapter mechanics --difficulty easy
```

## Notes

- The classifier agent is instructed to choose topics from the predefined list ONLY
- If a topic doesn't fit any predefined category, the agent should choose the closest match
- The chapter field is automatically populated based on the topic selection
- Case-insensitive matching is used when determining chapters from topics
