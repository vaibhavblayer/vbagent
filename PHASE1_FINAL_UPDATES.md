# Phase 1: Final Updates - Remaining Commands

## Completed So Far ✅
1. classify.py ✅
2. scan.py ✅
3. process.py ✅
4. main.py ✅

## Remaining Commands - Quick Reference

### Pattern to Apply to All

**1. Update module docstring:**
```python
# OLD: "physics question"
# NEW: "question" or "multi-subject question"
```

**2. Standardize input option:**
```python
# OLD
@click.option("-i", "--image", ...)
@click.option("-t", "--tex", ...)

# NEW
@click.option("-i", "--input", "--image", "--tex", "input_path", ...)
```

**3. Add verbose option:**
```python
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
```

**4. Add deprecation warnings:**
```python
import sys
if '--image' in sys.argv:
    console.print("[yellow]Note:[/yellow] --image is deprecated, use --input", style="dim")
```

**5. Update help text:**
- Remove "physics" references
- Add multi-subject examples
- Add "See Also" section

## Specific Updates Needed

### idea.py
```python
# Current
@click.option("-t", "--tex", ...)

# Update to
@click.option("-i", "--input", "--tex", "input_path", ...)

# Help text
"""Extract key concepts and problem-solving ideas.

Works across physics, chemistry, and mathematics problems.

Examples:
    vbagent idea -i problem.tex
    vbagent idea -i chemistry/problem.tex -o ideas.json
"""
```

### alternate.py
```python
# Current
@click.option("-t", "--tex", ...)

# Update to
@click.option("-i", "--input", "--tex", "input_path", ...)

# Help text
"""Generate alternative solution methods.

Supports multiple subjects with subject-specific approaches.

Examples:
    vbagent alternate -i problem.tex
    vbagent alternate -i chemistry/problem.tex -n 2
"""
```

### variant.py
```python
# Current
@click.option("-i", "--image", ...)
@click.option("-t", "--tex", ...)
@click.option("--type", ...)

# Update to
@click.option("-i", "--input", "--image", "--tex", "input_path", ...)
@click.option("--variant-type", ...)  # More specific than --type

# Help text
"""Generate problem variants.

Creates variations across numerical, contextual, and conceptual dimensions.

Examples:
    vbagent variant -i problem.tex --variant-type numerical
    vbagent variant -i chemistry/problem.tex --variant-type context
"""
```

### convert.py
```python
# Current
@click.option("-i", "--image", ...)
@click.option("-t", "--tex", ...)

# Update to
@click.option("-i", "--input", "--image", "--tex", "input_path", ...)

# Help text
"""Convert questions between different formats.

Supports conversion across all subjects.

Examples:
    vbagent convert -i problem.tex --to mcq_sc
    vbagent convert -i chemistry/problem.tex --from subjective --to mcq_mc
"""
```

### tikz.py
```python
# Current
@click.option("-i", "--image", ...)
@click.option("-d", "--description", ...)
@click.option("-t", "--tex", ...)

# Update to
@click.option("-i", "--input", "--image", "input_path", ...)
@click.option("--description", ...)  # Remove -d short form
@click.option("--reference", ...)  # Instead of -t

# Help text
"""Generate TikZ code for diagrams.

Supports subject-specific diagram types:
- Physics: FBD, circuits, optics, graphs
- Chemistry: Organic structures, energy diagrams, orbitals
- Mathematics: Function graphs, geometry, Venn diagrams

Examples:
    vbagent tikz -i diagram.png
    vbagent tikz -i chemistry/molecule.png
    vbagent tikz --description "benzene ring"
"""
```

### fbd.py (Keep physics-specific)
```python
# This is physics-specific, minimal changes
# Just add -v/--verbose
# Help text can mention it's physics-specific
"""Generate Free Body Diagram TikZ code.

Physics-specific command for force diagrams.

Examples:
    vbagent fbd -i diagram.png
    vbagent fbd --description "block on incline"
"""
```

### batch.py
```python
# Already uses -i for images-dir, keep as is
# Just update help text to be subject-agnostic

# Help text
"""Batch processing commands with resume capability.

Process multiple question images across all subjects.

Examples:
    vbagent batch init -i ./images
    vbagent batch continue
"""
```

### check.py
```python
# Minimal changes
# Add -v/--verbose
# Update help text

# Help text
"""QA review with interactive approval.

Review and approve processed questions across all subjects.
"""
```

### chat.py
```python
# Update system message
# OLD: "physics question processing system"
# NEW: "multi-subject question processing system"
```

## Testing Checklist

After all updates:
- [ ] All commands show `--help` correctly
- [ ] Old options still work with warnings
- [ ] New options work
- [ ] No breaking changes
- [ ] Multi-subject examples present
- [ ] "See Also" sections added

## Completion Criteria

✅ All 13 commands updated
✅ Consistent option patterns
✅ Subject-agnostic language
✅ Multi-subject examples
✅ Backward compatibility
✅ Deprecation warnings
✅ Tests pass

## Time Estimate

- idea.py: 10 min
- alternate.py: 10 min
- variant.py: 15 min
- convert.py: 10 min
- tikz.py: 15 min
- fbd.py: 5 min
- batch.py: 10 min
- check.py: 5 min
- chat.py: 5 min

**Total**: ~85 minutes

## Next Steps After Completion

1. Run full test suite
2. Update README with new examples
3. Create CHANGELOG entry
4. Update documentation
5. Prepare for Phase 2 (command grouping)
