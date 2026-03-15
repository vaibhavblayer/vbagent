# Metadata & Caching System (Option 3 Implementation)

## Overview

Implemented a clean, file-based metadata and content-addressable caching system for VBAgent pipeline tracking.

## Architecture

### Directory Structure

```
.vbagent/
├── metadata/
│   ├── problem_1.json          # Complete metadata for problem_1
│   ├── problem_2.json          # Complete metadata for problem_2
│   └── ...
└── cache/
    ├── content/
    │   ├── abc123...def.tex    # Content-addressed by SHA256 hash
    │   ├── 456789...abc.json
    │   └── ...
    └── index.json              # Cache index for fast lookup
```

### Key Components

#### 1. **Metadata Models** (`vbagent/models/metadata.py`)
- `PipelineMetadata`: Complete metadata for a problem's pipeline execution
- `StageMetadata`: Metadata for individual pipeline stages
- `ClassificationMetadata`: Extended metadata for classification stage
- `SourceInfo`: Source image information
- `CacheIndex`: Index of cached content
- `CacheEntry`: Individual cache entry with usage tracking

#### 2. **MetadataManager** (`vbagent/storage/metadata_manager.py`)
- Manages metadata files in `.vbagent/metadata/`
- Provides CRUD operations for metadata
- Supports querying by subject, type, etc.
- Generates statistics across all metadata

#### 3. **ContentCache** (`vbagent/storage/content_cache.py`)
- Content-addressable storage using SHA256 hashing
- Automatic deduplication (same content = same hash = stored once)
- Usage tracking (which problems use which content)
- Cleanup strategies (by age, by usage)

#### 4. **PipelineCache** (`vbagent/cache.py`)
- Updated to use new metadata system internally
- Maintains backward compatibility with existing API
- Transparent migration from old cache structure

## Features

### Metadata Tracking

Each problem gets a comprehensive metadata file:

```json
{
  "problem_id": "problem_1",
  "source": {
    "image_path": "images/problem_1.png",
    "image_hash": "sha256:abc123...",
    "file_size": 123456
  },
  "created_at": "2026-03-15T10:30:00Z",
  "updated_at": "2026-03-15T10:35:00Z",
  "classification": {
    "status": "completed",
    "subject": "chemistry",
    "question_type": "subjective",
    "has_diagram": false,
    "duration_ms": 5000,
    "agent_name": "ImageClassifier-chemistry",
    "content_hash": "sha256:def456...",
    "cache_path": "cache/content/def456.json"
  },
  "scan": {
    "status": "completed",
    "duration_ms": 10000,
    "agent_name": "Scanner-subjective-chemistry",
    "content_hash": "sha256:ghi789...",
    "cache_path": "cache/content/ghi789.tex"
  },
  "total_duration_ms": 45000,
  "stages_completed": 5,
  "stages_failed": 0,
  "stages_skipped": 1
}
```

### Content Deduplication

- Content is stored by SHA256 hash
- If two problems have identical LaTeX, it's stored once
- Saves disk space and improves cache efficiency
- Usage tracking shows which problems reference each content

### CLI Commands

#### `vbagent cache status`
Shows cache statistics and metadata summary:
- Total problems, completed, failed
- Breakdown by subject and question type
- Cache size and entry count

#### `vbagent cache list`
Lists all cached problems with metadata:
```bash
vbagent cache list
vbagent cache list --subject chemistry
vbagent cache list --type subjective
```

#### `vbagent cache clean`
Cleans up old or unused cache entries:
```bash
vbagent cache clean --days 30        # Remove entries older than 30 days
vbagent cache clean --unused         # Remove unreferenced entries
vbagent cache clean --dry-run        # Preview without deleting
```

#### `vbagent cache clear`
Clears entire cache or specific problem:
```bash
vbagent cache clear                  # Clear all (with confirmation)
vbagent cache clear --problem problem_1
```

## Benefits

### 1. **Single Source of Truth**
- One metadata file per problem contains everything
- No duplication across cache/database/output
- Easy to inspect and debug

### 2. **Queryable Metadata**
- Find all chemistry problems: `jq '.classification.subject' .vbagent/metadata/*.json | grep chemistry`
- Find problems by type, duration, status, etc.
- No database required for queries

### 3. **Git-Friendly**
- JSON files can be version controlled
- Diff-friendly format
- Easy to track changes over time

### 4. **Efficient Storage**
- Content deduplication via hashing
- Automatic cleanup of unused content
- Track cache size and usage

### 5. **Stage Tracking**
- Timestamps for each stage
- Duration tracking
- Agent and model information
- Error messages for failed stages

### 6. **Backward Compatible**
- Existing `PipelineCache` API still works
- Transparent migration to new system
- No breaking changes

## Usage in Pipeline

The system integrates seamlessly with existing pipeline code:

```python
from vbagent.cache import PipelineCache

cache = PipelineCache()

# Check if stage is cached
if cache.has(problem_id, "classification"):
    result = cache.get(problem_id, "classification")
else:
    result = classify_image(image_path)
    cache.set(problem_id, "classification", result)
```

Behind the scenes:
1. Metadata is loaded/created
2. Content is stored in content-addressable cache
3. Metadata is updated with hash and cache path
4. Statistics are automatically calculated

## Future Enhancements

### Phase 1 (Completed)
- ✅ Metadata models
- ✅ MetadataManager
- ✅ ContentCache
- ✅ PipelineCache integration
- ✅ CLI commands

### Phase 2 (Future)
- [ ] Analytics dashboard (web UI)
- [ ] Export metadata to CSV/Excel
- [ ] Distributed caching support
- [ ] Cache warming strategies
- [ ] Performance metrics visualization

### Phase 3 (Future)
- [ ] Machine learning on metadata (predict duration, difficulty)
- [ ] Automatic problem tagging
- [ ] Similarity detection (find duplicate problems)
- [ ] Recommendation system (suggest similar problems)

## Migration Notes

Since old data is not important (as per user), no migration is needed. The system will:
1. Create new metadata for new problems
2. Old cache in `.vbagent/pipeline_cache/` can be safely deleted
3. Old batch database `.vbagent_batch.db` continues to work for batch processing

## Technical Details

### Hash-Based Deduplication

```python
# Content is hashed
content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

# Stored with hash as filename
file_path = f".vbagent/cache/content/{content_hash}.tex"

# Multiple problems can reference same hash
# = stored once, used many times
```

### Metadata Updates

```python
# Metadata is automatically updated
metadata.update_timestamp()          # Updates updated_at
metadata.calculate_summary()         # Recalculates statistics
metadata_manager.save(metadata)      # Saves to disk
```

### Cache Index

```json
{
  "entries": {
    "abc123...": {
      "content_hash": "abc123...",
      "file_path": "cache/content/abc123.tex",
      "content_type": "tex",
      "size_bytes": 1234,
      "created_at": "2026-03-15T10:30:00Z",
      "last_accessed": "2026-03-15T11:00:00Z",
      "access_count": 5,
      "used_by": ["problem_1", "problem_2"]
    }
  },
  "total_size_bytes": 123456,
  "last_cleanup": "2026-03-15T09:00:00Z"
}
```

## Summary

Implemented a clean, efficient, and maintainable metadata and caching system that:
- Provides single source of truth for pipeline metadata
- Enables content deduplication via hashing
- Supports powerful querying and analytics
- Maintains backward compatibility
- Includes comprehensive CLI tools
- Is Git-friendly and portable

The system is production-ready and can be extended with additional features as needed.
