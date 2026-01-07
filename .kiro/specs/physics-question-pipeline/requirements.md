# Requirements Document

## Introduction

VBAgent is a multi-agent CLI system for processing physics question images. The system uses OpenAI's Agent SDK to orchestrate specialized agents for classification, scanning, diagram generation, idea extraction, solution generation, variant creation, and format conversion. The pipeline supports reference file search for context-aware processing and handles both image and LaTeX inputs.

## Glossary

- **VBAgent**: The CLI tool and agentic system for physics question processing
- **Classifier Agent**: Agent that extracts metadata (type, difficulty, topic) from question images
- **Scanner Agent**: Agent that extracts LaTeX from images using type-specific prompts
- **TikZ Agent**: Agent specialized in generating TikZ diagram code
- **Idea Agent**: Agent that extracts core physics concepts and problem-solving ideas
- **Alternate Solution Agent**: Agent that generates alternative solution methods
- **Variant Agent**: Agent that creates problem variants (numerical, context, conceptual)
- **Multi-Context Variant Agent**: Agent that uses multiple problems as context to generate variants
- **Format Converter Agent**: Agent that converts between question formats (MCQ ↔ subjective ↔ integer)
- **Reference Store**: Collection of PDF, TeX, STY files for TikZ, PGF packages used as context
- **Question Type**: Classification of question (mcq_sc, mcq_mc, subjective, assertion_reason, passage, match)

## Requirements

### Requirement 1: Image Classification and Metadata Extraction

**User Story:** As a user, I want to classify physics question images to extract metadata, so that the system can select appropriate processing prompts.

#### Acceptance Criteria

1. WHEN a user provides an image path THEN the Classifier Agent SHALL analyze the image and return structured JSON metadata
2. WHEN classifying an image THEN the Classifier Agent SHALL extract question_type from the set (mcq_sc, mcq_mc, subjective, assertion_reason, passage, match)
3. WHEN classifying an image THEN the Classifier Agent SHALL extract difficulty level (easy, medium, hard), topic, subtopic, and has_diagram flag
4. WHEN classification completes THEN the system SHALL store metadata for use by subsequent pipeline stages
5. IF the image cannot be classified THEN the Classifier Agent SHALL return an error with confidence score below threshold

### Requirement 2: LaTeX Scanning and Extraction

**User Story:** As a user, I want to extract LaTeX code from physics question images, so that I can get machine-readable question content with solutions.

#### Acceptance Criteria

1. WHEN a user requests scanning THEN the Scanner Agent SHALL use the prompt corresponding to the classified question_type
2. WHEN scanning an image THEN the Scanner Agent SHALL extract the complete LaTeX including problem statement, options (if MCQ), and solution
3. WHEN the question contains a diagram THEN the system SHALL flag it for TikZ Agent processing
4. WHEN scanning completes THEN the Scanner Agent SHALL output valid LaTeX starting with \item and ending with \end{solution}
5. IF scanning fails THEN the Scanner Agent SHALL return partial results with error indicators

### Requirement 3: TikZ Diagram Generation

**User Story:** As a user, I want diagrams in questions converted to TikZ code, so that I have reproducible vector graphics in my LaTeX documents.

#### Acceptance Criteria

1. WHEN a question has_diagram is true THEN the TikZ Agent SHALL generate TikZ code for the diagram
2. WHEN generating TikZ THEN the TikZ Agent SHALL search reference files (STY, PDF) for relevant package syntax
3. WHEN generating TikZ THEN the TikZ Agent SHALL produce code compatible with standard TikZ/PGF packages
4. WHEN TikZ generation completes THEN the output SHALL be insertable within a tikzpicture environment
5. IF the diagram is too complex THEN the TikZ Agent SHALL provide a simplified approximation with notes

### Requirement 4: Idea and Concept Extraction

**User Story:** As a user, I want to extract the core physics ideas from problems, so that I can understand the conceptual foundation and use it for variant generation.

#### Acceptance Criteria

1. WHEN a user requests idea extraction THEN the Idea Agent SHALL analyze the problem and solution
2. WHEN extracting ideas THEN the Idea Agent SHALL identify primary physics concepts, formulas used, and problem-solving approach
3. WHEN extraction completes THEN the Idea Agent SHALL output structured data with concepts, techniques, and difficulty factors
4. WHEN ideas are extracted THEN the system SHALL make them available for variant generation agents

### Requirement 5: Alternate Solution Generation

**User Story:** As a user, I want to generate alternative solution methods for problems, so that I can provide multiple approaches for learning.

#### Acceptance Criteria

