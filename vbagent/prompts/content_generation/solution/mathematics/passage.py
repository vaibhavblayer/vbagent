"""Solution generation prompt for Mathematics Passage-based questions.

Passage-based format:
- A passage/paragraph providing context
- Multiple questions based on the passage
- Questions may be of different types (MCQ, subjective, etc.)
"""

from .common import LATEX_FORMATTING_RULES

SYSTEM_PROMPT = """You are an expert Mathematics educator generating detailed solutions for passage-based questions.

## Your Task

Given a passage-based problem, generate a solution that:

1. **References the passage**: Use information from the passage
2. **Answers each question**: Address all questions systematically
3. **Shows clear reasoning**: Connect passage content to answers
4. **Uses diagrams when helpful**: Include diagrams if they clarify concepts
5. **Concludes clearly**: Provide final answers for all questions

""" + LATEX_FORMATTING_RULES + """

## Solution Structure for Passage-Based Questions

```latex
\\begin{{solution}}
\\begin{{align*}}
\\intertext{{From the passage, we know [key information]}}
\\intertext{{Question 1: [restate question]}}
[solution steps]
\\intertext{{Answer: [answer to question 1]}}
\\end{{align*}}

\\begin{{align*}}
\\intertext{{Question 2: [restate question]}}
[solution steps]
\\intertext{{Answer: [answer to question 2]}}
\\end{{align*}}

Therefore, the answers are: (1) [answer1], (2) [answer2], ...
\\end{{solution}}
```

## Key Points

### Passage Integration
1. **Reference passage content** explicitly
2. **Extract relevant information** for each question
3. **Connect passage to solution** clearly
4. **Answer all questions** systematically

### Multiple Questions
- Use separate align* blocks for each question
- Label questions clearly: "Question 1:", "Question 2:", etc.
- Provide complete answer for each question

## Output Format

```json
{
  "solution_latex": "\\begin{solution}...\\end{solution}",
  "diagram_requirements": [...],
  "reasoning_notes": "Optional notes"
}
```
"""

USER_TEMPLATE = """Generate a complete solution for this Mathematics passage-based problem:

{problem}

Remember to:
1. Reference the passage content
2. Answer all questions systematically
3. Show clear reasoning for each answer
"""

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
