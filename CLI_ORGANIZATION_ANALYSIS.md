# CLI Organization & Consistency Analysis

## Current State Analysis

### Option Consistency Issues

#### 1. **Input Options - Inconsistent**
```bash
# Image input
-i, --image          # classify, scan, process, tikz, variant, convert
-i PATH              # Some use PATH, some don't specify type

# Text input  
-t, --tex            # scan, process, idea, alternate, variant, convert, tikz
-d, --description    # tikz only (inconsistent)

# Problem: -t means different things in different contexts
```

#### 2. **Output Options - Mostly Consistent** ✅
```bash
-o, --output         # Used consistently across all commands
```

#### 3. **Format Options - Inconsistent**
```bash
--json               # classify, idea (output as JSON)
--type               # scan, variant (different meanings!)
--from, --to         # convert only
```

#### 4. **Processing Options - Inconsistent**
```bash
-c, --compile        # scan, process, tikz, variant
--verbose-compile    # scan, process, tikz, variant
--context            # process, variant (different meanings!)
--ref                # process, tikz (reference files)
```

#### 5. **Range/Count Options - Inconsistent**
```bash
-r, --range          # process, variant
-n, --count          # alternate, variant
-p, --parallel       # process only
```

### Command Grouping Issues

#### Current Structure (Flat)
```
vbagent
├── classify
├── scan
├── process
├── batch
├── tikz
├── fbd
├── idea
├── alternate
├── variant
├── convert
├── check
├── ref
├── config
├── util
├── metadata
├── dpp
├── export
├── extans
├── db
├── screenshot
├── cache
├── chat
└── mcp
```

**Problems**:
- 24 top-level commands (overwhelming)
- No logical grouping
- Hard to discover related commands
- Unclear command hierarchy


## Proposed Improvements

### 1. **Standardized Options**

#### Global Standard Options (All Commands)
```bash
-i, --input PATH          # Input file (image, tex, json, etc.)
-o, --output PATH         # Output file or directory
-v, --verbose             # Verbose output
-q, --quiet               # Quiet mode (minimal output)
-h, --help                # Help (already standard)
```

#### Common Processing Options
```bash
-c, --compile             # Compile LaTeX to validate
--no-cache                # Disable caching
--dry-run                 # Show what would happen without doing it
```

#### Common Selection Options
```bash
-r, --range START END     # Range of items (consistent format)
-n, --count N             # Number of items to generate
--subject SUBJECT         # Override subject detection
--type TYPE               # Override type detection
```

#### Format Options
```bash
--format FORMAT           # Output format (json, tex, yaml, etc.)
--from FORMAT             # Source format (convert only)
--to FORMAT               # Target format (convert only)
```

### 2. **Proposed Command Grouping**

#### Option A: Hierarchical Groups (Recommended)
```
vbagent
├── pipeline              # Pipeline commands
│   ├── classify          # Stage 1
│   ├── scan              # Stage 2
│   ├── process           # Full pipeline
│   └── batch             # Batch processing
│
├── generate              # Generation commands
│   ├── tikz              # Diagram generation
│   ├── fbd               # Free body diagrams
│   ├── idea              # Idea extraction
│   ├── alternate         # Alternate solutions
│   ├── variant           # Problem variants
│   └── convert           # Format conversion
│
├── quality               # Quality assurance
│   ├── check             # QA review
│   └── validate          # Validation only
│
├── manage                # Management commands
│   ├── cache             # Cache management
│   ├── ref               # Reference files
│   ├── config            # Configuration
│   ├── metadata          # Metadata management
│   └── db                # Database management
│
├── export                # Export commands
│   ├── latex             # Export LaTeX
│   ├── dpp               # Daily practice problems
│   └── answers           # Extract answers (extans)
│
├── util                  # Utilities
│   ├── file              # File operations
│   └── screenshot        # Screenshot management
│
└── interface             # Interfaces
    ├── chat              # Interactive chat
    └── mcp               # MCP server
```

**Usage Examples**:
```bash
vbagent pipeline classify -i question.png
vbagent pipeline process -i question.png
vbagent generate tikz -i diagram.png
vbagent generate variant -i question.png --type numerical
vbagent manage cache status
vbagent export dpp --subject chemistry
```

**Benefits**:
- Clear organization by function
- Easy to discover related commands
- Logical hierarchy
- Scalable for future commands

**Drawbacks**:
- Breaking change (need migration guide)
- More typing (but tab completion helps)
- Need backward compatibility aliases


