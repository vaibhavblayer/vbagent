"""Match-the-following question scanner prompt for biology."""

from vbagent.prompts.latex_style import solution_style_rules

from .common import DIAGRAM_PLACEHOLDER
from .._shared import (
    MATCH_OPTION_FORMAT_RULES,
    MATCH_TABLE_DIAGRAM_RULES,
    MCQ_ANSWER_FORMAT_RULES,
)

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image and extract a biology matching-type question. Format in LaTeX with the question in `\item`, then the matching table, then options in a tasks environment, then the solution.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do not include any preamble, `\documentclass`, `\begin{document}`, or extra commentary.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Every word, symbol, and detail from the image MUST be included in full.

---

## Required LaTeX Structure

1.  **Problem Statement (`\item ...`)**
    * Begin immediately with `\item` followed by the actual problem text.
    * Extract the exact question text from the image.
    * Italicise scientific names: `\textit{Homo sapiens}`, `\textit{E. coli}`.
    * Bold key biological terms: `\textbf{mitosis}`, `\textbf{photosynthesis}`.
    * Do **not** include exam or year metadata (e.g., `NEET[2022]`, `[2021]`).
    * Do **not** include example/exercise numbering prefixes.

2.  **Diagram (Optional)**
""" + DIAGRAM_PLACEHOLDER + MATCH_TABLE_DIAGRAM_RULES + r"""

3.  **Matching Table**
    * Use a table environment with appropriate column widths.
    * Format columns clearly with Column I and Column II headers (or List I / List II).
    * Use `\renewcommand{\arraystretch}{2}` for better spacing.

4.  **Options (`\begin{tasks}(2) ... \end{tasks}`)**
    * Provide matching combinations using `\task`.
    * Mark the correct answer by appending ` \ans` to the correct option.

5.  **Solution (`\begin{solution} ... \end{solution}`)**
    * Use an `align*` environment inside the solution.
    * Explain the matching logic step by step using `\intertext{}`.
    * End with the actual lowercase option letter, for example "Therefore, the correct option is (a)."

---

## Example Structure

```latex
\item Match Column I (organisms) with Column II (their characteristics).

\begin{center}
    \renewcommand{\arraystretch}{2}
    \begin{tabular}{@{}p{0.1\textwidth}p{0.3\textwidth}|p{0.1\textwidth}p{0.4\textwidth}@{}}
    \hline
    & \textbf{Column-I} & & \textbf{Column-II} \\
    \hline
    (a) & \textit{Plasmodium} & (p) & Nitrogen fixation \\
    (b) & \textit{Rhizobium} & (q) & Causes malaria \\
    (c) & \textit{Lactobacillus} & (r) & Curd formation \\
    (d) & \textit{Penicillium} & (s) & Antibiotic production \\
    \hline
    \end{tabular}
\end{center}

\begin{tasks}(2)
    \task $\mathrm{a\rightarrow q,\ b\rightarrow p,\ c\rightarrow r,\ d\rightarrow s}$ \ans
    \task $\mathrm{a\rightarrow p,\ b\rightarrow q,\ c\rightarrow s,\ d\rightarrow r}$
    \task $\mathrm{a\rightarrow r,\ b\rightarrow s,\ c\rightarrow p,\ d\rightarrow q}$
    \task $\mathrm{a\rightarrow s,\ b\rightarrow r,\ c\rightarrow q,\ d\rightarrow p}$
\end{tasks}

\begin{solution}
    \begin{align*}
        \intertext{Analyze each organism:}
        \intertext{(a) \textit{Plasmodium} is the causative agent of malaria $\rightarrow$ (q)}
        \intertext{(b) \textit{Rhizobium} is a nitrogen-fixing bacterium found in root nodules $\rightarrow$ (p)}
        \intertext{(c) \textit{Lactobacillus} is used in curd formation $\rightarrow$ (r)}
        \intertext{(d) \textit{Penicillium} produces the antibiotic penicillin $\rightarrow$ (s)}
        \intertext{Therefore, the correct option is (a).}
    \end{align*}
\end{solution}
```

---

## Strict LaTeX Rules

* Inline math: always `$...$`.
* Scientific names in `\textit{}`.
* Key biological terms in `\textbf{}`.
* No blank lines inside `align*` environment.

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
""" + MATCH_OPTION_FORMAT_RULES + MCQ_ANSWER_FORMAT_RULES

SYSTEM_PROMPT += solution_style_rules("biology")

USER_TEMPLATE = "Extract LaTeX from this biology match-the-following question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
