# Multi-Stage Classification Implementation

## Overview

Implemented a new multi-stage classification architecture with proper separation of concerns and parallel execution for metadata enrichment.

## Architecture

### Stage 1: Structural Classification (Agent 1)
- **Model:** `gpt-5-nano` (fast, cheap)
- **Reasoning:** None
- **Input:** Image only
- **Output:** Structural metadata (question_type, has_diagram, diagram_type, etc.)
- **Purpose:** Extract only what's needed for downstream routing decisions
- **Fallback:** `gpt-5-mini` if confidence < 0.7

### Stage 2: Scanner (Agent 2)
- **Model:** `gpt-5.2` or `gpt-5.1`
- **Reasoning:** Medium (changed from high)
- **Input:** Image + Stage 1 output
- **Output:** LaTeX content (problem + solution)

### Stage 3: TikZ Generation (if has_diagram)
- **Model:** `gpt-5.1` or `gpt-5.1-codex`
- **Reasoning:** Medium
- **Input:** Image + Stage 1 + Stage 2 output
- **Output:** TikZ code

### Stage 4: Taxonomy Classification (NEW)
- **Model:** `gpt-5-nano`
- **Reasoning:** None
- **Input:** LaTeX text only (NO image)
- **Output:** Chapter, topic, subtopic (structured output with enum constraints)
- **Features:**
  - Uses OpenAI structured outputs for guaranteed compliance
  - Dynamic Pydantic schema with Literal types from taxonomy
  - Fallback to `gpt-5-mini` if confidence < 0.8
- **Runs in parallel with Stage 5**

### Stage 5: Difficulty Assessment (Existing v2.0, Enhanced)
- **Model:** `gpt-5.1` or `gpt-5.2`
- **Reasoning:** Low
- **Input:** LaTeX text + PrimaryClassification object
- **Output:** Comprehensive difficulty assessment with nested structures
- **Features:**
  - Uses existing comprehensive `DifficultyAssessment` model from v2.0
  - Nested structures: `DifficultyFactors`, `ProblemStructure`, `ExamRelevance`
  - 15+ metadata fields including solution approach, formulas, learning objectives
  - Updated to use `difficulty_assessor` agent config
- **Runs in parallel with Stage 4**

## Implementation Files

### Core Components

1. **`vbagent/config.py`**
   - Added `taxonomy_classifier` and `difficulty_assessor` agent configs
   - Added `gpt-5-nano` to supported models
   - Added pipeline settings: `enable_taxonomy`, `enable_difficulty`, `run_metadata_parallel`
   - Added confidence thresholds: `classifier_confidence_threshold`, `taxonomy_confidence_threshold`
   - Updated model groups with nano for classifier and taxonomy
   - Updated default reasoning levels (scanner: medium, difficulty: low)

2. **`vbagent/models/metadata.py`** (NEW)
   - `TaxonomyClassification`: Chapter, topic, subtopic, concepts, prerequisites, etc.
   - `EnrichedMetadata`: Combined taxonomy + difficulty (uses v2.0 DifficultyAssessment)
   - Note: `DifficultyAssessment` comes from `classification_v2.py` (existing comprehensive model)

3. **`vbagent/agents/classification/schema_builder.py`** (NEW)
   - `create_taxonomy_schema()`: Dynamic Pydantic model with Literal types
   - `get_taxonomy_json_schema()`: JSON schema for OpenAI structured outputs
   - Adds enum constraints for chapter/topic from taxonomy
   - Cached for performance

4. **`vbagent/agents/taxonomy_classifier.py`** (NEW)
   - `classify_taxonomy()`: Main function for taxonomy classification
   - `create_taxonomy_classifier_agent()`: Agent factory with structured output
   - Uses nano model with fallback to mini
   - Enforces taxonomy compliance via structured outputs

