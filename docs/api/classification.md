# Classification API Reference

Auto-generated API documentation for VBAgent classification agents (v2 multi-agent system).

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
