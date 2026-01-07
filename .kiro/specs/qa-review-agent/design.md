# Design Document: QA Review Agent

## Overview

The QA Review Agent extends VBAgent with quality assurance capabilities for processed physics questions. It provides random spot-checking, AI-powered review with diff-based suggestions, interactive approval workflow, and versioned backup storage for rejected suggestions.

The system follows the existing VBAgent architecture patterns:
- Agent-based AI processing using OpenAI Agents SDK
- SQLite for state persistence (similar to BatchDatabase)
- Click-based CLI with Rich console output
- Pydantic models for structured data

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                    │
│  vbagent check [--count N] [--problem-id ID] [--dir PATH]           │
│  vbagent check history [--problem-id ID]                            │
│  vbagent check apply VERSION_ID                                     │
│  vbagent check stats [--days N]                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Review Orchestrator                             │
│  - Coordinates random selection, AI review, and user interaction    │
│  - Manages review session state                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────────┐    ┌─────────────────┐
│ Random        │    │ QA Review Agent   │    │ Interactive     │
│ Selector      │    │ (AI)              │    │ Review UI       │
│               │    │                   │    │                 │
│ - Discover    │    │ - Analyze LaTeX   │    │ - Display diff  │
│   problems    │    │ - Check physics   │    │ - Prompt user   │
│ - Random pick │    │ - Generate diffs  │    │ - Apply changes │
│ - Load files  │    │ - Score confidence│    │ - Handle input  │
└───────────────┘    └───────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Version Store (SQLite)                        │
│  - Rejected suggestions with version tracking                        │
│  - Review session history and statistics                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Random Selector (`vbagent/agents/selector.py`)

```python
@dataclass
class ProblemContext:
    """Context for a problem selected for review."""
    problem_id: str
    base_path: Path
    image_path: str | None
    latex_path: str
    latex_content: str
    variants: dict[str, str]  # variant_type -> latex content
    variant_paths: dict[str, str]  # variant_type -> file path

def discover_problems(output_dir: str) -> list[str]:
    """Discover all problem IDs in the output directory."""
    
def select_random(output_dir: str, count: int) -> list[str]:
    """Randomly select problem IDs for review."""
    
def load_problem_context(output_dir: str, problem_id: str) -> ProblemContext:
    """Load all files for a problem into a review context."""
```

### 2. QA Review Agent (`vbagent/agents/reviewer.py`)

```python
class ReviewIssueType(str, Enum):
    LATEX_SYNTAX = "latex_syntax"
    PHYSICS_ERROR = "physics_error"
    SOLUTION_ERROR = "solution_error"
    VARIANT_INCONSISTENCY = "variant_inconsistency"
    FORMATTING = "formatting"
    OTHER = "other"

class Suggestion(BaseModel):
    """A suggested edit from the QA Review Agent."""
    issue_type: ReviewIssueType
    file_path: str
    description: str
    reasoning: str
    confidence: float  # 0.0 to 1.0
    original_content: str
    suggested_content: str
    diff: str  # unified diff format

class ReviewResult(BaseModel):
    """Result from reviewing a problem."""
    problem_id: str
    passed: bool
    suggestions: list[Suggestion]
    summary: str

async def review_problem(context: ProblemContext) -> ReviewResult:
    """Review a problem and generate suggestions."""
```

### 3. Diff Utilities (`vbagent/models/diff.py`)

```python
def generate_unified_diff(
    original: str,
    modified: str,
    file_path: str,
    context_lines: int = 3
) -> str:
    """Generate unified diff between original and modified content."""

def apply_diff(file_path: str, diff: str) -> bool:
    """Apply a unified diff to a file. Returns True if successful."""

def parse_diff(diff: str) -> tuple[str, str]:
    """Parse a unified diff to extract original and modified content."""

def display_diff(diff: str, console: Console) -> None:
    """Display a diff with color coding using Rich."""
```

### 4. Version Store (`vbagent/models/version_store.py`)

