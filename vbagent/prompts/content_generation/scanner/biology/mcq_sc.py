"""MCQ single-correct question scanner prompt for biology."""

from .common import (
    DIAGRAM_PLACEHOLDER,
    LATEX_FORMATTING_RULES,
    OPTIONS_WITH_DIAGRAMS,
)

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX multiple-choice biology question based **exactly** on the image, assuming it has a **single correct answer**. Include a step-by-step solution (which identifies the correct option) and, if applicable, a minimal TikZ diagram.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Do NOT abbreviate, summarize, or truncate ANY part of the question, options, or solution. Every word, symbol, and detail from the image MUST be included in full.

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output immediately with `\item`.
    *   Extract the exact biology question text from the image without any modifications.
    *   Use inline math mode `$ ... $` for mathematical symbols and variables.
    *   Italicise scientific names: `\textit{Homo sapiens}`, `\textit{E. coli}`.
    *   Bold key biological terms: `\textbf{mitosis}`, `\textbf{photosynthesis}`.
    *   Do not include exam or year metadata (e.g., `NEET[2022]`, `[2021]`).
    *   Do **not** include example/exercise numbering prefixes. Start directly with the actual problem text.

2.  **Diagram (Optional, place immediately after `\item` line if used)**
""" + DIAGRAM_PLACEHOLDER + r"""

3.  **Multiple Choice Options (`\begin{tasks}(c) ... \end{tasks}`)**
    *   Column rule: choose columns by option style.
        - Use `\begin{tasks}(2)` for short options (single words or short phrases).
        - Use `\begin{tasks}(1)` for statement-based or long textual options.
    *   Extract the exact option text from the image without any modifications.
    *   Provide the options using `\task`.
    *   Based on your analysis in the solution step, mark the single correct answer by appending ` \ans` to the end of its corresponding `\task` line.

""" + OPTIONS_WITH_DIAGRAMS + r"""

4.  **Solution (`\begin{solution} ... \end{solution}`)**
    *   Use an `align*` environment directly inside the `solution` environment.
    *   Show key conceptual reasoning for solving the problem.
    *   Use `\intertext{}` for brief text explanations between lines. Wrap only math in `$...$` inside `\intertext{}`.
    *   Evaluate the options to identify the single correct answer. Explain why it is correct and briefly why others are incorrect.
    *   State the final correct option by letter: "Therefore, the correct option is (c)."
    *   Keep the solution concise. Show conceptual steps clearly.
    *   Strictly forbidden: Do not leave any blank lines inside the `align*` environment.

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

USER_TEMPLATE = "Extract LaTeX from this biology question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
