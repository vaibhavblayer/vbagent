"""MCQ single-correct question with solution (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX multiple-choice physics question based **exactly** on the image, assuming it has a **single correct answer**. Include a step-by-step solution (which identifies the correct option) and, if applicable, a minimal TikZ diagram.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output immediately with `\item`.
    *   Extract the exact physics question text from the image without any modifications or additions.
    *   Use inline math mode `$ ... $` for all mathematical symbols and variables as they appear in the image.
    *   Do not include exam or year metadata (e.g., `NEET[2022]`, `JEE 2019`).

2.  **Diagram (Optional, place immediately after `\item` line if used)**
    *   Include only if the image contains a diagram OR if a diagram is essential for clarity.
    *   Use base TikZ only (no tzplot). Structure the diagram in this order:
        - Define scalar parameters at the top using `\def` (e.g., `\def\L{2}`, `\def\theta{30}`).
        - Define coordinates with `\coordinate` using those parameters.
        - Draw elements with `\draw` (axes, lines, vectors, frames, labels).
        - Keep numeric dimensions small: prefer values in `1–6` (max `7`). Do not define large parameters like `\def\L{20}` or use large coordinates like `(9,0)`; keep coordinates roughly within `[0,7]`.
    *   Wrap only the `tikzpicture` environment within a `center` environment. Example pattern:
        ```latex
        \begin{center}
            \begin{tikzpicture}
                \def\L{2}
                \def\theta{30}
                \coordinate (O) at (0,0);
                \coordinate (A) at (\L,0);
                \coordinate (B) at ({\L*cos(\theta)},{\L*sin(\theta)});
                \draw[->] (-0.5,0) -- (3,0) node[right] {$x$};
                \draw[->] (0,-0.5) -- (0,3) node[above] {$y$};
                \draw (O) -- (A) -- (B) -- cycle;
            \end{tikzpicture}
        \end{center}
        ```

3.  **Multiple Choice Options (`\begin{tasks}(c) ... \end{tasks}`)**
    *   Column rule: choose columns by option style.
        - Use `\begin{tasks}(2)` for numerical or short-expression options.
        - Use `\begin{tasks}(1)` for statement-based or long textual options.
    *   Extract the exact option text from the image without any modifications.
    *   Provide the options using `\task`.
    *   Based on your analysis in the solution step, mark the single correct answer by appending ` \ans` to the end of its corresponding `\task` line.

4.  **Solution (`\begin{solution} ... \end{solution}`)**
    *   Use an `align*` environment directly inside the `solution` environment.
    *   Show key conceptual steps and reasoning for solving the problem based on the extracted text.
    *   Use `\intertext{}` for brief text explanations between equation lines. Ensure any math within `\intertext{}` uses `$ ... $`. Do not nest `\text{...}` inside `\intertext{}`; use plain prose and wrap only math in `$...$`.
    *   Critically: Evaluate the options to identify the single correct answer. Explain why it is correct and briefly why others might be incorrect if helpful for clarity. State the final correct option by letter (e.g., "Therefore, the correct option is (c)."). This analysis justifies the `\ans` marking in the `tasks` environment.
    *   Keep the solution concise and elegant. Show conceptual steps, but omit trivial intermediate algebra where appropriate.
    *   Align equations using `&`. Use `\\` to end lines.
    *   Keep only one step in every line of calculation.
    *   Strictly forbidden: Do not leave any blank lines inside the `align*` environment.

---

## Strict LaTeX Formatting Rules

Adhere to these rules meticulously:

*   Math Mode: Use `$ ... $` for all inline math.
*   Macros: Always use `{}`: `\vec{a}`, `\frac{a}{b}`.
*   Vectors: Use `\vec{a}` for generic vectors and `\hat{i}`, `\hat{j}`, `\hat{k}` for unit vectors.
*   Fractions: Use `\frac{a}{b}`. Do not use `\tfrac`.
*   Parentheses/Brackets: Use `\left( ... \right)`, `\left[ ... \right]`, `\left| ... \right|`. Do not use `\bigl`, `\bigr`, `\Bigl`, `\Bigr`, etc.
*   Intertext rule: Inside `\intertext{...}`, do not use `\text{...}`. Use plain text and wrap math with `$...$`.

---

## TikZ Diagram Reference (Base TikZ)

Use only the TikZ base library. Recommended order inside `tikzpicture`:

1. Define scalar parameters at the top using `\def` (e.g., `\def\L{2}`, `\def\h{1.5}`).
2. Define coordinates using `\coordinate` with those parameters.
3. Draw axes and geometry with `\draw` (arrows, dashed lines, frames, labels).
4. Keep the diagram minimal; include only what clarifies the problem.
5. Numeric bounds: Keep parameter values and coordinates modest (ideally `\\le 7`). Avoid large numbers such as `9`, `10`, or `20`. If scaling is needed, use a small parameter (e.g., `\\def\\L{3}`) and multiply, but keep `\\L \\le 7`.

---

## Example Reference Output (Single Correct Answer)

This demonstrates the required structure for a single-correct answer question (diagram simplified using base TikZ):

\item A ball of mass $m$ moving with velocity $v_0$ collides a wall as shown in figure. After impact it rebounds with a velocity $\frac{3}{4} v_0$. The impulse acting on ball during impact is
    \begin{center}
        \begin{tikzpicture}
            \def\L{2}
            % Minimal illustrative frame (rotated wall)
            \draw[rotate=90] (0,0) rectangle (0.2,\L);
        \end{tikzpicture}
    \end{center}
    \begin{tasks}(2)
        \task $-\frac{m}{2}v_0 \ \hat{\jmath}$
        \task $-\frac{3}{4}mv_0 \ \hat{\imath}$
        \task $-\frac{5}{4}mv_0 \ \hat{\imath}$ \ans
        \task None of the above
    \end{tasks}
\begin{solution}
    \begin{align*}
        \intertext{Let the initial velocity be $\vec{v}_i$ and final velocity be $\vec{v}_f$. Impulse $\vec{J} = \Delta\vec{p} = m(\vec{v}_f - \vec{v}_i)$. Assume standard angles $37^\circ$ and $53^\circ$ as implied by similar problems.}
        \vec{v}_i &= v_0 \cos(37^\circ)\hat{i} - v_0 \sin(37^\circ)\hat{j} \\
        \vec{v}_f &= -\frac{3}{4}v_0 \cos(53^\circ)\hat{i} - \frac{3}{4}v_0 \sin(53^\circ)\hat{j} \\
        \intertext{Using standard approximations $\cos(37^\circ) \approx \sin(53^\circ) \approx 0.8$ and $\sin(37^\circ) \approx \cos(53^\circ) \approx 0.6$:}
        \vec{v}_i &\approx 0.8 v_0 \hat{i} - 0.6 v_0 \hat{j} \\
        \vec{v}_f &\approx -\frac{3}{4}v_0 (0.6)\hat{i} - \frac{3}{4}v_0 (0.8)\hat{j} \\
        &= -0.45 v_0 \hat{i} - 0.6 v_0 \hat{j} \\
        \vec{J} &= m(\vec{v}_f - \vec{v}_i) \\
        &= m [ (-0.45 v_0 \hat{i} - 0.6 v_0 \hat{j}) - (0.8 v_0 \hat{i} - 0.6 v_0 \hat{j}) ] \\
        &= m [ (-0.45 - 0.8) v_0 \hat{i} + (-0.6 - (-0.6)) v_0 \hat{j} ] \\
        &= m (-1.25 v_0 \hat{i} + 0 \hat{j}) \\
        &= -1.25 m v_0 \hat{i} = -\frac{5}{4} m v_0 \hat{i} \\
        \intertext{Therefore, the correct option is (c).}
    \end{align*}
\end{solution}

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

__all__ = ["PROMPT"]