```python
class SuggestionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class StoredSuggestion:
    """A suggestion stored in the version store."""
    id: int
    version: int
    problem_id: str
    file_path: str
    issue_type: str
    description: str
    reasoning: str
    confidence: float
    original_content: str
    suggested_content: str
    diff: str
    status: SuggestionStatus
    created_at: datetime
    session_id: str | None

class VersionStore:
    """SQLite-based storage for suggestions and review history."""
    
    def save_suggestion(
        self,
        suggestion: Suggestion,
        problem_id: str,
        status: SuggestionStatus,
        session_id: str | None = None
    ) -> int:
        """Save a suggestion and return its ID."""
    
    def get_versions(
        self,
        problem_id: str | None = None,
        file_path: str | None = None
    ) -> list[StoredSuggestion]:
        """Get version history for a problem or file."""
    
    def get_suggestion(self, suggestion_id: int) -> StoredSuggestion | None:
        """Get a specific suggestion by ID."""
    
    def update_status(
        self,
        suggestion_id: int,
        status: SuggestionStatus
    ) -> None:
        """Update the status of a suggestion."""
    
    def get_stats(
        self,
        days: int | None = None
    ) -> dict:
        """Get review statistics."""
```

### 5. Interactive Review UI (`vbagent/cli/check.py`)

```python
class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    SKIP = "skip"
    EDIT = "edit"
    QUIT = "quit"

def prompt_review_action(
    suggestion: Suggestion,
    console: Console
) -> ReviewAction:
    """Display suggestion and prompt user for action."""

def apply_suggestion(suggestion: Suggestion) -> bool:
    """Apply an approved suggestion to the file."""

def run_review_session(
    problems: list[ProblemContext],
    store: VersionStore,
    console: Console
) -> dict:
    """Run an interactive review session. Returns summary stats."""
```

## Data Models

### Database Schema (Version Store)

```sql
-- Suggestions table
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    problem_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    confidence REAL NOT NULL,
    original_content TEXT NOT NULL,
    suggested_content TEXT NOT NULL,
    diff TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(problem_id, file_path, version)
);

-- Review sessions table
CREATE TABLE review_sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    problems_reviewed INTEGER DEFAULT 0,
    suggestions_made INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0
);

-- Index for efficient queries
CREATE INDEX idx_suggestions_problem ON suggestions(problem_id);
CREATE INDEX idx_suggestions_status ON suggestions(status);
CREATE INDEX idx_suggestions_created ON suggestions(created_at);
```

### Pydantic Models

