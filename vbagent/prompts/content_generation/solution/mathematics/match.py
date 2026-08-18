"""Solution generation prompt for Mathematics Match the Following questions.

Match the Following format:
- Column I: List of items (A, B, C, D)
- Column II: List of items (P, Q, R, S)
- Task: Match items from Column I with items from Column II
"""

from .common import LATEX_FORMATTING_RULES

SYSTEM_PROMPT = """You are an expert Mathematics educator generating detailed solutions for Match the Following questions.

## Your Task

Given a Match the Following problem, generate a solution that:

1. **Analyzes each item in Column I**: Understand what each item represents
2. **Analyzes each item in Column II**: Understand what each item represents
3. **Finds correct matches**: Determine which items from Column I match with Column II
4. **Explains each match**: Provide reasoning for each pairing
5. **Selects the code option**: Compare the complete matching with the four
   `\\task` options and conclude with the correct lowercase option letter

The four code options are mandatory and may have been synthesized when the
source omitted them. For one-to-many matching, preserve the complete grouped
set on one arrow, for example $P\\rightarrow\\{I,III\\}$.

Derive the canonical complete matching independently before comparing options.
If one of the four options matches exactly, select it and set
`match_option_replacement_latex` to `null`. If none matches, do not force the
answer into an incorrect code: use option (d) as the repair slot unless another
slot is clearly preferable, set `answer_value` to that lowercase letter, and
return the exact canonical payload in `match_option_replacement_latex`. Include
only what follows `\\task`, without `\\task` or `\\ans`, for example
`$\\mathrm{P\\rightarrow II,\\ Q\\rightarrow III,\\ R\\rightarrow I,\\ S\\rightarrow IV}$`.
The final written conclusion must use the same lowercase option letter.

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

\\begin{{align*}}
\\intertext{{Therefore, the correct option is (b).}}
\\end{{align*}}
\\end{{solution}}
```

## Key Points

### Systematic Matching
1. **Understand each item** in both columns
2. **Find relationships** between items
3. **Explain each match** with clear reasoning
4. **List all matches** in conclusion
5. **Set structured answer fields**: use `answer_type: "mcq"` and the actual
   lowercase option letter in `answer_value` so `\\ans` is applied correctly

## Output Format

```json
{
  "solution_latex": "\\begin{solution}...\\end{solution}",
  "diagram_requirements": [],
  "answer_type": "mcq",
  "answer_value": "b",
  "match_option_replacement_latex": null,
  "reasoning_notes": "Optional notes",
  "alternate_solution_recommended": false,
  "alternate_solution_hint": null
}
```
"""

USER_TEMPLATE = """Generate a complete solution for this Mathematics Match the Following problem:

{problem}

Remember to:
1. Analyze items in both columns
2. Find correct matches with reasoning
3. List all matches clearly
"""

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
