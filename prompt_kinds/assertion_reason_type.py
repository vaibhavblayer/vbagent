"""Assertion–Reason question extraction with solution (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

Analyze the provided image and extract an Assertion–Reason style question. Produce only a LaTeX snippet that starts with a single `\item` containing the assertion and reason on one item, then a worked `solution` block.

**CRITICAL OUTPUT CONSTRAINT:** Return only the raw LaTeX snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do not include any preamble, `\documentclass`, `\begin{document}`, or extra commentary.

---

## Required LaTeX Structure

1.  Problem Statement (`\item ...`)
    * Begin immediately with `\item`.
    * Use this exact pattern (two bold labels inside the same item):
      `\item \textbf{Assertion}: <extracted assertion text>\\\n      \textbf{Reason}: <extracted reason text>`
    * Extract the assertion and reason exactly as shown in the image (no additions/omissions).
    * Do not include exam/year metadata (e.g., `NEET[2022]`).

2.  Assertion and Reason Options (`\begin{tasks}(c) ... \end{tasks}`)**
    *   Column rule: choose columns by option style.
        \begin{tasks}(1)
          \task Both Assertion and Reason are true and  Reason is the correct explanation of Assertion 
          \task Both Assertion and Reason are true but Reason  is not the correct explanation of Assertion  
          \task Assertion is true but Reason is false \ans
          \task Both Assertion and Reason are false 
        \end{tasks}
    *   Provide the options using `\task`.
    *   Based on your analysis in the solution step, mark the single correct answer by appending ` \ans` to the end of its corresponding `\task` line.

3.  Solution (`\begin{solution} ... \end{solution}`)
    * Place a `solution` environment immediately after the `\item`.
    * Inside, use one `align*` environment.
    * Use `\intertext{...}` for short prose between equation lines; wrap any math with `$...$`. Do not nest `\text{...}` inside `\intertext{...}`.
    * Briefly analyze truth values and causal relation:
      - Is the Assertion true or false?
      - Is the Reason true or false?
      - If both are true, does the Reason correctly explain the Assertion?
    * Conclude with a clear classification sentence, e.g.,
      `\intertext{Therefore: Assertion is true; Reason is true and is the correct explanation.}`
      or
      `\intertext{Therefore: Assertion is true; Reason is false.}`
    * Keep one logical step per line; do not leave blank lines inside `align*`.

---

## Strict LaTeX Rules

* Inline math: always `$...$` (including inside `\intertext{...}`).
* Macros with braces: `\vec{a}`, `\frac{a}{b}`.
* Parentheses/brackets: `\left(\cdot\right)`, `\left[\cdot\right]`, `\left|\cdot\right|`.
* Intertext rule: in `\intertext{...}`, do not use `\text{...}`; write plain prose and wrap math with `$...$` only.

---

## Mini Example (format illustration only)

\item \textbf{Assertion}: Linear momentum of a body changes even when it moves uniformly in a circle.\\
\textbf{Reason}: In uniform circular motion, velocity remains constant.
\begin{tasks}(1)
  \task Both Assertion and Reason are true and  Reason is the correct explanation of Assertion 
  \task Both Assertion and Reason are true but Reason  is not the correct explanation of Assertion  
  \task Assertion is true but Reason is false \ans
  \task Both Assertion and Reason are false 
\end{tasks}
\begin{solution}
    \begin{align*}
        \intertext{Velocity changes direction continuously in uniform circular motion; thus momentum $\vec{p}=m\vec{v}$ changes. Assertion: true.}
        \intertext{Magnitude of speed is constant, but $\vec{v}$ (a vector) is not constant; hence the Reason statement ("velocity remains constant") is false if it means vector velocity.}
        \intertext{Therefore: Assertion is true; Reason is false.}
    \end{align*}
\end{solution}
"""

__all__ = ["PROMPT"]
