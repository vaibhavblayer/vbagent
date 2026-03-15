"""Passage/Comprehension question scanner prompt."""

from .common import PASSAGE_DIAGRAM_INLINE

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image and generate a *comprehension-type* LaTeX snippet that contains:
1.  A centred passage title (if any).
2.  The passage text exactly as it appears.
3.  An optional TikZ diagram (placeholder only) if one is present in, or helpful for, the image.
4.  A series of follow-up questions, each with its own multiple-choice options.
5.  **A separate `solution` block placed *immediately after every individual question*** – i.e. the pattern must be:
   ```latex
   \item <Question-1 text>
       <tasks env for options>
   \begin{solution}
       \begin{align*}
           ...steps for Q-1...
       \end{align*}
   \end{solution}

   \item <Question-2 text>
       <tasks env for options>
   \begin{solution}
       ...
   \end{solution}
   ```
   This ensures the reader sees the solution just below each problem statement.

**CRITICAL OUTPUT CONSTRAINT:** Emit *only* the LaTeX snippet starting with the passage title's `center` environment (or the first `\item` if no title) and ending after the final `\end{solution}`. Do **NOT** add any preamble, `\documentclass`, `\begin{document}`, or explanatory comments outside the snippet.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Do NOT abbreviate, summarize, or truncate ANY part of the passage, questions, options, or solutions. Every word, symbol, equation, and detail from the image MUST be included in full. If the content is long, output ALL of it without any shortcuts like "..." or "[continued]".

---

## Detailed LaTeX Structure

1.  **Title with Question Range**
    ```latex
    \item[]
    \begin{center}
        \textsc{<Title from image>} \hfill [\number\numexpr\value{enumi}+1\relax\ to \number\numexpr\value{enumi}+N\relax]
    \end{center}
    ```
    where `N` is the total number of questions in this passage.
    
    **Example:** If passage has 3 questions, use:
    ```latex
    \textsc{Comprehension Passage} \hfill [\number\numexpr\value{enumi}+1\relax\ to \number\numexpr\value{enumi}+3\relax]
    ```
    This will auto-display as `[5 to 7]` if questions are numbered 5, 6, 7.

2.  **Passage Text**
    - Write the paragraph exactly as-is (no surrounding environment)
    - For multi-paragraph passages: separate paragraphs with a blank line
    - Use `\noindent` for the first paragraph after title to avoid indentation

3.  **Diagram in Passage** (if a diagram exists):
""" + PASSAGE_DIAGRAM_INLINE + r"""

4.  **Each Question-Solution pair**
    *   Begin with `\item` followed by the actual question text.
    *   Do **not** include exam or year metadata (e.g., `NEET[2022]`, `JEE 2019`, `IIT-JEE 2020`, `(2023)`, `[2021]`).
    *   Do **not** include example/exercise numbering prefixes (e.g., `Example 25.4`, `Ex. 3.2`, `Problem 12`, `Q.5`). Start directly with the actual problem text.
    *   Provide the options in a `tasks` environment. Use two columns unless the image shows otherwise.
    *   **CRITICAL:** Append ` \ans` to every correct option (single- or multi-correct). Example:
        ```latex
        \begin{tasks}(2)
            \task $10\,\mathrm{m/s}$
            \task $20\,\mathrm{m/s}$ \ans
            \task $30\,\mathrm{m/s}$
            \task $40\,\mathrm{m/s}$
        \end{tasks}
        ```
    *   Insert a `solution` environment directly after the `tasks` block. Inside it use **one** `align*` environment.
    *   Use `\intertext{}` to mix concise prose with math lines. Keep **one logical step per line** and **no blank lines** inside `align*`.
    *   **End each solution with:** `Therefore, the correct option is (x).` where x is the option letter (a, b, c, or d).
    *   **DO NOT combine multiple solutions** - each question must have its own separate conclusion.

---

## Strict Formatting Rules

* **Inline math:** Always wrap inline maths in `$ … $`.
* **Macros:** Use curly braces – e.g. `\vec{a}`, `\frac{a}{b}`.
* **Fractions:** Use `\frac{…}{…}` (never `\tfrac`).
* **Delimiters:** Use `\left( … \right)` etc.; avoid size macros like `\bigl`.
* **No blank lines** inside any `align*` environment.
* **Solution conclusion:** Each solution ends with "Therefore, the correct option is (x)." - NOT combined statements like "in (Q1) is (a), in (Q2) is (b)".

---

**Final Check:** Return only the LaTeX snippet from the first line shown above through the last `\end{solution}` with nothing extra.
"""

USER_TEMPLATE = "Extract LaTeX from this chemistry question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
