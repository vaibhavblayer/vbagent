"""Subjective problem with solution (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX **subjective** physics question based **exactly** on the image. Include a detailed, step-by-step solution and, if applicable, a simplified `tzplot` diagram.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output *immediately* with `\item`.
    *   Extract the **exact** physics question text from the image **without any modifications or additions**.
    *   Use inline math mode `$ ... $` for all mathematical symbols and variables as they appear in the image.

2.  **TZPlot Diagram (Optional, place immediately after `\item` line if used)**
    *   Include *only* if the image contains a diagram **or** if a diagram is essential for understanding the extracted text.
    *   Use `tzplot` commands (see reference below). **Only draw the frame/surface if necessary.** Do not draw additional elements.
    *   Wrap *only* the `tikzpicture` environment within a `center` environment:
        ```latex
        \begin{center}
            \begin{tikzpicture}
                % Your simplified tzplot commands here (e.g., \pic)
            \end{tikzpicture}
        \end{center}
        ```

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

## TZPlot Command Reference (Use for Simplified Diagrams)

*(Only use the following if a simple surface/frame diagram is needed)*

*   **Ground/Wall:** `\pic (surface) at (0, 0) {frame=7cm};`

---

## Example Reference Output (Subjective Question)

*(This demonstrates the required structure for a subjective question)*

\item A ball of mass $m$ moving with velocity $v_0$ collides with a wall as shown in the figure. After impact, it rebounds with a velocity $\frac{3}{4} v_0$. Calculate the impulse acting on the ball during impact.
    \begin{center}
        \begin{tikzpicture}
            \pic (surface) [rotate=90] at (0,0) {frame=4cm};
        \end{tikzpicture}
    \end{center}
\begin{solution}
    \begin{align*}
        \intertext{Let the initial velocity be $\vec{v}_i$ and final velocity be $\vec{v}_f$. Impulse $\vec{J} = \Delta\vec{p} = m(\vec{v}_f - \vec{v}_i)$.}
        \vec{v}_i &= v_0 \cos(37^\circ)\hat{i} - v_0 \sin(37^\circ)\hat{j} \\
        \vec{v}_f &= -\frac{3}{4}v_0 \cos(53^\circ)\hat{i} - \frac{3}{4}v_0 \sin(53^\circ)\hat{j} \\
        \intertext{Using $\cos(37^\circ)\approx\sin(53^\circ)\approx0.8$ and $\sin(37^\circ)\approx\cos(53^\circ)\approx0.6$:}
        \vec{v}_i &\approx 0.8v_0\hat{i} - 0.6v_0\hat{j} \\
        \vec{v}_f &\approx -0.45v_0\hat{i} - 0.6v_0\hat{j} \\
        \vec{J} &= m(\vec{v}_f - \vec{v}_i) \\
        &= m\left[(-0.45 - 0.8)v_0\hat{i} + (-0.6 - (-0.6))v_0\hat{j}\right] \\
        &= -1.25mv_0\hat{i} \\
        &= -\frac{5}{4}mv_0\hat{i}
    \end{align*}
\end{solution}

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

__all__ = ["PROMPT"]