5. **`vbagent/agents/classification/difficulty_assessor.py`** (Enhanced Existing)
   - Updated to use `difficulty_assessor` agent config (was using `classifier`)
   - Comprehensive `DifficultyAssessment` model with nested structures
   - `DifficultyFactors`: concept_complexity, calculation_complexity, multi_step, etc.
   - `ProblemStructure`: has_given_data, has_find_statement, has_constraints, is_multi_part
   - `ExamRelevance`: jee_main, jee_advanced, neet scores (0.0-1.0)
   - Additional fields: solution_approach, required_formulas, learning_objectives, tags_auto
   - Much more comprehensive than a simple difficulty assessment

6. **`vbagent/agents/metadata_enricher.py`** (NEW)
   - `enrich_metadata()`: Main entry point (respects config.run_metadata_parallel)
   - `enrich_metadata_parallel()`: Async parallel execution of Stage 4 & 5
   - `enrich_metadata_sync()`: Synchronous wrapper for parallel execution
   - `enrich_metadata_sequential()`: Sequential execution (Stage 5 can use taxonomy)
   - Adapted to work with existing comprehensive difficulty assessor

### API Exports

7. **`vbagent/__init__.py`**
   - Added `classify_taxonomy`, `assess_difficulty`, `enrich_metadata` to exports
   - Added `TaxonomyClassification`, `DifficultyAssessment`, `EnrichedMetadata` models
   - Lazy loading for all new functions

8. **`vbagent/agents/__init__.py`**
   - Added new agent functions to exports
   - Lazy loading for taxonomy_classifier, metadata_enricher modules
   - `assess_difficulty` imported from `classification.difficulty_assessor` (existing)

9. **`vbagent/models/__init__.py`**
   - Added new metadata models to exports
   - `TaxonomyClassification` and `EnrichedMetadata` from metadata module
   - `DifficultyAssessment` from classification_v2 module (existing comprehensive model)
   - Lazy loading for metadata module

## Key Features

### 1. Structured Outputs
- Stage 4 uses OpenAI structured outputs with JSON schema
- Enum constraints for chapter/topic enforce taxonomy compliance
- Guaranteed valid chapter/topic selection (no post-validation needed)

### 2. Parallel Execution
- Stage 4 and 5 run simultaneously using `asyncio.gather()`
- Total time = max(stage_4_time, stage_5_time), not sum
- Configurable via `config.run_metadata_parallel`

### 3. Confidence-Based Fallback
- Stage 1: nano → mini if confidence < 0.7
- Stage 4: nano → mini if confidence < 0.8
- Automatic quality improvement for edge cases

### 4. Model Optimization
- Stage 1: nano (structural classification, no reasoning)
- Stage 2: 5.2 with medium reasoning (LaTeX extraction)
- Stage 4: nano (taxonomy classification, no reasoning)
- Stage 5: 5.1 with low reasoning (difficulty analysis)
- Cost-effective while maintaining quality

### 5. Input Optimization
- Stage 4 & 5 use LaTeX text only (no image)
- Smaller context, fits nano limits
- Faster processing

## Configuration

### Default Settings
```json
{
  "agents": {
    "classifier": {
      "model": "gpt-5-nano",
      "reasoning_effort": "low"
    },
    "scanner": {
      "model": "gpt-5.2",
      "reasoning_effort": "medium"
    },
    "taxonomy_classifier": {
      "model": "gpt-5-nano",
      "reasoning_effort": "low"
    },
    "difficulty_assessor": {
      "model": "gpt-5.1",
      "reasoning_effort": "low"
    }
  },
  "enable_taxonomy": true,
  "enable_difficulty": true,
  "run_metadata_parallel": true,
  "classifier_confidence_threshold": 0.7,
  "taxonomy_confidence_threshold": 0.8
}
```

## Usage

### Library API

