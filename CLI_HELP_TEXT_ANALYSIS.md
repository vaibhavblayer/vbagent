# CLI Help Text Analysis

## Issues Found

### 1. **Subject-Specific Language**

**Problem**: Many help texts say "physics question" but the system now supports:
- Physics
- Chemistry  
- Mathematics

**Affected Files**:
- `vbagent/cli/main.py` - Main description
- `vbagent/cli/core/classify.py` - "Classify physics question"
- `vbagent/cli/core/scan.py` - "Extract LaTeX from physics question"
- `vbagent/cli/core/process.py` - "Complete physics question processing"
- `vbagent/cli/generation/convert.py` - "Converting physics questions"
- `vbagent/cli/generation/idea.py` - "Extract physics concepts"
- `vbagent/cli/generation/alternate.py` - "Generate alternative solutions for physics"
- `vbagent/cli/generation/variant.py` - "Generate problem variants"
- `vbagent/cli/generation/tikz.py` - "Generate TikZ for physics diagrams"
- `vbagent/cli/generation/fbd.py` - "Generate Free Body Diagram" (physics-specific, OK)
- `vbagent/cli/interfaces/chat.py` - "physics question processing system"

### 2. **Outdated Examples**

**Problem**: Examples don't show subject-aware features or new capabilities

**Examples that need updating**:


#### classify command
```bash
# Current examples don't mention subject detection
vbagent classify -i question.png

# Should show:
vbagent classify -i chemistry_question.png
vbagent classify -i mathematics_problem.png --json
```

#### scan command
```bash
# Current examples don't show subject-specific scanning
vbagent scan -i question.png

# Should show:
vbagent scan -i chemistry_question.png
vbagent scan -i math_problem.png --type subjective
```

#### process command
```bash
# Current examples mention "physics concepts" in ideas
# Should be generic "concepts" or "subject concepts"
```

### 3. **Missing Information**

**What's not documented**:
- Subject detection (physics/chemistry/mathematics)
- Subject-specific diagram types (organic structures, energy diagrams, function graphs, etc.)
- Subject-specific formatting (\\ce{} for chemistry, proof structure for mathematics)
- New cache management commands
- Metadata tracking features

### 4. **Diagram Type Documentation**

**Problem**: Help texts don't mention the full range of diagram types now supported

**Current**: Mentions FBD, circuit, optics (physics only)

**Should mention**:
- **Physics**: FBD, circuit, graph, optics
- **Chemistry**: organic structure, reaction mechanism, orbital, lewis structure, chemical equation, energy diagram
- **Mathematics**: function graph, coordinate geometry, geometric figure, number line, venn diagram



## Recommended Changes

### Priority 1: Generic Language (High Impact)

Replace "physics question" with generic terms:
- "physics question" → "question" or "problem"
- "physics concepts" → "concepts" or "key ideas"
- "physics diagrams" → "diagrams"
- "physics question processing" → "question processing" or "multi-subject question processing"

### Priority 2: Add Subject Information (Medium Impact)

Add notes about subject support:
```
Supports multiple subjects: physics, chemistry, mathematics
Subject is automatically detected from the image.
```

### Priority 3: Update Examples (Medium Impact)

Show diverse examples:
```bash
# Physics
vbagent process -i physics/kinematics.png

# Chemistry  
vbagent process -i chemistry/thermodynamics.png

# Mathematics
vbagent process -i math/calculus.png
```

### Priority 4: Document New Features (Low Impact)

Add documentation for:
- Cache management (`vbagent cache status`)
- Metadata tracking
- Subject-specific diagram types
- Subject-specific formatting



## Files to Update

### Core Commands
1. ✅ `vbagent/cli/main.py` - Main description
2. ⚠️ `vbagent/cli/core/classify.py` - Classification help
3. ⚠️ `vbagent/cli/core/scan.py` - Scanning help
4. ⚠️ `vbagent/cli/core/process.py` - Pipeline help
5. ⚠️ `vbagent/cli/core/batch.py` - Batch processing help