1. WHEN a user requests alternate solutions THEN the Alternate Solution Agent SHALL receive the problem, original solution, and extracted ideas
2. WHEN generating alternates THEN the Alternate Solution Agent SHALL produce at least one different valid approach
3. WHEN generating alternates THEN the Alternate Solution Agent SHALL maintain the same answer while using different methods
4. WHEN alternate generation completes THEN the output SHALL be valid LaTeX in solution environment format

### Requirement 6: Variant Generation - Single Problem

**User Story:** As a user, I want to create variants of physics problems, so that I can generate practice material with controlled modifications.

#### Acceptance Criteria

1. WHEN a user requests numerical variant THEN the Variant Agent SHALL modify only numerical values while preserving context and physics
2. WHEN a user requests context variant THEN the Variant Agent SHALL change the scenario while preserving numerical values and physics
3. WHEN a user requests conceptual variant THEN the Variant Agent SHALL modify the core physics concept being tested
4. WHEN a user requests conceptual-calculus variant THEN the Variant Agent SHALL introduce calculus-based modifications
5. WHEN generating any variant THEN the Variant Agent SHALL recalculate solutions and generate new distractors
6. WHEN variant generation completes THEN the output SHALL be valid LaTeX matching the original question format

### Requirement 7: Variant Generation - Multi-Problem Context

**User Story:** As a user, I want to generate variants using multiple problems as context, so that I can create hybrid problems combining concepts.

#### Acceptance Criteria

1. WHEN a user provides multiple problems as context THEN the Multi-Context Variant Agent SHALL analyze all provided problems
2. WHEN generating from multiple contexts THEN the Multi-Context Variant Agent SHALL combine elements from different source problems
3. WHEN generating from multiple contexts THEN the Multi-Context Variant Agent SHALL produce a coherent single problem
4. WHEN multi-context generation completes THEN the output SHALL include proper solution and be valid LaTeX

### Requirement 8: Format Conversion

**User Story:** As a user, I want to convert questions between formats, so that I can repurpose content for different assessment types.

#### Acceptance Criteria

1. WHEN a user requests subjective to MCQ conversion THEN the Format Converter Agent SHALL generate appropriate options and distractors
2. WHEN a user requests MCQ to integer type conversion THEN the Format Converter Agent SHALL reformulate to require numerical answer
3. WHEN a user requests MCQ to subjective conversion THEN the Format Converter Agent SHALL remove options and expand solution
4. WHEN converting formats THEN the Format Converter Agent SHALL preserve the core physics and difficulty level
5. WHEN format conversion completes THEN the output SHALL be valid LaTeX in the target format

### Requirement 9: Reference File Search

**User Story:** As a user, I want agents to search reference files for context, so that they can produce better TikZ code and follow package conventions.

#### Acceptance Criteria

1. WHEN an agent needs package syntax THEN the system SHALL search configured reference directories
2. WHEN searching references THEN the system SHALL support PDF, TeX, and STY file formats
3. WHEN relevant content is found THEN the system SHALL provide it as context to the requesting agent
4. WHEN no relevant content is found THEN the system SHALL proceed with default knowledge
5. WHERE reference directories are configured THEN the system SHALL index them for efficient search

### Requirement 10: CLI Interface

**User Story:** As a user, I want a command-line interface to access all pipeline functions, so that I can process questions efficiently.

#### Acceptance Criteria

1. WHEN a user runs a command THEN the CLI SHALL accept image input via -i/--image flag with path
2. WHEN a user runs a command THEN the CLI SHALL accept TeX input via -t/--tex flag with path
3. WHEN a user specifies -r/--range THEN the CLI SHALL process only the specified range of items
4. WHEN a user runs classify command THEN the CLI SHALL invoke the Classifier Agent and display results
5. WHEN a user runs scan command THEN the CLI SHALL run classification then scanning pipeline
6. WHEN a user runs variant command THEN the CLI SHALL accept variant type and generate accordingly
7. WHEN a user runs convert command THEN the CLI SHALL accept source and target formats
8. WHEN any command completes THEN the CLI SHALL support -o/--output flag for saving results

### Requirement 11: Prompt Organization

**User Story:** As a developer, I want prompts organized in separate files, so that I can maintain and update them independently.

#### Acceptance Criteria

1. WHEN organizing prompts THEN each agent SHALL have its own prompt file in the prompts directory
2. WHEN organizing prompts THEN variant prompts SHALL be in separate files per variant type
3. WHEN organizing prompts THEN system and user prompt templates SHALL be in a single file per agent
4. WHEN loading prompts THEN the system SHALL support dynamic prompt selection based on context
