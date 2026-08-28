"""Match-the-following question scanner prompt."""

from vbagent.prompts.latex_style import solution_style_rules

from .common import DIAGRAM_PLACEHOLDER
from .._shared import (
    MATCH_OPTION_FORMAT_RULES,
    MATCH_TABLE_DIAGRAM_RULES,
    MCQ_ANSWER_FORMAT_RULES,
)

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

Subject: Physics

**Goal:** Analyze the provided image and extract a matching-type question. Format it with the question in `\item`, the matching table (keeping any row diagrams inside their own cells), and the answer codes in a tasks environment.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do not include any preamble, `\documentclass`, `\begin{document}`, or extra commentary.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Do NOT abbreviate, summarize, or truncate ANY part of the question, table entries, options, or solution. Every word, symbol, equation, and detail from the image MUST be included in full. If the content is long, output ALL of it without any shortcuts like "..." or "[continued]".

---

## Required LaTeX Structure

1.  **Problem Statement (`\item ...`)**
    * Begin immediately with `\item` followed by the actual problem text.
    * Extract the exact question text from the image.
    * Do **not** include exam or year metadata (e.g., `NEET[2022]`, `JEE 2019`, `IIT-JEE 2020`, `(2023)`, `[2021]`).
    * Do **not** include example/exercise numbering prefixes (e.g., `Example 25.4`, `Ex. 3.2`, `Problem 12`, `Q.5`). Start directly with the actual problem text.

2.  **Diagram (Optional)**
""" + DIAGRAM_PLACEHOLDER + MATCH_TABLE_DIAGRAM_RULES + r"""

3.  **Matching Table**
    * Use a table environment with appropriate column widths.
    * Format columns clearly with Column I and Column II headers.
    * Use `\renewcommand{\arraystretch}{2}` for better spacing.

4.  **Options (`\begin{tasks}(2) ... \end{tasks}`)**
    * Provide matching combinations using `\task`.
    * Mark the correct answer by appending ` \ans` to the correct option.

5.  **Solution (`\begin{solution} ... \end{solution}`)**
    * Use an `align*` environment inside the solution.
    * Explain the matching logic step by step.
    * Use `\intertext{}` for prose between equations.

---

## Example Structure

```latex
\item This is a sample question for matching type questions. Match column I with column II. 

\begin{center}
    \renewcommand{\arraystretch}{2}
    \begin{tabular}{@{}p{0.1\textwidth}p{0.3\textwidth}|p{0.1\textwidth}p{0.4\textwidth}@{}}
    \hline
    & \textbf{Column-I} & & \textbf{Column-II} \\
    \hline
    (a) & Item A description & (p) & Match P description \\
    (b) & Item B description & (q) & Match Q description \\
    (c) & Item C description & (r) & Match R description \\
    (d) & Item D description & (s) & Match S description \\
    \hline
    \end{tabular}
\end{center}

\begin{tasks}(2)
    \task $\mathrm{a\rightarrow p,\ b\rightarrow q,\ c\rightarrow r,\ d\rightarrow s}$
    \task $\mathrm{a\rightarrow q,\ b\rightarrow p,\ c\rightarrow s,\ d\rightarrow r}$ \ans
    \task $\mathrm{a\rightarrow r,\ b\rightarrow s,\ c\rightarrow p,\ d\rightarrow q}$
    \task $\mathrm{a\rightarrow s,\ b\rightarrow r,\ c\rightarrow q,\ d\rightarrow p}$
\end{tasks}
\begin{solution}
    \begin{align*}
        \intertext{Analyzing each match:}
        \intertext{(a) matches with (q) because...}
        \intertext{(b) matches with (p) because...}
        \intertext{(c) matches with (s) because...}
        \intertext{(d) matches with (r) because...}
        \intertext{Therefore, the correct option is (b).}
    \end{align*}
\end{solution}
```

---

## Strict LaTeX Rules

* Inline math: always `$...$`.
* Macros with braces: `\vec{a}`, `\dfrac{a}{b}`.
* Use `\left(\cdot\right)` for delimiters.
* No blank lines inside `align*` environment.

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
""" + MATCH_OPTION_FORMAT_RULES + MCQ_ANSWER_FORMAT_RULES

SYSTEM_PROMPT += solution_style_rules("physics")

USER_TEMPLATE = "Extract LaTeX from this physics question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