### Generation Commands
6. ⚠️ `vbagent/cli/generation/convert.py` - Format conversion help
7. ⚠️ `vbagent/cli/generation/idea.py` - Idea extraction help
8. ⚠️ `vbagent/cli/generation/alternate.py` - Alternate solutions help
9. ⚠️ `vbagent/cli/generation/variant.py` - Variant generation help
10. ⚠️ `vbagent/cli/generation/tikz.py` - TikZ generation help
11. ✅ `vbagent/cli/generation/fbd.py` - FBD (physics-specific, OK as is)

### Interface Commands
12. ⚠️ `vbagent/cli/interfaces/chat.py` - Chat interface help

### Legend
- ✅ = OK or already updated
- ⚠️ = Needs updating

## Specific Text Replacements

### main.py
```python
# OLD
"""VBAgent - Physics question processing pipeline."""

# NEW
"""VBAgent - Multi-subject question processing pipeline."""

# OLD
"A multi-agent CLI system for processing physics question images."

# NEW
"A multi-agent CLI system for processing question images across physics, chemistry, and mathematics."
```

### classify.py
```python
# OLD
"""Stage 1: Classify physics question image."""

# NEW
"""Stage 1: Classify question image and detect subject."""

# OLD
"Analyzes a physics question image and extracts metadata"

# NEW
"Analyzes a question image and extracts metadata including subject (physics/chemistry/mathematics)"
```

### scan.py
```python
# OLD
"""Stage 2: Extract LaTeX from physics question image."""

# NEW
"""Stage 2: Extract LaTeX from question image with subject-specific formatting."""

# OLD
help="Path to the physics question image file"

# NEW
help="Path to the question image file"
```

### process.py
```python
# OLD
"Orchestrates all agents for complete physics question processing."

# NEW
"Orchestrates all agents for complete question processing across multiple subjects."

# OLD
"4. Ideas - Extract physics concepts (--ideas)"

# NEW
"4. Ideas - Extract key concepts and problem-solving ideas (--ideas)"
```



## Implementation Strategy

### Phase 1: Quick Wins (15 minutes)
1. Update main.py description
2. Global find/replace in CLI files:
   - "physics question" → "question"
   - "Physics question" → "Question"
   - "physics concepts" → "concepts"
   - "physics diagrams" → "diagrams"

### Phase 2: Contextual Updates (30 minutes)
1. Add subject information to classify command
2. Add subject-specific formatting notes to scan command
3. Update process command with subject examples
4. Update tikz command with diagram type list

### Phase 3: Enhanced Documentation (30 minutes)
1. Add comprehensive examples showing all three subjects
2. Document subject-specific features
3. Add notes about automatic subject detection
4. Update variant types documentation

### Phase 4: New Features Documentation (15 minutes)
1. Ensure cache commands are well-documented
2. Add metadata tracking information
3. Document subject-specific diagram agents

## Testing Checklist

After updates, verify:
- [ ] `vbagent --help` shows generic language
- [ ] `vbagent classify --help` mentions subject detection
- [ ] `vbagent scan --help` mentions subject-specific formatting
- [ ] `vbagent process --help` shows multi-subject examples
- [ ] `vbagent tikz --help` lists all diagram types
- [ ] `vbagent cache --help` is comprehensive
- [ ] No references to "physics-only" remain (except FBD)
- [ ] Examples show physics, chemistry, and mathematics

## Summary

**Total files to update**: 12  
**Estimated time**: 90 minutes  
**Impact**: High - improves user understanding of multi-subject capabilities  
**Risk**: Low - only documentation changes, no code changes  

The CLI help texts are indeed outdated and need updating to reflect the multi-subject nature of the system. The main issues are:
1. Physics-centric language throughout
2. Missing subject detection information
3. No mention of chemistry/mathematics support
4. Examples don't show subject diversity
5. New features (cache, metadata) need better documentation
