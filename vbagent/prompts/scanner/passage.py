"""Passage/Comprehension question scanner prompt."""

from vbagent.prompts.scanner.common import DIAGRAM_PLACEHOLDER

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
        \textsc{<Title from image>} \hfill [\arabic{enumi} to \number\numexpr\value{enumi}+N-1\relax]
    \end{center}
    ```
    where `N` is the total number of questions in this passage.
    
    **Example:** If passage has 3 questions, use:
    ```latex
    \textsc{Comprehension Passage} \hfill [\arabic{enumi} to \number\numexpr\value{enumi}+2\relax]
    ```
    This will auto-display as `[5 to 7]` if questions are numbered 5, 6, 7.

2.  **Passage Text**
    - Write the paragraph exactly as-is (no surrounding environment)
    - For multi-paragraph passages: separate paragraphs with a blank line
    - Use `\noindent` for the first paragraph after title to avoid indentation

3.  **Optional Diagram** (if a diagram exists OR is essential):
""" + DIAGRAM_PLACEHOLDER + r"""

4.  **Each Question-Solution pair**
    *   Begin with `\item` followed by the question text.
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

---

## Strict Formatting Rules

* **Inline math:** Always wrap inline maths in `$ … $`.
* **Macros:** Use curly braces – e.g. `\vec{a}`, `\frac{a}{b}`.
* **Fractions:** Use `\frac{…}{…}` (never `\tfrac`).
* **Delimiters:** Use `\left( … \right)` etc.; avoid size macros like `\bigl`.
* **No blank lines** inside any `align*` environment.

---

**Final Check:** Return only the LaTeX snippet from the first line shown above through the last `\end{solution}` with nothing extra.
"""

USER_TEMPLATE = "Extract LaTeX from this physics question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
