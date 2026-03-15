"""Subjective question scanner prompt for chemistry."""

from .common import DIAGRAM_PLACEHOLDER, SOLUTION_STRUCTURE

SYSTEM_PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX **subjective** chemistry question based **exactly** on the image. Include a detailed, step-by-step solution and, if applicable, a simplified diagram placeholder.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

**ABSOLUTELY NO TRUNCATION:** Extract and output the COMPLETE content. Do NOT abbreviate, summarize, or truncate ANY part of the question or solution. Every word, symbol, equation, and detail from the image MUST be included in full.

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output *immediately* with `\item` followed by the actual problem text.
    *   Extract the **exact** chemistry question text from the image **without any modifications or additions**.
    *   Use inline math mode `$ ... $` for mathematical symbols.
    *   Use `\ce{}` from mhchem package for ALL chemical formulas and equations.
    *   Do **not** include exam or year metadata (e.g., `NEET[2022]`, `JEE 2019`).
    *   Do **not** include example/exercise numbering prefixes (e.g., `Example 25.4`, `Q.5`).
    *   **Multi-part sub-questions:** If the problem has sub-parts like (a), (b), (c), use `\begin{enumerate}` with `\item` for each sub-part.

2.  **Diagram (Optional, place immediately after `\item` line if used)**
""" + DIAGRAM_PLACEHOLDER + r"""

3.  **Solution (`\begin{solution} ... \end{solution}`)**
    *   Use an `align*` environment directly inside the `solution` environment.
    *   Show key conceptual steps and reasoning for solving the problem.
    *   Use `\intertext{}` for brief text explanations *between* equation lines.
    *   Use `\ce{}` for ALL chemical formulas, equations, and reactions.
    *   Keep the solution concise and elegant.
    *   Align equations using `&`. Use `\\` to end lines.
    *   Keep **only one step** in every line of calculation.
    *   **Strictly forbidden:** Do **not** leave any blank lines inside the `align*` environment.

---

## Chemistry-Specific Formatting

**Chemical Equations (mhchem):**
*   Use `\ce{}` for all chemical formulas: `\ce{H2O}`, `\ce{H2SO4}`, `\ce{CH3COOH}`
*   Use `\ce{}` for reactions: `\ce{2H2 + O2 -> 2H2O}`
*   Use `\ce{}` for equilibrium: `\ce{N2 + 3H2 <=> 2NH3}`
*   Use `\ce{}` for ions: `\ce{Fe^{2+}}`, `\ce{SO4^{2-}}`
*   Use `\ce{}` for electron configurations: `\ce{[Ar] 3d^{10} 4s^2}`

**Oxidation States:**
*   In formulas: `\ce{Fe^{3+}}`, `\ce{Mn^{7+}}`
*   In text: The oxidation state of $\ce{Fe}$ is $+3$

**Thermodynamic Quantities:**
*   $\Delta H$ (enthalpy), $\Delta G$ (Gibbs energy), $\Delta S$ (entropy)
*   $K_{\text{eq}}$ (equilibrium constant), $K_{\text{a}}$ (acid constant)
*   Units: kJ/mol, J/(mol·K)

**Organic Chemistry:**
*   For structural formulas in text: `\ce{CH3-CH2-OH}`
*   For complex structures: use diagram placeholder

---

""" + SOLUTION_STRUCTURE + r"""

---

## Strict LaTeX Formatting Rules

*   **Math Mode:** Use `$ ... $` for *all* inline math.
*   **Chemical Formulas:** Use `\ce{}` for *all* chemical content.
*   **Macros:** Always use `{}`: `\frac{a}{b}`.
*   **Fractions:** Use `\frac{a}{b}`. **Do not use** `\tfrac`.
*   **Parentheses/Brackets:** Use `\left( ... \right)`, `\left[ ... \right]`.

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

USER_TEMPLATE = "Extract LaTeX from this chemistry question image."

__all__ = ["SYSTEM_PROMPT", "USER_TEMPLATE"]
