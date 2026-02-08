# Metadata System Implementation

## Overview

The metadata system provides SQLite-based storage and querying for question bank metadata. It enables indexing LaTeX question files with searchable metadata including chapter, topic, difficulty, question type, tags, and usage statistics.

## Components Implemented

### 1. Core Classes (`vbagent/metadata/store.py`)

#### QuestionMetadata
- Dataclass representing metadata for a single question
- Fields: file_path, chapter, topic, difficulty, question_type, tags, usage_count, last_used, created_at, updated_at
- Methods: `to_dict()`, `from_dict()` for serialization

#### MetadataExtractor
- Extracts metadata from LaTeX files
- Reads metadata from comments at the top of files:
  ```latex
  % chapter: Mechanics
  % topic: Kinematics
  % difficulty: medium
  % type: mcq_sc
  % tags: motion, acceleration, graphs
  ```
- Infers metadata from content when not explicitly specified:
  - Question type detection (mcq_sc, mcq_mc, subjective, assertion_reason, match, passage)
  - Difficulty inference based on content complexity

#### MetadataStore
- SQLite-based storage with indexed queries
- Database schema with indexes on topic, difficulty, chapter, question_type
- Methods:
  - `index_directory()`: Scan and index all .tex files in a directory
  - `upsert()`: Insert or update question metadata
  - `query()`: Query with filters (topic, difficulty, chapter, question_type, tags, limit)
  - `get_by_path()`: Get metadata for a specific file
  - `update_usage()`: Increment usage count and update last_used timestamp
  - `get_statistics()`: Get aggregate statistics (counts by chapter, difficulty, topic, type)

### 2. CLI Commands (`vbagent/cli/metadata.py`)

#### `vbagent metadata index <directory>`
- Index all LaTeX files in a directory
- Options:
  - `--db`: Path to metadata database (default: `.vbagent/metadata.db`)
  - `--recursive/--no-recursive`: Scan subdirectories (default: recursive)
- Example: `vbagent metadata index ./questions`

#### `vbagent metadata query`
- Query questions by metadata filters
- Options:
  - `--db`: Path to metadata database
  - `--topic`: Filter by topic
  - `--difficulty`: Filter by difficulty (easy, medium, hard)
  - `--chapter`: Filter by chapter
  - `--type`: Filter by question type
  - `--tags`: Filter by tags (comma-separated, must have all)
  - `--limit`: Maximum number of results
  - `--format`: Output format (table, json, paths)
- Examples:
  - `vbagent metadata query --topic Kinematics`
  - `vbagent metadata query --difficulty medium --chapter Mechanics`
  - `vbagent metadata query --tags "motion,graphs" --format json`

#### `vbagent metadata stats`
- Show aggregate statistics about the question bank
- Options:
  - `--db`: Path to metadata database
- Displays:
  - Total question count
  - Counts by chapter, difficulty, topic, question type
  - Most used questions (top 10)
  - Unused questions (sample)
- Example: `vbagent metadata stats`

### 3. Integration

- Added to main CLI (`vbagent/cli/main.py`) as lazy-loaded command
- Registered in `LAZY_SUBCOMMANDS` dictionary
- Added to help text in main CLI

## Testing

### Unit Tests (`tests/test_metadata.py`)

Comprehensive test suite with 19 tests covering:

1. **QuestionMetadata Tests**
   - Dictionary serialization/deserialization
   - Field validation

2. **MetadataExtractor Tests**
   - Metadata extraction from comments
   - Question type inference (mcq_sc, mcq_mc, subjective)
   - Difficulty inference

3. **MetadataStore Tests**
   - Insert and retrieve operations
   - Update existing records (upsert)
   - Query by single filter (topic, difficulty)
   - Query by multiple filters
   - Query by tags
   - Query with limit
   - Usage statistics update
   - Aggregate statistics
   - Directory indexing (recursive and non-recursive)

All tests pass successfully.

## Usage Examples

### Indexing a Question Bank

```bash
# Index all questions in a directory
vbagent metadata index ./questions

# Index with custom database location
vbagent metadata index ./questions --db custom.db

# Index only top-level directory (no subdirectories)
vbagent metadata index ./questions --no-recursive
```

### Querying Questions

```bash
# Find all kinematics questions
vbagent metadata query --topic Kinematics

# Find medium difficulty mechanics questions
vbagent metadata query --difficulty medium --chapter Mechanics

# Find questions with specific tags
vbagent metadata query --tags "motion,graphs"

# Get results as JSON
vbagent metadata query --topic Dynamics --format json

# Get just file paths
vbagent metadata query --difficulty easy --format paths

# Limit results
vbagent metadata query --chapter Mechanics --limit 10
```

### Viewing Statistics

```bash
# Show question bank statistics
vbagent metadata stats

# Statistics for custom database
vbagent metadata stats --db custom.db
```

## Database Schema

```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    chapter TEXT,
    topic TEXT,
    difficulty TEXT,
    question_type TEXT,
    tags TEXT,  -- JSON array
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_topic ON questions(topic);
CREATE INDEX idx_difficulty ON questions(difficulty);
CREATE INDEX idx_chapter ON questions(chapter);
CREATE INDEX idx_question_type ON questions(question_type);
```

## Metadata Format

Questions can include metadata in comments at the top of the file:

```latex
% chapter: Mechanics
% topic: Kinematics
% difficulty: medium
% type: mcq_sc
% tags: motion, velocity, acceleration

\item A car moves with constant acceleration...
```

### Supported Fields

- **chapter**: Chapter name (e.g., "Mechanics", "Thermodynamics")
- **topic**: Topic within chapter (e.g., "Kinematics", "Dynamics")
- **difficulty**: One of: easy, medium, hard
- **type**: Question type (mcq_sc, mcq_mc, subjective, assertion_reason, match, passage)
- **tags**: Comma-separated list of tags

### Automatic Inference

If metadata is not explicitly provided, the system will attempt to infer:

1. **Question Type**:
   - Detects MCQ from `\begin{tasks}` or `\task` commands
   - Distinguishes single/multiple correct from keywords
   - Identifies assertion-reason, match, passage patterns
   - Defaults to subjective

2. **Difficulty**:
   - Analyzes content complexity (math expressions, equations, diagrams)
   - Assigns easy/medium/hard based on complexity score

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **3.1**: Index directory of LaTeX files with metadata extraction ✓
- **3.2**: Store chapter, topic, difficulty, question type, and tags ✓
- **3.3**: Persist metadata to SQLite storage ✓
- **3.4**: Query with filtering by any metadata field ✓
- **3.5**: Update usage statistics (usage_count, last_used) ✓
- **3.6**: Display statistics grouped by chapter, difficulty, topic ✓

## Future Enhancements

Potential improvements for future iterations:

1. **Bulk Operations**: Batch update/delete operations
2. **Search**: Full-text search in question content
3. **Export**: Export metadata to CSV/JSON for analysis
4. **Validation**: Validate metadata consistency across question bank
5. **Migration**: Database migration tools for schema updates
6. **Caching**: Cache frequently accessed queries
7. **Relationships**: Track question dependencies and variants
8. **History**: Track metadata change history
