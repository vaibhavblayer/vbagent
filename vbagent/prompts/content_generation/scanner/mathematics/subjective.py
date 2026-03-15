"""Subjective question scanner prompt."""

from .common import DIAGRAM_PLACEHOLDER

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX **subjective** mathematics question based **exactly** on the image. Include a detailed, step-by-step solution and, if applicable, a simplified TikZ diagram.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Do NOT abbreviate, summarize, or truncate ANY part of the question or solution. Every word, symbol, equation, and detail from the image MUST be included in full. If the content is long, output ALL of it without any shortcuts like "..." or "[continued]".

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output *immediately* with `\item` followed by the actual problem text.
    *   Extract the **exact** mathematics question text from the image **without any modifications or additions**.
    *   Use inline math mode `$ ... $` for all mathematical symbols and variables as they appear in the image.
    *   Do **not** include exam or year metadata (e.g., `NEET[2022]`, `JEE 2019`, `IIT-JEE 2020`, `(2023)`, `[2021]`).
    *   Do **not** include example/exercise numbering prefixes (e.g., `Example 25.4`, `Ex. 3.2`, `Problem 12`, `Q.5`). Start directly with the actual problem text.
    *   **Multi-part sub-questions:** If the problem has sub-parts like (a), (b), (c), use `\begin{enumerate}` with `\item` for each sub-part instead of manual `(a) ...\\` formatting. Add `\renewcommand{\labelenumi}{(\alph{enumi})}` before enumerate if (a), (b), (c) labels are needed. Example:
        ```latex
        \item In the circuit shown, find
        \renewcommand{\labelenumi}{(\alph{enumi})}
        \begin{enumerate}
            \item the current through the resistor.
            \item the voltage across the capacitor.
        \end{enumerate}
        ```

2.  **Diagram (Optional, place immediately after `\item` line if used)**
""" + DIAGRAM_PLACEHOLDER + r"""

3.  **Solution (`\begin{solution} ... \end{solution}`)**
    *   Use an `align*` environment directly inside the `solution` environment.
    *   Show key conceptual steps and reasoning for solving the problem based on the extracted text.
    *   Use `\intertext{}` for brief text explanations *between* equation lines. Ensure any math within `\intertext{}` uses `$ ... $`.
    *   Keep the solution concise and elegant. Omit trivial intermediate algebra where appropriate while ensuring logical flow.
    *   Align equations using `&`. Use `\\` to end lines.
    *   Keep **only one step** in every line of calculation.
    *   **Strictly forbidden:** Do **not** leave any blank lines inside the `align*` environment.

---

## Strict LaTeX Formatting Rules

Adhere to these rules meticulously:

*   **Math Mode:** Use `$ ... $` for *all* inline math.
*   **Macros:** Always use `{}`: `\vec{a}`, `\frac{a}{b}`.
*   **Vectors:** Use `\vec{a}` for generic vectors and `\hat{i}`, `\hat{j}`, `\hat{k}` for unit vectors.
*   **Fractions:** Use `\frac{a}{b}`. **Do not use** `\tfrac`.
*   **Parentheses/Brackets:** Use `\left( ... \right)`, `\left[ ... \right]`, `\left| ... \right|`. **Do not use** `\bigl`, `\bigr`, `\Bigl`, `\Bigr`, etc.

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

USER_TEMPLATE = "Extract LaTeX from this mathematics question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
