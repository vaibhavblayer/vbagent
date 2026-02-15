# Classification API Reference

The v2 multi-agent classification system provides comprehensive metadata extraction through 7 specialized agents.

## System Overview

The classification pipeline supports multiple input modalities:

- **Image** → Agent 1 (Image Classifier)
- **LaTeX** → Agent 4 (LaTeX Classifier)
- **Idea/Concept** → Agent 5 (Idea Generator)
- **Multiple Problems** → Agent 6 (Problem Combiner)

Additional agents provide:
- **Agent 2** - Diagram analysis (hierarchical categorization)
- **Agent 3** - Difficulty assessment (post-scan, detailed metadata)
- **Agent 7** - TikZ validation (automatic fixing)

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
    classify_from_image,
    analyze_diagram,
    assess_difficulty,
    validate_tikz,
)

# Agent 1: Classify from image
classification = classify_from_image("question.png")

# Agent 2: Analyze diagram (if has_diagram)
if classification.has_diagram:
    diagram = analyze_diagram("question.png", classification)

# Agent 3: Assess difficulty (after scanning)
difficulty = assess_difficulty(latex_content, classification, diagram)

# Agent 7: Validate TikZ
validation = validate_tikz(tikz_code, auto_fix=True)
```

---

## Auto-Generated API Documentation

## Pipeline Orchestrator

::: vbagent.agents.classification.pipeline
    options:
      show_root_heading: true
      show_source: false

## Agent 1: Image Classifier

::: vbagent.agents.classification.image_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_image
        - create_image_classifier_agent

## Agent 2: Diagram Analyzer

::: vbagent.agents.classification.diagram_analyzer
    options:
      show_root_heading: true
      show_source: false
      members:
        - analyze_diagram
        - analyze_diagram_from_description
        - create_diagram_analyzer_agent

## Agent 3: Difficulty Assessor

::: vbagent.agents.classification.difficulty_assessor
    options:
      show_root_heading: true
      show_source: false
      members:
        - assess_difficulty
        - create_difficulty_assessor_agent

## Agent 4: LaTeX Classifier

::: vbagent.agents.classification.latex_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_latex
        - create_latex_classifier_agent

## Agent 5: Idea Generator

::: vbagent.agents.classification.idea_generator
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_from_idea
        - create_idea_generator_agent

## Agent 6: Problem Combiner

::: vbagent.agents.classification.problem_combiner
    options:
      show_root_heading: true
      show_source: false
      members:
        - combine_problems
        - create_problem_combiner_agent

## Agent 7: TikZ Checker

::: vbagent.agents.classification.tikz_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_tikz
        - create_tikz_checker_agent