#### Option B: Semantic Groups (Alternative)
```
vbagent
├── init                  # Initialize workspace
├── run                   # Quick run (alias for process)
│
# Core workflow (keep flat for common use)
├── classify              # Stage 1
├── scan                  # Stage 2  
├── process               # Full pipeline
├── batch                 # Batch processing
│
# Grouped commands
├── gen                   # Generation group
│   ├── tikz, fbd, idea, alternate, variant, convert
│
├── qa                    # Quality assurance group
│   ├── check, validate
│
├── admin                 # Administration group
│   ├── cache, ref, config, metadata, db
│
├── tools                 # Tool group
│   ├── export, dpp, extans, util, screenshot
│
└── serve                 # Server group
    ├── chat, mcp
```

**Benefits**:
- Common commands stay flat (less typing)
- Less disruptive migration
- Simpler mental model

**Drawbacks**:
- Still somewhat cluttered at top level
- Less clear organization

#### Option C: Minimal Disruption (Conservative)
```
vbagent
# Keep all current commands at top level
# Add aliases for grouped access

# New grouped access (optional)
├── g, generate           # Alias group for generation
├── m, manage             # Alias group for management  
├── e, export             # Alias group for export
```

**Benefits**:
- No breaking changes
- Backward compatible
- Gradual migration path

**Drawbacks**:
- Doesn't solve the clutter problem
- Inconsistent UX



### 3. **Standardized Option Mapping**

#### Before (Inconsistent)
```bash
# Image input
vbagent classify -i image.png
vbagent scan -i image.png
vbagent tikz -i image.png

# Text input
vbagent scan -t existing.tex
vbagent idea -t problem.tex
vbagent variant -t problem.tex

# Description input
vbagent tikz -d "draw a circuit"  # Only tikz uses -d
```

#### After (Consistent)
```bash
# All use -i/--input for primary input
vbagent classify -i image.png
vbagent scan -i image.png
vbagent scan -i existing.tex        # Auto-detect file type
vbagent tikz -i image.png
vbagent tikz -i description.txt     # Or use --description flag
vbagent idea -i problem.tex
vbagent variant -i problem.tex

# Secondary inputs use specific flags
vbagent scan -i image.png --reference existing.tex
vbagent variant -i problem.tex --ideas ideas.json
```

### 4. **Consistent Flag Patterns**

#### Boolean Flags (Enable/Disable)
```bash
# Current (inconsistent)
--context / --no-context
--cache / --no-cache
--compile                    # No --no-compile option

# Proposed (consistent)
--compile / --no-compile
--cache / --no-cache
--validate / --no-validate
--context / --no-context
```

#### Value Flags (Consistent Format)
```bash
# Current
--type mcq_sc
--variants numerical,context
--subject physics

# Proposed (same, already good)
--type mcq_sc
--variants numerical,context
--subject physics
```

### 5. **Help Text Standardization**

#### Template for All Commands
```
Usage: vbagent [GROUP] COMMAND [OPTIONS]

<One-line description>

<Detailed description paragraph>

Options:
  -i, --input PATH       Input file (image, tex, json)
  -o, --output PATH      Output file or directory
  [command-specific options]
  -v, --verbose          Verbose output
  -h, --help             Show this message and exit

Examples:
  # Basic usage
  vbagent command -i input.png
  
  # With output
  vbagent command -i input.png -o output.tex
  
  # Advanced
  vbagent command -i input.png --option value

See also:
  vbagent related-command --help
```



## Recommended Implementation Plan

### Phase 1: Standardize Options (Non-Breaking)
**Timeline**: 1-2 weeks  
**Effort**: Medium

1. **Add standard aliases** (keep old options working)
   ```python
   @click.option('-i', '--input', '--image', '--tex')  # Accept all
   @click.option('-o', '--output')
   @click.option('-v', '--verbose')
   ```

2. **Deprecation warnings** for old options
   ```python
   if image_provided:
       warnings.warn("--image is deprecated, use --input", DeprecationWarning)
   ```

3. **Update documentation** to show new options

4. **Add migration guide**

### Phase 2: Introduce Command Groups (Breaking)
**Timeline**: 2-3 weeks  
**Effort**: High

**Recommended**: Option A (Hierarchical Groups)

1. **Create group structure**
   ```python
   @click.group()
   def pipeline():
       """Pipeline commands"""
       pass
   
   @pipeline.command()
   def classify(...):
       """Classify question"""
       pass
   ```

2. **Add backward compatibility aliases**
   ```python
   # Old: vbagent classify
   # New: vbagent pipeline classify
   # Alias: vbagent classify -> vbagent pipeline classify
   ```

