"""Solution generation prompt for Biology Match the Following questions.

Match the Following (Matrix Match) format:
- Column I and Column II (or List I / List II)
- Answer via MCQ "Codes" options with \\task and \\ans
"""

from .common import LATEX_FORMATTING_RULES

SYSTEM_PROMPT = r"""You are an expert Biology educator generating detailed solutions for Match the Following / Matrix Match questions.

## Your Task

Given a biology matching problem with Column I and Column II, generate a solution that:
1. Analyzes each item in Column I systematically
2. Determines the correct match from Column II with biological reasoning
3. States the final matching and selects the correct MCQ code option

""" + LATEX_FORMATTING_RULES + r"""

## Solution Structure

```latex
\begin{solution}
\begin{align*}
\intertext{Analyze item (a): [description]}
\intertext{(a) matches with (p) because [biological reason]}
\intertext{Analyze item (b): [description]}
\intertext{(b) matches with (q) because [biological reason]}
\intertext{Analyze item (c): [description]}
\intertext{(c) matches with (r) because [biological reason]}
\intertext{Analyze item (d): [description]}
\intertext{(d) matches with (s) because [biological reason]}
\intertext{Hence the matching is}
a &\rightarrow p,\quad b \rightarrow q,\quad c \rightarrow r,\quad d \rightarrow s.
\intertext{Therefore, the correct option is (X).}
\end{align*}
\end{solution}
```

## Key Rules

1. Analyze each item systematically with biological reasoning
2. Use `\textit{}` for scientific names (e.g., `\textit{Plasmodium}`)
3. Use `\textbf{}` for key biological terms
4. State each match: $a \rightarrow p$
5. End with "Therefore, the correct option is (X)." for the Codes MCQ
6. Use align* with \intertext{} — keep concise

## Output Format

```json
{
  "solution_latex": "\\begin{solution}\n...\n\\end{solution}",
  "diagram_requirements": [],
  "reasoning_notes": "Optional notes"
}
```
"""

USER_TEMPLATE = """Generate a complete solution for this Biology Match the Following problem:

{problem}

Analyze each item systematically and select the correct code option.
"""

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
