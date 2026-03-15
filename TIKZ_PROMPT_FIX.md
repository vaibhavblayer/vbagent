# TikZ Prompt Fix: No Problem Text in Diagrams

## Problem

Occasionally (1 in 10-20 problems), the TikZ agent includes problem text, headings, and question statements inside the TikZ code as nodes, when it should only generate the diagram itself.

### Example of Wrong Output

```latex
\begin{tikzpicture}
% ❌ WRONG - Includes problem text
\node[problem] at (0,4.3) {\textsc{Problem 188}};
\node[title] at (2.8,4.33){From the following enthalpies values, determine resonance energy...};

% Diagram code
\schemestart
\chemfig{benzene}
\arrow{->}
\chemfig{cyclohexane}
\schemestop
\end{tikzpicture}
```

### What Should Happen

- **Scanner agent**: Extracts problem text, question, options, solution
- **TikZ agent**: Generates ONLY the diagram code

### Example of Correct Output

```latex
\begin{tikzpicture}
% ✅ CORRECT - Only diagram code
\schemestart
\chemfig{benzene}
\arrow{->}
\chemfig{cyclohexane}
\schemestop
\end{tikzpicture}
```

## Root Cause

The TikZ agent prompts didn't explicitly forbid including problem text, so occasionally the model would include it, especially when:
- The problem has a complex layout
- The diagram is part of a larger problem statement
- The model tries to be "helpful" by including context

## Solution

Added explicit instructions to ALL diagram prompts forbidding problem text inclusion.

### Files Modified

1. `vbagent/prompts/diagram/tikz.py` - Generic TikZ prompt
2. `vbagent/prompts/diagram/chemistry/reaction_mechanism.py` - Reaction schemes
3. `vbagent/prompts/diagram/chemistry/orbital.py` - Orbital diagrams

### Instructions Added

```markdown
## CRITICAL: What NOT to Include

**DO NOT include:**
- Problem text or question statements
- Problem numbers or headings (e.g., "Problem 188", "\textsc{Problem}")
- Instructions or explanatory text
- Options text (A, B, C, D) - only the diagrams
- Solution text or answers
- Any \item commands
- Document structure
- Explanatory text nodes (e.g., \node[problem], \node[title], \node[note])

**ONLY include:**
- The TikZ/chemfig diagram code itself
- Diagram elements only (structures, arrows, labels)
```

## Impact

### Before
- 1 in 10-20 problems had problem text in TikZ code
- Required manual cleanup
- Inconsistent output

### After
- Explicit instructions prevent this issue
- Consistent diagram-only output
- Clear separation of concerns:
  - Scanner → Problem text
  - TikZ → Diagram only

## Testing

Test with problems that previously had this issue:
1. Chemistry reaction schemes with complex layouts
2. Physics problems with multiple diagrams
3. Problems with headings and numbered sections

Expected: TikZ code contains ONLY diagram elements, no text nodes.

## Examples

### Chemistry Reaction Scheme

**Wrong (before fix):**
```latex
\begin{tikzpicture}
\node[problem] at (0,4.3) {\textsc{Problem 188}};
\node[title] at (2.8,4.33){From the following...};
\schemestart
\chemfig{C6H6}
\arrow{->}
\chemfig{C6H12}
\schemestop
\end{tikzpicture}
```

**Correct (after fix):**
```latex
\begin{tikzpicture}
\schemestart
\chemfig{C6H6}
\arrow{->}
\chemfig{C6H12}
\schemestop
\end{tikzpicture}
```

### Physics Circuit Diagram

**Wrong:**
```latex
\begin{tikzpicture}
\node[problem] at (0,5) {Problem 42: Find the current...};
\draw (0,0) to[R=$4\Omega$] (2,0);
\end{tikzpicture}
```

**Correct:**
```latex
\begin{tikzpicture}
\draw (0,0) to[R=$4\Omega$] (2,0);
\end{tikzpicture}
```

## Related Prompts

The same fix should be applied to all diagram generation prompts:

### Already Fixed
- ✅ `tikz.py` - Generic TikZ
- ✅ `reaction_mechanism.py` - Chemistry reactions
- ✅ `orbital.py` - Orbital diagrams

### Should Also Have This (if not already)
- `energy_diagram.py` - Energy diagrams
- `organic_structure.py` - Organic structures
- `lewis_structure.py` - Lewis structures
- `chemical_equation.py` - Chemical equations
- All physics diagram prompts (FBD, circuit, graph, optics)
- All mathematics diagram prompts (function_graph, venn_diagram, etc.)

## Verification

To verify the fix is working:

```bash
# Process a problem
vbagent process -i problem.png

# Check the generated TikZ
cat agentic/tikz/problem_1.tex

# Should NOT contain:
# - \node[problem]
# - \node[title]
# - \node[note]
# - Problem text
# - Question statements

# Should ONLY contain:
# - \begin{tikzpicture}
# - Diagram elements
# - \end{tikzpicture}
```

## Summary

Added explicit instructions to diagram prompts to prevent inclusion of problem text, headings, and explanatory nodes in TikZ code. This ensures clean separation between:
- **Scanner**: Extracts all text (problem, solution, options)
- **TikZ**: Generates only diagram code

The fix addresses the occasional issue (1 in 10-20 problems) where TikZ code incorrectly included problem text as nodes.
