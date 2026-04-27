"""Problem-only scanner prompts for biology.

Extracts problem statement, diagram placeholder, and options (for MCQ).
Does NOT extract solution - stops before \\begin{solution}.
"""

from .formatting_rules import (
    LATEX_FORMATTING_RULES,
    DIAGRAM_PLACEHOLDER,
    OPTIONS_WITH_DIAGRAMS,
    PROBLEM_FORMATTING_RULES,
    TIKZ_GUIDELINES_SHORT,
)
from .common import PASSAGE_DIAGRAM_INLINE


def get_problem_prompt(question_type: str) -> str:
    """Get problem extraction prompt for specific question type.

    Args:
        question_type: One of: mcq_sc, mcq_mc, subjective, assertion_reason, passage, match

    Returns:
        System prompt for problem extraction
    """

    base_prompt = r"""You are an expert at extracting biology problem statements from images.

**Your Task:** Extract ONLY the problem statement, diagram placeholder (if present), and options (for MCQ).
**CRITICAL:** Do NOT extract the solution. Stop before `\begin{solution}`.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet starting with `\item` and ending after options (for MCQ) or after diagram placeholder (for subjective). Do NOT include `\begin{solution}`, preamble, `\documentclass`, `\begin{document}`, or any explanatory text.

**Biology-specific formatting:**
- Italicise scientific names: `\textit{Homo sapiens}`, `\textit{E. coli}`
- Bold key terms: `\textbf{mitosis}`, `\textbf{photosynthesis}`
- Use `\ce{}` for biological molecules: `\ce{ATP}`, `\ce{CO2}`, `\ce{NADH}`

"""

    if question_type in ("mcq_sc", "mcq_mc"):
        return base_prompt + r"""
## MCQ - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin output immediately with `\item`
   - Extract the exact question text without modifications
   - Use inline math `$ ... $` for mathematical symbols

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

3. **Options (`\begin{tasks}(2) ... \end{tasks}`)**
   - Use `\begin{tasks}(2)` for short options
   - Use `\begin{tasks}(1)` for long statement options
   - Each option: `\task [option text]`
   - Do NOT mark any answer with `\ans` — answer marking is done later by the solution agent

""" + OPTIONS_WITH_DIAGRAMS + r"""

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from `\item` to `\end{tasks}`. Do NOT include solution.
"""

    elif question_type == "assertion_reason":
        return base_prompt + r"""
## Assertion-Reason - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin with `\item`
   - Extract assertion and reason

2. **Options (`\begin{tasks}(1) ... \end{tasks}`)**
   - Use 1-column tasks
   - Do NOT mark any answer with `\ans`

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from `\item` to `\end{tasks}`. Do NOT include solution.
"""

    elif question_type == "passage":
        return base_prompt + r"""
## Passage/Comprehension - Problem Extraction

Extract the passage and all sub-questions with their options.

1. **Passage Title with Question Range**
2. **Passage Text** — extract full passage
3. **Diagram in Passage** (if present):
""" + PASSAGE_DIAGRAM_INLINE + r"""

4. **Sub-questions** — each with `\item` and `\begin{tasks}...\end{tasks}`
   - Do NOT mark any answers with `\ans`

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from passage through all questions and options. Do NOT include solutions.
"""

    else:
        # subjective, match, integer — default
        return base_prompt + r"""
## Subjective/Other - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin output immediately with `\item`
   - Extract the exact question text

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX starting with `\item`. Do NOT include solution.
"""


USER_TEMPLATE = "Extract the problem statement from this biology image (do not extract solution)."

__all__ = ["get_problem_prompt", "USER_TEMPLATE"]
