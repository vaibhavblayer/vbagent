# Agents API Reference

Complete API documentation for VBAgent's multi-agent system.

## Quick Links

- **[Classification System](classification.md)** - 7-agent pipeline for metadata extraction
- **[Data Models](models.md)** - Pydantic models for all data structures
- **[CLI Functions](cli.md)** - Command-line interface modules
- **[Orchestrator](orchestrator.md)** - Tool wrappers and orchestration

---

## Agent Architecture

VBAgent uses a multi-agent architecture with specialized agents for different tasks:

### Classification Agents (v2)
Advanced 7-agent system for comprehensive metadata extraction:

1. **Image Classifier** - Classify questions from images
2. **Diagram Analyzer** - Hierarchical diagram categorization
3. **Difficulty Assessor** - Post-scan difficulty with detailed metadata
4. **LaTeX Classifier** - Batch processing of LaTeX files
5. **Idea Generator** - Generate problems from concepts
6. **Problem Combiner** - Combine multiple problems
7. **TikZ Checker** - Validate and fix TikZ code

### Core Processing Agents
Main workflow agents:

- **Scanner** - Extract LaTeX from images
- **TikZ Generator** - Generate TikZ diagrams
- **Variant Generator** - Create problem variants
- **Alternate Solutions** - Generate alternative solutions
- **Idea Extraction** - Extract physics concepts

### Quality Assurance Agents
Review and validation:

- **Reviewer** - Comprehensive QA review
- **Solution Checker** - Verify solution correctness
- **Grammar Checker** - Check grammar and style
- **Clarity Checker** - Assess clarity and readability

---

## Classification Agents

### Question Classifier

::: vbagent.agents.classification.question_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_question_image
        - classify_primary_image
        - create_question_classifier
        - to_primary_classification

### Diagram Classifier

::: vbagent.agents.classification.diagram_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_diagram_image
        - classify_diagram_description
        - create_diagram_classifier

### Difficulty Assessor

::: vbagent.agents.classification.difficulty_assessor
    options:
      show_root_heading: true
      show_source: false
      members:
        - assess_difficulty
        - create_difficulty_assessor_agent

### LaTeX Classifier

::: vbagent.agents.classification.latex_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_latex
        - create_latex_classifier_agent

### Idea Generator

::: vbagent.agents.content_generation.idea_generator
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_from_idea
        - create_idea_generator_agent

### Problem Combiner

::: vbagent.agents.content_generation.problem_combiner
    options:
      show_root_heading: true
      show_source: false
      members:
        - combine_problems
        - create_problem_combiner_agent

### TikZ Checker

::: vbagent.agents.diagram.tikz_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - validate_tikz
        - create_tikz_checker_agent

## Core Agents

### Base Agent Functions

::: vbagent.agents.base
    options:
      show_root_heading: true
      show_source: false
      members:
        - create_agent
        - run_agent_sync
        - create_image_message

### Classifier Compatibility Facade

::: vbagent.agents.classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify
        - create_classifier_agent

### Scanner Agent

::: vbagent.agents.content_generation.scanner
    options:
      show_root_heading: true
      show_source: false
      members:
        - scan
        - scan_with_type
        - create_scanner_agent

### TikZ Agent

::: vbagent.agents.diagram.tikz
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_tikz
        - create_tikz_agent
        - get_tikz_context_for_classification

### TikZ Router

::: vbagent.agents.diagram.tikz_router
    options:
      show_root_heading: true
      show_source: false

### Free Body Diagram Agent

::: vbagent.agents.diagram.physics.fbd
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_fbd
        - create_fbd_agent

### Variant Agent

::: vbagent.agents.variants.variant
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_variant
        - generate_numerical_variant
        - generate_context_variant

### Multi-Variant Agent

::: vbagent.agents.variants.multi_context_variant
    options:
      show_root_heading: true
      show_source: false

### Alternate Solution Agent

::: vbagent.agents.content_generation.alternate
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_alternate

### Idea Extraction Agent

::: vbagent.agents.content_generation.idea
    options:
      show_root_heading: true
      show_source: false
      members:
        - extract_ideas

### Converter Agent

::: vbagent.agents.content_generation.converter
    options:
      show_root_heading: true
      show_source: false
      members:
        - convert_format

### Compile Fixer Agent

::: vbagent.agents.quality.latex_fixer
    options:
      show_root_heading: true
      show_source: false

## QA Agents

### Reviewer Agent

::: vbagent.agents.quality.reviewer
    options:
      show_root_heading: true
      show_source: false
      members:
        - review_problem_sync

### Solution Checker

::: vbagent.agents.quality.solution_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_solution

### Grammar Checker

::: vbagent.agents.quality.grammar_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_grammar

### Clarity Checker

::: vbagent.agents.quality.clarity_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_clarity

## Selector Agent

::: vbagent.agents.selection.selector
    options:
      show_root_heading: true
      show_source: false