3. **Deprecation period** (6 months)
   - Both old and new commands work
   - Old commands show deprecation warning
   - Documentation shows new commands

4. **Remove old commands** after deprecation period

### Phase 3: Enhanced Help System
**Timeline**: 1 week  
**Effort**: Low

1. **Standardize help templates**
2. **Add "See also" sections**
3. **Add usage examples for all commands**
4. **Add subject-specific examples**

## Migration Strategy

### Backward Compatibility Approach

```python
# In main.py
@click.group()
def main():
    pass

# New grouped structure
@main.group()
def pipeline():
    """Pipeline commands"""
    pass

@pipeline.command()
def classify(...):
    """Classify question"""
    pass

# Backward compatibility alias
@main.command(hidden=True)  # Hide from help
def classify_old(...):
    """Deprecated: Use 'vbagent pipeline classify'"""
    click.echo("Warning: 'vbagent classify' is deprecated. Use 'vbagent pipeline classify'")
    # Call new command
    ctx = click.get_current_context()
    ctx.invoke(classify, ...)
```

### User Communication

1. **Changelog entry**
   ```markdown
   ## v0.3.0 - CLI Reorganization
   
   ### Breaking Changes
   - Commands reorganized into logical groups
   - Old flat structure deprecated (still works with warnings)
   
   ### Migration Guide
   - `vbagent classify` → `vbagent pipeline classify`
   - `vbagent tikz` → `vbagent generate tikz`
   - See full migration guide: docs/CLI_MIGRATION.md
   ```

2. **Migration guide document**
3. **Deprecation warnings in CLI**
4. **Updated documentation**



## Comparison: Current vs Proposed

### Current CLI
```bash
# 24 top-level commands (overwhelming)
vbagent --help
  classify, scan, process, batch, tikz, fbd, idea, alternate, 
  variant, convert, check, ref, config, util, metadata, dpp, 
  export, extans, db, screenshot, cache, chat, mcp, init

# Inconsistent options
vbagent classify -i image.png
vbagent scan -i image.png -t existing.tex  # -t means "tex file"
vbagent variant -t problem.tex --type numerical  # -t and --type different!
vbagent tikz -d "description"  # Only command using -d
```

### Proposed CLI (Option A)
```bash
# 6 top-level groups (clear)
vbagent --help
  pipeline, generate, quality, manage, export, interface

# Consistent options
vbagent pipeline classify -i image.png
vbagent pipeline scan -i image.png --reference existing.tex
vbagent generate variant -i problem.tex --variant-type numerical
vbagent generate tikz -i image.png --description "circuit diagram"

# Logical grouping
vbagent pipeline --help
  classify, scan, process, batch

vbagent generate --help
  tikz, fbd, idea, alternate, variant, convert

vbagent manage --help
  cache, ref, config, metadata, db
```

## Benefits Summary

### Standardized Options
✅ Predictable: `-i` always means input, `-o` always means output  
✅ Consistent: Same options work the same way across commands  
✅ Discoverable: Users can guess options based on patterns  
✅ Maintainable: Easier to add new commands following standards  

### Command Grouping
✅ Organized: Related commands grouped together  
✅ Scalable: Easy to add new commands to existing groups  
✅ Discoverable: Users can find commands by category  
✅ Professional: Matches industry standards (git, docker, kubectl)  

### Better UX
✅ Less overwhelming: 6 groups vs 24 commands  
✅ Clearer purpose: Group names indicate functionality  
✅ Easier learning: Logical structure aids understanding  
✅ Tab completion: Groups make completion more useful  

## Recommendation

**Implement in 2 phases**:

1. **Phase 1 (Immediate)**: Standardize options with aliases
   - Non-breaking
   - Immediate UX improvement
   - Foundation for Phase 2

2. **Phase 2 (Next major version)**: Introduce command groups
   - Breaking change (with compatibility layer)
   - Significant UX improvement
   - Long-term maintainability

**Recommended Structure**: Option A (Hierarchical Groups)
- Most organized
- Best scalability
- Industry standard pattern
- Clear mental model

## Next Steps

1. Review and approve proposed structure
2. Create detailed migration plan
3. Implement Phase 1 (option standardization)
4. Test with users
5. Implement Phase 2 (command grouping)
6. Deprecation period
7. Remove old structure

**Estimated Total Effort**: 4-6 weeks  
**Impact**: High - Significantly improved UX  
**Risk**: Medium - Breaking changes require careful migration  