```python
# vbagent/models/review.py

class ReviewIssueType(str, Enum):
    LATEX_SYNTAX = "latex_syntax"
    PHYSICS_ERROR = "physics_error"
    SOLUTION_ERROR = "solution_error"
    VARIANT_INCONSISTENCY = "variant_inconsistency"
    FORMATTING = "formatting"
    OTHER = "other"

class Suggestion(BaseModel):
    """A suggested edit from the QA Review Agent."""
    issue_type: ReviewIssueType
    file_path: str
    description: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    original_content: str
    suggested_content: str
    diff: str

class ReviewResult(BaseModel):
    """Result from reviewing a problem."""
    problem_id: str
    passed: bool
    suggestions: list[Suggestion]
    summary: str

class ReviewStats(BaseModel):
    """Statistics from review sessions."""
    total_reviewed: int
    total_suggestions: int
    approved_count: int
    rejected_count: int
    skipped_count: int
    approval_rate: float
    issues_by_type: dict[str, int]
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Random Selection Count Constraint

*For any* output directory with N problems and any requested count M, the Random Selector SHALL return exactly min(N, M) problems.

**Validates: Requirements 1.1, 1.3**

### Property 2: Problem Context Completeness

*For any* problem selected for review, the loaded ProblemContext SHALL contain non-empty latex_content and the variants dictionary SHALL contain entries for all variant files present in the problem directory.

**Validates: Requirements 1.2**

### Property 3: Suggestion Model Validity

*For any* Suggestion generated by the QA Review Agent, the suggestion SHALL have a valid issue_type enum value, confidence between 0.0 and 1.0, and a non-empty diff field in unified diff format.

**Validates: Requirements 2.3, 2.4**

### Property 4: Diff Round-Trip

*For any* original content and modified content, generating a unified diff and then parsing it SHALL produce content equivalent to the original inputs.

**Validates: Requirements 3.5, 3.6**

### Property 5: Diff Application Correctness

*For any* file with original content and a valid unified diff, applying the diff SHALL produce a file with content matching the expected modified content.

**Validates: Requirements 4.2**

### Property 6: Rejected Suggestion Storage

*For any* suggestion that is rejected, the Version Store SHALL contain a record with matching problem_id, file_path, and diff content that can be retrieved.

**Validates: Requirements 4.3**

### Property 7: Version Store Persistence

*For any* sequence of suggestions stored for the same problem-file combination, each stored suggestion SHALL have a unique, monotonically increasing version number, and all required fields (problem_id, file_path, diff, reasoning, timestamp, version) SHALL be persisted.

**Validates: Requirements 5.1, 5.2, 5.5**

### Property 8: Version History Retrieval

*For any* problem_id with N stored suggestions, querying version history for that problem_id SHALL return exactly N suggestions.

**Validates: Requirements 5.3**

### Property 9: Stored Diff Application

*For any* suggestion stored in the Version Store, retrieving it by ID and applying its diff to a file with the original content SHALL produce the expected modified content.

**Validates: Requirements 5.4**

### Property 10: Version Data Serialization Round-Trip

*For any* StoredSuggestion, serializing to JSON and deserializing SHALL produce an equivalent StoredSuggestion with all fields preserved.

**Validates: Requirements 5.6**

### Property 11: Statistics Accumulation

*For any* sequence of review actions (approve, reject, skip), the cumulative statistics SHALL accurately reflect the total counts for each action type.

**Validates: Requirements 7.1, 7.3**

### Property 12: Date Range Filtering

*For any* set of stored suggestions with various timestamps and any date range query, the filtered results SHALL contain exactly those suggestions whose timestamps fall within the specified range.

**Validates: Requirements 7.4**

### Property 13: Failed Diff Preserves Original

*For any* file and an invalid or inapplicable diff, attempting to apply the diff SHALL leave the file content unchanged.

**Validates: Requirements 8.1**

## Error Handling

### Diff Application Errors

- **File not found**: Log error, skip suggestion, continue session
- **Diff conflict**: Warn user that file has changed, offer to regenerate diff or skip
- **Permission denied**: Report error, preserve original, continue session

### AI Review Errors

- **API timeout**: Retry with exponential backoff (max 3 attempts)
- **Invalid response**: Log error, skip problem, continue with next
- **Rate limiting**: Pause and retry after delay

### Version Store Errors

- **Database locked**: Retry with backoff
- **Corruption detected**: Attempt recovery, report status to user
- **Disk full**: Report error, suggest cleanup

### Session Interruption

- **SIGINT/SIGTERM**: Save current session state, allow resume
- **Crash recovery**: On startup, check for incomplete sessions and offer to resume

## Testing Strategy

### Property-Based Testing

The system will use **Hypothesis** for property-based testing in Python, consistent with the existing test infrastructure (`.hypothesis` directory present in workspace).

Each correctness property will be implemented as a property-based test with:
- Minimum 100 iterations per property
- Smart generators that produce valid test data
- Explicit property annotations linking to requirements

### Unit Tests

Unit tests will cover:
- Edge cases for random selection (empty directory, single problem)
- Diff generation with various content types (LaTeX special characters, unicode)
- Version store CRUD operations
- CLI argument parsing

### Test File Organization

```
tests/
├── test_selector.py      # Random selector tests
├── test_reviewer.py      # QA Review Agent tests  
├── test_diff.py          # Diff utilities tests
├── test_version_store.py # Version store tests
├── test_check.py         # CLI integration tests
```

### Property Test Annotations

Each property-based test MUST include a comment in this format:
```python
# **Feature: qa-review-agent, Property 1: Random Selection Count Constraint**
# **Validates: Requirements 1.1, 1.3**
@given(...)
def test_random_selection_count(problems, count):
    ...
```
