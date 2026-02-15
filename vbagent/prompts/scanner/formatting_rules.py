"""Shared formatting rules for all scanner prompts.

This module contains LaTeX formatting rules, TikZ guidelines, and other
formatting standards used across problem and solution scanners.
"""

# Re-export from common.py for backward compatibility
from vbagent.prompts.scanner.common import (
    TIKZ_GUIDELINES,
    TIKZ_GUIDELINES_SHORT,
    LATEX_FORMATTING_RULES,
    PGFPLOTS_EXAMPLE,
    OPTIONS_WITH_DIAGRAMS,
    DIAGRAM_PLACEHOLDER,
)

# Solution-specific formatting rules
SOLUTION_FORMATTING_RULES = r"""
## Solution Formatting Rules (CRITICAL)

1. **Use `align*` environment** directly inside the `solution` environment
2. **Use `\intertext{}`** for brief text explanations *between* equation lines
   - Any math within `\intertext{}` must use `$ ... $`
   - Do NOT nest `\text{...}` inside `\intertext{}`
3. **Align equations using `&`** at the `=` sign and use `\\` to end lines
4. **Keep only one step** in every line of calculation
5. **NO blank lines** inside the `align*` environment
6. **Keep solution concise** - show key conceptual steps, omit trivial algebra
7. **For diagrams inside solution:** wrap in `\begin{center}...\end{center}`
8. **Multiple `align*` blocks** only when diagram/table interrupts the flow

## Solution Structure Patterns

**Pattern 1: Simple (one align* block)**
```latex
\begin{solution}
\begin{align*}
\intertext{[Brief reasoning]}
[equation] &= [result] \\
[step] &= [result] \\
[final] &= \boxed{[answer]}
\end{align*}
\end{solution}
```

**Pattern 2: With diagram (multiple blocks)**
```latex
\begin{solution}
\begin{align*}
\intertext{[Initial reasoning]}
[equation] &= [result] \\
[step] &= [result]
\end{align*}

\begin{center}
\begin{tikzpicture}
[diagram code]
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{[Continue reasoning]}
[equation] &= [result] \\
[final] &= \boxed{[answer]}
\end{align*}
\end{solution}
```

**Pattern 3: MCQ solution**
```latex
\begin{solution}
\begin{align*}
\intertext{[Brief analysis]}
[key equation] &= [result] \\
[comparison] &= [value]
\end{align*}

Therefore, the correct option is (c).
\end{solution}
```
"""

# Problem-specific formatting rules
PROBLEM_FORMATTING_RULES = r"""
## Problem Formatting Rules

1. **Start with `\item`** - Begin output immediately with `\item`
2. **Extract exact text** - Do not modify or add to the problem statement
3. **Use inline math** - `$ ... $` for all mathematical symbols
4. **Diagram placeholder** - Use `\input{diagram}` if diagram present
5. **MCQ options** - Use `\begin{tasks}(2)...\end{tasks}` environment
6. **Mark correct answer** - Add `\ans` after correct option text
"""

__all__ = [
    # From common.py
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "PGFPLOTS_EXAMPLE",
    "OPTIONS_WITH_DIAGRAMS",
    "DIAGRAM_PLACEHOLDER",
    # New
    "SOLUTION_FORMATTING_RULES",
    "PROBLEM_FORMATTING_RULES",
]
