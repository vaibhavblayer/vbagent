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

## Classification Agents (v2 Multi-Agent System)

### Agent 1: Image Classifier

::: vbagent.agents.classification.image_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_image
        - create_image_classifier_agent

### Agent 2: Diagram Analyzer

::: vbagent.agents.classification.diagram_analyzer
    options:
      show_root_heading: true
      show_source: false
      members:
        - analyze_diagram
        - analyze_diagram_from_description
        - create_diagram_analyzer_agent

### Agent 3: Difficulty Assessor

::: vbagent.agents.classification.difficulty_assessor
    options:
      show_root_heading: true
      show_source: false
      members:
        - assess_difficulty
        - create_difficulty_assessor_agent

### Agent 4: LaTeX Classifier

::: vbagent.agents.classification.latex_classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify_from_latex
        - create_latex_classifier_agent

### Agent 5: Idea Generator

::: vbagent.agents.classification.idea_generator
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_from_idea
        - create_idea_generator_agent

### Agent 6: Problem Combiner

::: vbagent.agents.classification.problem_combiner
    options:
      show_root_heading: true
      show_source: false
      members:
        - combine_problems
        - create_problem_combiner_agent

### Agent 7: TikZ Checker

::: vbagent.agents.classification.tikz_checker
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

### Classifier Agent (v1)

::: vbagent.agents.classifier
    options:
      show_root_heading: true
      show_source: false
      members:
        - classify
        - create_classifier_agent

### Scanner Agent

::: vbagent.agents.scanner
    options:
      show_root_heading: true
      show_source: false
      members:
        - scan
        - scan_with_type
        - create_scanner_agent

### TikZ Agent

::: vbagent.agents.tikz
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_tikz
        - create_tikz_agent
        - get_tikz_context_for_classification

### TikZ Router

::: vbagent.agents.tikz_router
    options:
      show_root_heading: true
      show_source: false

### Free Body Diagram Agent

::: vbagent.agents.fbd
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_fbd
        - create_fbd_agent

### Variant Agent

::: vbagent.agents.variant
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_variant
        - generate_numerical_variant
        - generate_context_variant

### Multi-Variant Agent

::: vbagent.agents.multi_variant
    options:
      show_root_heading: true
      show_source: false

### Alternate Solution Agent

::: vbagent.agents.alternate
    options:
      show_root_heading: true
      show_source: false
      members:
        - generate_alternate
        - create_alternate_agent

### Idea Extraction Agent

::: vbagent.agents.idea
    options:
      show_root_heading: true
      show_source: false
      members:
        - extract_ideas
        - create_idea_agent

### Converter Agent

::: vbagent.agents.converter
    options:
      show_root_heading: true
      show_source: false
      members:
        - convert_format
        - create_converter_agent

### Compile Fixer Agent

::: vbagent.agents.compile_fixer
    options:
      show_root_heading: true
      show_source: false

## QA Agents

### Reviewer Agent

::: vbagent.agents.reviewer
    options:
      show_root_heading: true
      show_source: false
      members:
        - review_problem_sync
        - create_reviewer_agent

### Solution Checker

::: vbagent.agents.solution_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_solution
        - create_solution_checker_agent

### Grammar Checker

::: vbagent.agents.grammar_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_grammar
        - create_grammar_checker_agent

### Clarity Checker

::: vbagent.agents.clarity_checker
    options:
      show_root_heading: true
      show_source: false
      members:
        - check_clarity
        - create_clarity_checker_agent

## Selector Agent

::: vbagent.agents.selector
    options:
      show_root_heading: true
      show_source: false
