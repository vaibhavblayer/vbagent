# Classification API Reference

The classification system provides one canonical image classifier plus
specialized LaTeX, diagram, taxonomy, and difficulty classifiers.

## System Overview

The classification pipeline supports multiple input modalities:

- **Image** → Question Classifier
- **LaTeX** → LaTeX Classifier
- **Diagram descriptions** → Diagram Classifier

Problem generation and combination live under `agents.content_generation`;
they are not classification agents.

## Key Features

- ✅ Multiple input modalities
- ✅ Hierarchical diagram classification
- ✅ Detailed difficulty assessment (reasoning, time, prerequisites, mistakes)
- ✅ Automatic TikZ validation with error fixing
- ✅ Specialized TikZ agent routing
- ✅ Bloom's taxonomy cognitive levels
- ✅ Cross-subject problem combination

## Usage Example

```python
from vbagent.agents.classification import (
    classify_primary_image,
    classify_diagram_image,
    assess_difficulty,
    validate_tikz,
)

# Classify from image
classification = classify_primary_image("question.png")

# Classify the diagram separately when needed
if classification.has_diagram:
    diagram = classify_diagram_image("question.png", classification)

# Assess difficulty after scanning
difficulty = assess_difficulty(latex_content, classification, diagram)

# Validate TikZ
validation = validate_tikz(tikz_code, auto_fix=True)
```

---

## Auto-Generated API Documentation

## Question Classifier

::: vbagent.agents.classification.question_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_question_image
        - classify_primary_image
        - create_question_classifier

## Diagram Classifier

::: vbagent.agents.classification.diagram_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_diagram_image
        - classify_diagram_description
        - create_diagram_classifier

## Difficulty Assessor

::: vbagent.agents.classification.difficulty_assessor
    options:
      show_root_heading: true
      show_source: false
      members:
        - assess_difficulty
        - create_difficulty_assessor_agent

## LaTeX Classifier

::: vbagent.agents.classification.latex_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_latex
        - create_latex_classifier_agent

## Idea Generator

::: vbagent.agents.content_generation.idea_generator
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_from_idea
        - create_idea_generator_agent

## Problem Combiner

::: vbagent.agents.content_generation.problem_combiner
    options:
      show_root_heading: true
      show_source: false
      members:
        - combine_problems
        - create_problem_combiner_agent

## TikZ Checker

::: vbagent.agents.diagram.tikz_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_tikz
        - create_tikz_checker_agent