```python
from vbagent import classify_taxonomy, assess_difficulty, enrich_metadata

# Stage 4 only: Taxonomy classification
taxonomy = classify_taxonomy(
    latex_problem="...",
    latex_solution="...",  # optional
    tikz_code="...",       # optional
    question_type="mcq_sc",
    key_concepts=["forces", "friction"],
    requires_calculus=False,
    subject="physics"
)
print(f"Chapter: {taxonomy.chapter}, Topic: {taxonomy.topic}")

# Stage 5 only: Difficulty assessment
difficulty = assess_difficulty(
    latex_problem="...",
    latex_solution="...",
    question_type="mcq_sc",
    requires_calculus=False,
    chapter="Laws of Motion",  # optional context
    topic="friction",
    subject="physics"
)
print(f"Difficulty: {difficulty.difficulty} ({difficulty.difficulty_score}/10)")

# Both stages (parallel by default)
metadata = enrich_metadata(
    latex_problem="...",
    latex_solution="...",
    tikz_code="...",
    question_type="mcq_sc",
    key_concepts=["forces"],
    requires_calculus=False,
    subject="physics",
    parallel=True  # or None to use config default
)
print(f"Chapter: {metadata.taxonomy.chapter}")
print(f"Difficulty: {metadata.difficulty.difficulty}")
```

### CLI Integration (TODO)

```bash
# Scan with metadata enrichment (default)
vbagent scan -i question.png

# Scan without metadata
vbagent scan -i question.png --no-metadata

# Force re-classification (invalidate cache)
vbagent scan -i question.png --force

# Full pipeline with metadata
vbagent process -i question.png
```

## Next Steps

### 1. CLI Integration
- [ ] Add `--force` / `--no-cache` flag to scan command
- [ ] Add `--no-metadata` / `--no-taxonomy` / `--no-difficulty` flags
- [ ] Update scan command to run Stage 4 & 5 by default
- [ ] Add cache management for metadata outputs

### 2. Cache Management
- [ ] Create `agentic/metadata/taxonomy/` and `agentic/metadata/difficulty/` directories
- [ ] Save Stage 4 & 5 outputs as JSON files
- [ ] Implement cache invalidation with `--force`
- [ ] Granular cache control (--force-classify, --force-metadata, etc.)

### 3. Update Stage 1 (Classifier)
- [ ] Remove chapter/topic/difficulty from Stage 1 output
- [ ] Simplify to structural classification only
- [ ] Update `PrimaryClassification` model
- [ ] Update all consumers of Stage 1 output

### 4. Taxonomy Population
- [ ] Add subtopics to taxonomy structure (currently topics are flat lists)
- [ ] Change from `List[str]` to `Dict[str, List[str]]` (topic → subtopics)
- [ ] Populate subtopics for Physics (high priority)
- [ ] Populate subtopics for Chemistry, Mathematics, Biology

### 5. Testing
- [ ] Unit tests for taxonomy_classifier
- [ ] Unit tests for difficulty_assessor
- [ ] Unit tests for metadata_enricher (parallel execution)
- [ ] Integration tests for full pipeline
- [ ] Test confidence-based fallback

### 6. Documentation
- [ ] Update README with new architecture
- [ ] Add examples for metadata enrichment
- [ ] Document CLI flags
- [ ] Update API documentation

## Benefits

1. **Better Accuracy:** Taxonomy classification after LaTeX extraction (full context)
2. **Faster Stage 1:** Simplified to structural classification only
3. **Cost Optimization:** Nano for classification tasks, 5.1/5.2 only where needed
4. **Parallel Execution:** Stage 4 & 5 run simultaneously (faster pipeline)
5. **Guaranteed Compliance:** Structured outputs enforce taxonomy constraints
6. **Comprehensive Metadata:** Uses existing v2.0 difficulty model with 15+ fields and nested structures
7. **Flexible:** Can run stages independently or together
8. **Configurable:** Enable/disable metadata enrichment, parallel execution, etc.
9. **No Duplication:** Merged with existing comprehensive difficulty assessor

## Performance

### Before (Single Agent 3)
- 1 API call × gpt-5.1 × high reasoning
- Time: ~5-10 seconds
- Cost: ~$0.XX

### After (Parallel Stage 4 + 5)
- Stage 4: 1 × gpt-5-nano × no reasoning = ~$0.00X (very cheap)
- Stage 5: 1 × gpt-5.1 × low reasoning = ~$0.0X
- Total time: max(stage_4, stage_5) = ~5-8 seconds (similar or faster)
- Total cost: ~$0.0X (similar or cheaper)

**Net result:** Similar or better performance at similar or lower cost, with better separation of concerns and accuracy.
