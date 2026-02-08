# Curriculum-Based Classification Guide

## Overview

The classification agent now uses predefined curriculum structures for all four subjects (Physics, Chemistry, Mathematics, and Biology). This ensures consistent topic and chapter classification across all questions.

## Key Features

1. **Predefined Curriculum**: Each subject has a structured list of chapters and topics
2. **Automatic Chapter Detection**: The chapter is automatically determined from the selected topic
3. **Constrained Classification**: The agent must choose topics from the predefined list only
4. **Subject-Specific**: Each subject has its own curriculum tailored to standard syllabi

## Curriculum Structure

### Physics (10 Chapters, 27 Topics)
- **Mechanics**: kinematics, laws of motion, work energy and power, system of particles and rotational motion, gravitation
- **Properties of Bulk Matter**: mechanical properties of solids, mechanical properties of fluids, thermal properties of matter
- **Thermodynamics**: thermodynamics, kinetic theory
- **Oscillations and Waves**: oscillations, waves
- **Electrostatics**: electric charges and fields, electrostatic potential and capacitance
- **Current Electricity**: current electricity, moving charges and magnetism, magnetism and matter
- **Electromagnetic Induction and AC**: electromagnetic induction, alternating current, electromagnetic waves
- **Optics**: ray optics and optical instruments, wave optics
- **Dual Nature of Radiation and Matter**: dual nature of radiation and matter, atoms, nuclei
- **Electronic Devices**: semiconductor electronics, communication systems

### Chemistry (14 Chapters, 54 Topics)
- **Some Basic Concepts of Chemistry**: mole concept, stoichiometry, atomic mass and molecular mass, percentage composition
- **Structure of Atom**: atomic models, quantum numbers, electronic configuration, periodic trends
- **Classification of Elements and Periodicity**: periodic table, periodic properties, ionization energy, electronegativity
- **Chemical Bonding and Molecular Structure**: ionic bonding, covalent bonding, hybridization, molecular orbital theory, VSEPR theory
- **States of Matter**: gaseous state, liquid state, solid state
- **Thermodynamics**: first law of thermodynamics, enthalpy, entropy, gibbs free energy, hess law
- **Equilibrium**: chemical equilibrium, law of mass action, le chatelier principle, equilibrium constant
- **Redox Reactions**: oxidation and reduction, balancing redox equations, oxidation number
- **Hydrogen**: hydrogen, water, hydrogen peroxide
- **s-Block Elements**: alkali metals, alkaline earth metals
- **p-Block Elements**: group 13-18 elements
- **Organic Chemistry - Basic Principles**: nomenclature, isomerism, reaction mechanisms, inductive effect, resonance
- **Hydrocarbons**: alkanes, alkenes, alkynes, aromatic hydrocarbons
- **Environmental Chemistry**: pollution, green chemistry

### Mathematics (9 Chapters, 47 Topics)
- **Sets, Relations and Functions**: sets, relations, functions, inverse functions, composite functions
- **Algebra**: complex numbers, quadratic equations, linear inequalities, permutations and combinations, binomial theorem, sequences and series, mathematical induction
- **Coordinate Geometry**: straight lines, circles, parabola, ellipse, hyperbola, conic sections
- **Calculus**: limits and continuity, differentiation, applications of derivatives, indefinite integration, definite integration, applications of integrals, differential equations
- **Vectors and Three-Dimensional Geometry**: vectors, scalar and vector products, three dimensional geometry, direction cosines
- **Linear Algebra**: matrices, determinants, system of linear equations
- **Probability and Statistics**: probability, conditional probability, bayes theorem, random variables, probability distributions, statistics, mean and variance
- **Trigonometry**: trigonometric functions, trigonometric equations, inverse trigonometric functions, properties of triangles
- **Mathematical Reasoning**: statements, logical operations, implications, validating statements

### Biology (12 Chapters, 52 Topics)
- **The Living World**: diversity in living world, biological classification, taxonomy
- **Plant Kingdom**: algae, bryophytes, pteridophytes, gymnosperms, angiosperms
- **Animal Kingdom**: animal classification, phyla, vertebrates, invertebrates
- **Structural Organization in Animals and Plants**: morphology of flowering plants, anatomy of flowering plants, animal tissues, organ systems
- **Cell: The Unit of Life**: cell structure, cell organelles, cell membrane, cell wall, cell division
- **Biomolecules**: carbohydrates, proteins, lipids, nucleic acids, enzymes
- **Plant Physiology**: transport in plants, mineral nutrition, photosynthesis, respiration, plant growth and development
- **Human Physiology**: digestion and absorption, breathing and exchange of gases, body fluids and circulation, excretory products and elimination, locomotion and movement, neural control and coordination, chemical coordination and integration
- **Reproduction**: reproduction in organisms, sexual reproduction in flowering plants, human reproduction, reproductive health
- **Genetics and Evolution**: principles of inheritance and variation, molecular basis of inheritance, evolution, human health and disease
- **Biotechnology**: biotechnology principles and processes, biotechnology and its applications
- **Ecology and Environment**: organisms and populations, ecosystem, biodiversity and conservation, environmental issues

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
from vbagent.prompts.subjects.curriculum import (
    get_chapters,
    get_all_topics,
    get_chapter_for_topic
)

# Get all chapters for a subject
chapters = get_chapters("physics")
for chapter in chapters:
    print(f"{chapter.display_name}: {len(chapter.topics)} topics")

# Get all topics (flattened list)
topics = get_all_topics("chemistry")
print(f"Total chemistry topics: {len(topics)}")

# Find chapter for a specific topic
chapter = get_chapter_for_topic("mathematics", "differentiation")
print(f"Differentiation belongs to: {chapter}")  # "calculus"
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

1. Edit `vbagent/prompts/subjects/curriculum.py`
2. Update the chapter and topic lists for each subject
3. The changes will automatically be reflected in the classifier prompt

Example:

```python
# Add a new chapter to Physics
PHYSICS_CHAPTERS.append(
    Chapter(
        name="quantum_mechanics",
        display_name="Quantum Mechanics",
        topics=["wave-particle duality", "uncertainty principle", "quantum tunneling"]
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
