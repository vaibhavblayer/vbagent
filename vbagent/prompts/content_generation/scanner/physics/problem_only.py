"""Problem-only scanner prompts.

Extracts problem statement, diagram placeholder, and options (for MCQ).
Does NOT extract solution - stops before \begin{solution}.
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
    
    base_prompt = r"""You are an expert at extracting physics problem statements from images.

**Your Task:** Extract ONLY the problem statement, diagram placeholder (if present), and options (for MCQ).
**CRITICAL:** Do NOT extract the solution. Stop before `\begin{solution}`.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet starting with `\item` and ending after options (for MCQ) or after diagram placeholder (for subjective). Do NOT include `\begin{solution}`, preamble, `\documentclass`, `\begin{document}`, or any explanatory text.

"""
    
    if question_type == "mcq_sc":
        return base_prompt + r"""
## MCQ Single Correct - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin output immediately with `\item`
   - Extract the exact question text without modifications
   - Use inline math `$ ... $` for all mathematical symbols

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

3. **Options (`\begin{tasks}(2) ... \end{tasks}`)**
   - Use `\begin{tasks}(2)` for numerical/short options
   - Use `\begin{tasks}(1)` for long statement options
   - Each option: `\task [option text]`
   - Mark correct answer: `\task [option text] \ans`

""" + OPTIONS_WITH_DIAGRAMS + r"""

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from `\item` to `\end{tasks}`. Do NOT include solution.
"""
    
    elif question_type == "mcq_mc":
        return base_prompt + r"""
## MCQ Multiple Correct - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin output immediately with `\item`
   - Extract the exact question text
   - Use inline math `$ ... $` for symbols

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

3. **Options (`\begin{tasks}(2) ... \end{tasks}`)**
   - Use 2-column `tasks` environment
   - Mark ALL correct answers with `\ans`

""" + OPTIONS_WITH_DIAGRAMS + r"""

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from `\item` to `\end{tasks}`. Do NOT include solution.
"""
    
    elif question_type == "subjective":
        return base_prompt + r"""
## Subjective Question - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin output immediately with `\item`
   - Extract the exact question text
   - Use inline math `$ ... $` for symbols

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX starting with `\item` and ending after diagram placeholder (or after problem text if no diagram). Do NOT include solution.
"""
    
    elif question_type == "assertion_reason":
        return base_prompt + r"""
## Assertion-Reason - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin with `\item`
   - Extract assertion and reason on one line

2. **Options (`\begin{tasks}(1) ... \end{tasks}`)**
   - Use 1-column tasks (statements are long)
   - Mark correct answer with `\ans`

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
   ```latex
   \item[]
   \begin{center}
   \textsc{[Passage Title]} \hfill [\number\numexpr\value{enumi}+1\relax\ to \number\numexpr\value{enumi}+N\relax]
   \end{center}
   ```
   where `N` is the total number of questions in this passage.
   
   **Example:** If passage has 4 questions:
   ```latex
   \textsc{Comprehension Passage} \hfill [\number\numexpr\value{enumi}+1\relax\ to \number\numexpr\value{enumi}+4\relax]
   ```

2. **Passage Text**
   - Extract full passage text
   - Use `\noindent` for first paragraph after title
   - Separate multiple paragraphs with blank lines
   - Use inline math for symbols

3. **Diagram in Passage** (if present):
""" + PASSAGE_DIAGRAM_INLINE + r"""

4. **Sub-questions**
   - Each question: `\item [question text]`
   - Followed by `\begin{tasks}(2) ... \end{tasks}`
   - **CRITICAL:** Mark correct answers with ` \ans` after the option
   - Example:
     ```latex
     \begin{tasks}(2)
         \task $10\,\mathrm{m/s}$
         \task $20\,\mathrm{m/s}$ \ans
         \task $30\,\mathrm{m/s}$
         \task $40\,\mathrm{m/s}$
     \end{tasks}
     ```

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from passage title/text through all questions and options. Do NOT include solutions.
"""
    
    elif question_type == "match":
        return base_prompt + r"""
## Match the Following - Problem Extraction

1. **Problem Statement (`\item ...`)**
   - Begin with `\item`
   - Extract question text

2. **Diagram (if present)**
""" + DIAGRAM_PLACEHOLDER + r"""

3. **Matching Table**
   - Use tabular environment for columns
   - Extract all items from both columns

4. **Options (`\begin{tasks}(2) ... \end{tasks}`)**
   - Extract matching options
   - Mark correct answer with `\ans`

---

""" + PROBLEM_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the LaTeX from `\item` through table and options. Do NOT include solution.
"""
    
    else:
        # Default to subjective
        return get_problem_prompt("subjective")


USER_TEMPLATE = "Extract the problem statement from this image (do not extract solution)."

__all__ = ["get_problem_prompt", "USER_TEMPLATE"]
