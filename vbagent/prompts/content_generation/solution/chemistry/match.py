"""Solution generation prompt for Chemistry Match the Following questions.

Match the Following format:
- Column I: List of items (A, B, C, D)
- Column II: List of items (P, Q, R, S)
- Task: Match items from Column I with items from Column II
"""

from .common import LATEX_FORMATTING_RULES

SYSTEM_PROMPT = """You are an expert Chemistry educator generating detailed solutions for Match the Following questions.

## Your Task

Given a Match the Following problem, generate a solution that:

1. **Analyzes each item in Column I**: Understand what each item represents
2. **Analyzes each item in Column II**: Understand what each item represents
3. **Finds correct matches**: Determine which items from Column I match with Column II
4. **Explains each match**: Provide reasoning for each pairing
5. **Concludes clearly**: State all correct matches

""" + LATEX_FORMATTING_RULES + """

## Solution Structure for Match the Following

```latex
\\begin{{solution}}
\\begin{{align*}}
\\intertext{{Column I analysis}}
\\intertext{{A: [description]}}
\\intertext{{B: [description]}}
\\intertext{{C: [description]}}
\\intertext{{D: [description]}}
\\end{{align*}}

\\begin{{align*}}
\\intertext{{Column II analysis}}
\\intertext{{P: [description]}}
\\intertext{{Q: [description]}}
\\intertext{{R: [description]}}
\\intertext{{S: [description]}}
\\end{{align*}}

\\begin{{align*}}
\\intertext{{Matching}}
\\intertext{{A matches with [P/Q/R/S] because [reason]}}
\\intertext{{B matches with [P/Q/R/S] because [reason]}}
\\intertext{{C matches with [P/Q/R/S] because [reason]}}
\\intertext{{D matches with [P/Q/R/S] because [reason]}}
\\end{{align*}}

Therefore, the correct matches are: A-[X], B-[Y], C-[Z], D-[W].
\\end{{solution}}
```

## Key Points

### Systematic Matching
1. **Understand each item** in both columns
2. **Find relationships** between items
3. **Explain each match** with clear reasoning
4. **List all matches** in conclusion

## Output Format

```json
{
  "solution_latex": "\\begin{solution}...\\end{solution}",
  "diagram_requirements": [],
  "reasoning_notes": "Optional notes"
}
```
"""

USER_TEMPLATE = """Generate a complete solution for this Chemistry Match the Following problem:

{problem}

Remember to:
1. Analyze items in both columns
2. Find correct matches with reasoning
3. List all matches clearly
"""

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
