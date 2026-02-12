# Metadata Fields Guide

## Overview

The metadata system now supports extended fields for richer question classification and filtering. These fields can be specified in LaTeX files using comment syntax or programmatically when creating `QuestionMetadata` objects.

## Supported Fields

### Basic Fields
- **file_path** (str, required): Path to the question file
- **chapter** (str, optional): Chapter name (e.g., "Mechanics")
- **topic** (str, optional): Main topic (e.g., "kinematics")
- **subtopic** (str, optional): Specific subtopic (e.g., "position-time graphs and relative motion")
- **difficulty** (str, optional): Question difficulty - "easy", "medium", or "hard"
- **question_type** (str, optional): Type of question - "mcq_sc", "mcq_mc", "subjective", "passage", "assertion_reason", "match"
- **tags** (list[str], optional): List of tags for categorization

### Extended Fields
- **has_diagram** (bool, optional): Whether the question includes a diagram
- **diagram_type** (str, optional): Type of diagram (e.g., "graph", "circuit", "free_body", "ray_diagram")
- **num_options** (int, optional): Number of options for MCQ questions
- **key_concepts** (list[str], optional): List of key concepts tested
- **requires_calculus** (bool, optional): Whether the question requires calculus knowledge
- **confidence** (float, optional): Confidence score (0.0 to 1.0) for auto-generated metadata

### Usage Tracking Fields
- **usage_count** (int): Number of times the question has been used in DPPs
- **last_used** (datetime, optional): Timestamp of last usage
- **created_at** (datetime): When the metadata was first created
- **updated_at** (datetime): When the metadata was last updated

## LaTeX Comment Syntax

Add metadata as comments at the top of your LaTeX files:

```latex
% chapter: Mechanics
% topic: kinematics
% subtopic: position-time graphs and relative motion
% difficulty: easy
% type: passage
% tags: graphs, motion, relative velocity
% has_diagram: true
% diagram_type: graph
% num_options: 4
% key_concepts: position vs time graphs, velocity as slope, overtaking
% requires_calculus: false
% confidence: 0.9

\item A particle moves with velocity...
```

## Programmatic Usage

### Creating Metadata

```python
from vbagent.metadata.store import QuestionMetadata

metadata = QuestionMetadata(
    file_path="/path/to/question.tex",
    chapter="Mechanics",
    topic="kinematics",
    subtopic="position-time graphs and relative motion",
    difficulty="easy",
    question_type="passage",
    tags=["graphs", "motion"],
    has_diagram=True,
    diagram_type="graph",
    num_options=4,
    key_concepts=[
        "position vs time graphs",
        "velocity as slope of x-t graph",
        "overtaking/relative position"
    ],
    requires_calculus=False,
    confidence=0.9
)
```

### Storing Metadata

```python
from pathlib import Path
from vbagent.metadata.store import MetadataStore

# Initialize store
store = MetadataStore(Path("metadata.db"))

# Insert or update
store.upsert(metadata)

# Close when done
store.close()
```

### Querying with New Fields

```python
# Query by subtopic
results = store.query(subtopic="position-time graphs and relative motion")

# Query questions with diagrams
results = store.query(has_diagram=True)

# Query non-calculus questions
results = store.query(requires_calculus=False)

# Combine multiple filters
results = store.query(
    topic="kinematics",
    difficulty="easy",
    has_diagram=True,
    requires_calculus=False,
    limit=10
)
```

### Extracting from LaTeX Files

```python
from pathlib import Path
from vbagent.metadata.store import MetadataExtractor

extractor = MetadataExtractor()
metadata = extractor.extract(Path("question.tex"))

# Metadata is automatically extracted from comments
print(f"Subtopic: {metadata.subtopic}")
print(f"Has diagram: {metadata.has_diagram}")
print(f"Key concepts: {metadata.key_concepts}")
```

## Database Schema

The SQLite database includes the following columns:

```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    chapter TEXT,
    topic TEXT,
    subtopic TEXT,
    difficulty TEXT,
    question_type TEXT,
    tags TEXT,                    -- JSON array
    has_diagram INTEGER,          -- 0/1 for false/true
    diagram_type TEXT,
    num_options INTEGER,
    key_concepts TEXT,            -- JSON array
    requires_calculus INTEGER,    -- 0/1 for false/true
    confidence REAL,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## CLI Usage

### Indexing with Extended Metadata

```bash
# Index a directory - metadata is extracted from comments
vbagent metadata index /path/to/questions

# Query with new filters
vbagent metadata query --subtopic "position-time graphs" --has-diagram

# View statistics
vbagent metadata stats
```

### Creating DPPs with Extended Filters

```bash
# Create DPP with only diagram-based questions
vbagent dpp create -n 10 --has-diagram

# Create DPP with non-calculus questions
vbagent dpp create -n 15 --no-calculus

# Combine filters
vbagent dpp create -n 20 --topic kinematics --difficulty easy --has-diagram
```

## Best Practices

1. **Consistent Naming**: Use consistent naming for topics, subtopics, and diagram types
2. **Key Concepts**: List 3-5 key concepts per question for better searchability
3. **Confidence Scores**: Use confidence scores when auto-generating metadata to track quality
4. **Diagram Types**: Use standard diagram type names: "graph", "circuit", "free_body", "ray_diagram", "vector", "energy_level", etc.
5. **Tags vs Key Concepts**: Use tags for broad categorization, key concepts for specific learning objectives

## Migration from Old Schema

If you have an existing metadata database, it will be automatically migrated when you first open it with the updated code. The new columns will be added with NULL values for existing records. You can re-index your questions to populate the new fields:

```bash
# Re-index to extract new metadata fields
vbagent metadata index /path/to/questions --force
```
