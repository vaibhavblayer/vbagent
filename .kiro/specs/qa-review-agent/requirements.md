# Requirements Document

## Introduction

The QA Review Agent is a feature for VBAgent that enables random spot-checking of processed physics questions and their variants. After the agentic pipeline processes questions (classification, scanning, variant generation, etc.), users can run a random check command that selects problems for AI-powered quality review. The AI analyzes the problem, its variants, and associated images, then suggests edits as diffs. Users can approve or reject suggestions interactively. Approved changes are applied to the files, while rejected suggestions are stored as versioned backups for potential future reference.

## Glossary

- **QA Review Agent**: AI agent that analyzes processed questions for quality issues and suggests corrections
- **Random Selector**: Component that randomly picks problems from the processed output for review
- **Diff**: A structured representation of changes between original and suggested content
- **Review Session**: An interactive session where users approve or reject AI suggestions
- **Version Store**: SQLite-based storage for rejected suggestions with version tracking
- **Suggestion**: A proposed edit from the QA Review Agent including the diff and reasoning
- **Review Status**: State of a suggestion (pending, approved, rejected)
- **Backup Version**: A stored rejected suggestion that can be retrieved later

## Requirements

### Requirement 1: Random Problem Selection

**User Story:** As a user, I want to randomly select processed problems for quality review, so that I can spot-check the pipeline output without manually choosing files.

#### Acceptance Criteria

1. WHEN a user runs the check command THEN the Random Selector SHALL pick a configurable number of problems from the processed output directory
2. WHEN selecting problems THEN the Random Selector SHALL load the problem's LaTeX, all variants, and associated image paths
3. WHEN a user specifies --count N THEN the Random Selector SHALL select exactly N problems for review
4. WHEN a user specifies --problem-id THEN the Random Selector SHALL select that specific problem instead of random selection
5. IF the output directory contains fewer problems than requested THEN the Random Selector SHALL select all available problems and report the count

### Requirement 2: AI Quality Review

**User Story:** As a user, I want an AI agent to analyze my processed questions and suggest improvements, so that I can catch errors and improve quality.

#### Acceptance Criteria

1. WHEN reviewing a problem THEN the QA Review Agent SHALL analyze the original LaTeX, all variants, and the source image
2. WHEN analyzing content THEN the QA Review Agent SHALL check for LaTeX syntax errors, physics correctness, solution accuracy, and variant consistency
3. WHEN issues are found THEN the QA Review Agent SHALL generate structured suggestions with reasoning and confidence scores
4. WHEN generating suggestions THEN the QA Review Agent SHALL produce unified diff format for each proposed change
5. WHEN no issues are found THEN the QA Review Agent SHALL report the problem as passing review
6. WHEN reviewing variants THEN the QA Review Agent SHALL verify that variant modifications are appropriate for their type (numerical changes only for numerical variants, etc.)

### Requirement 3: Diff Generation and Display

**User Story:** As a user, I want to see proposed changes as readable diffs, so that I can understand exactly what the AI wants to modify.

#### Acceptance Criteria

1. WHEN displaying a suggestion THEN the system SHALL show a unified diff with context lines
2. WHEN displaying a diff THEN the system SHALL use color coding (red for deletions, green for additions)
3. WHEN a suggestion spans multiple files THEN the system SHALL group diffs by file
4. WHEN displaying suggestions THEN the system SHALL show the AI's reasoning and confidence score
5. WHEN serializing diffs THEN the system SHALL produce valid unified diff format that can be applied with standard tools
6. WHEN parsing diffs THEN the system SHALL reconstruct the original unified diff format from stored data

### Requirement 4: Interactive Review Interface

**User Story:** As a user, I want an interactive CLI to approve or reject suggestions, so that I can control which changes are applied.

#### Acceptance Criteria

1. WHEN presenting a suggestion THEN the CLI SHALL display the diff and prompt for user action
2. WHEN a user approves a suggestion THEN the system SHALL apply the diff to the target file
3. WHEN a user rejects a suggestion THEN the system SHALL store the suggestion in the Version Store
4. WHEN a user requests to skip THEN the system SHALL move to the next suggestion without action
5. WHEN a user requests to edit THEN the system SHALL open the target file in the default editor
6. WHEN all suggestions are processed THEN the CLI SHALL display a summary of actions taken

### Requirement 5: Version Store for Rejected Suggestions

**User Story:** As a user, I want rejected suggestions stored with version tracking, so that I can review and potentially apply them later.

#### Acceptance Criteria

1. WHEN a suggestion is rejected THEN the Version Store SHALL save the suggestion with a unique version identifier
2. WHEN storing a rejected suggestion THEN the Version Store SHALL record the problem ID, file path, diff content, reasoning, timestamp, and version number
3. WHEN a user requests version history THEN the Version Store SHALL return all versions for a given problem or file
4. WHEN a user requests to apply a stored version THEN the system SHALL retrieve and apply the stored diff
5. WHEN storing versions THEN the Version Store SHALL increment version numbers per problem-file combination
6. WHEN serializing version data THEN the Version Store SHALL produce valid JSON that can be deserialized to reconstruct the original data

### Requirement 6: CLI Commands

**User Story:** As a user, I want CLI commands to access all QA review functions, so that I can integrate quality checks into my workflow.

#### Acceptance Criteria

1. WHEN a user runs `vbagent check` THEN the CLI SHALL start a random review session with default settings
2. WHEN a user runs `vbagent check --count N` THEN the CLI SHALL review N randomly selected problems
3. WHEN a user runs `vbagent check --problem-id ID` THEN the CLI SHALL review the specified problem
4. WHEN a user runs `vbagent check --dir PATH` THEN the CLI SHALL use the specified output directory
5. WHEN a user runs `vbagent check history` THEN the CLI SHALL display rejected suggestion history
6. WHEN a user runs `vbagent check apply VERSION_ID` THEN the CLI SHALL apply a previously rejected suggestion
7. WHEN a user runs `vbagent check stats` THEN the CLI SHALL display review statistics

### Requirement 7: Review Statistics and Reporting

**User Story:** As a user, I want to see statistics about my review sessions, so that I can track quality trends over time.

#### Acceptance Criteria

1. WHEN tracking reviews THEN the system SHALL record total problems reviewed, suggestions made, approved count, and rejected count
2. WHEN displaying stats THEN the system SHALL show approval rate, common issue types, and review history
3. WHEN a review session completes THEN the system SHALL update cumulative statistics
4. WHEN displaying stats THEN the system SHALL support filtering by date range

### Requirement 8: Error Handling and Recovery

**User Story:** As a user, I want the system to handle errors gracefully, so that I don't lose work during review sessions.

#### Acceptance Criteria

1. IF applying a diff fails THEN the system SHALL report the error and preserve the original file
2. IF the AI review fails THEN the system SHALL log the error and continue with the next problem
3. IF the Version Store is corrupted THEN the system SHALL attempt recovery and report status
4. WHEN a review session is interrupted THEN the system SHALL save progress and allow resumption
5. IF a file has been modified since the diff was generated THEN the system SHALL warn the user before applying

