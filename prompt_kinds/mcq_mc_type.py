"""MCQ multi-correct (analyze and mark all correct options) – embedded."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** Analyze the provided image. Generate a complete LaTeX multiple-choice physics question based **exactly** on the image, including a step-by-step solution (which identifies all correct options) and, if applicable, a simplified `tzplot` diagram.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required LaTeX Structure

Follow this exact structure for your output:

1.  **Problem Statement (`\item ...`)**
    *   Begin the output *immediately* with `\item`.
    *   Extract the **exact** physics question text from the image **without any modifications or additions**.
    *   Use inline math mode `$ ... $` for all mathematical symbols and variables as they appear in the image.

2.  **TZPlot Diagram (Optional, place immediately after `\item` line if used)**
    *   Include *only* if the image contains a diagram OR if a diagram is essential for understanding the extracted text.
    *   Use `tzplot` commands (see reference below). **Only draw the frame/surface if necessary.** Do not draw other elements.
    *   Wrap *only* the `tikzpicture` environment within a `center` environment:
        ```latex
        \begin{center}
            \begin{tikzpicture}
                % Your simplified tzplot commands here (e.g., \pic)
            \end{tikzpicture}
        \end{center}
        ```

3.  **Multiple Choice Options (`\begin{tasks}(2) ... \end{tasks}`)**
    *   Use a 2-column `tasks` environment.
    *   Extract the **exact** option text from the image **without any modifications**.
    *   Provide the options using `\task`.
    *   Based on your analysis in the solution step, mark **every** correct answer by appending ` \ans` to the end of its corresponding `\task` line.

4.  **Solution (`\begin{solution} ... \end{solution}`)**
    *   Use an `align*` environment directly inside the `solution` environment.
    *   Show key conceptual steps and reasoning for solving the problem based on the extracted text.
    *   Use `\intertext{}` for brief text explanations *between* equation lines. Ensure any math within `\intertext{}` uses `$ ... $`.
    *   **Critically:** Analyze the problem to determine if it's single-correct or multi-correct. Evaluate *each* extracted option explicitly (e.g., "Checking option (a): ... This is correct/incorrect."). State the final correct options by letter (e.g., "Therefore, the correct option is (c)." or "Therefore, the correct options are (a) and (c)."). This analysis justifies the `\ans` markings in the `tasks` environment.
    *   Keep the solution concise and elegant. Show conceptual steps, but omit trivial intermediate algebra where appropriate.
    *   Align equations using `&`. Use `\\` to end lines.
    *   Keep only one step in every line of calculation.
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

## Example Reference Output (Illustrating Multi-Correct Handling)

*(This demonstrates how the structure handles a problem determined to be multi-correct during the solution phase, even if the extracted question wasn't explicitly phrased as multi-correct. The key is exact extraction first, then analysis.)*

\item A ball of mass $m$ moving with velocity $v_0$ collides a wall as shown in figure. After impact it rebounds with a velocity $\frac{3}{4} v_0$. Select the correct statement(s).
    \begin{center}
        \begin{tikzpicture}
            \pic (surface) [rotate=90] at (0, 0) {frame=4cm}; % Example using the simplified diagram command
        \end{tikzpicture}
    \end{center}
    \begin{tasks}(2)
        \task The component of impulse along $\hat{\jmath}$ is zero. \ans
        \task The magnitude of impulse is $\frac{3}{4}mv_0$.
        \task The impulse vector is $-\frac{5}{4}mv_0 \ \hat{\imath}$ (using standard angle approximations). \ans
        \task The impulse is purely vertical.
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
        &= m \left[ -1.25 v_0 \hat{i} + 0 \hat{j} \right] \\
        &= -1.25 m v_0 \hat{i} = -\frac{5}{4} m v_0 \hat{i} \\
        \intertext{Now checking the options based on the extracted text:}
        \intertext{(a) Option states: "The component of impulse along $\hat{\jmath}$ is zero." Our calculated $\vec{J}$ has a zero $\hat{j}$ component. So, option (a) is correct.}
        \intertext{(b) Option states: "The magnitude of impulse is $\frac{3}{4}mv_0$." Our calculated magnitude is $|\vec{J}| = \frac{5}{4} m v_0$. So, option (b) is incorrect.}
        \intertext{(c) Option states: "The impulse vector is $-\frac{5}{4}mv_0 \ \hat{\imath}$ (using standard angle approximations)." This matches our calculated $\vec{J}$. So, option (c) is correct.}
        \intertext{(d) Option states: "The impulse is purely vertical." Our calculated $\vec{J}$ is purely horizontal. So, option (d) is incorrect.}
        \intertext{Based on the analysis, the problem allows for multiple correct statements. Therefore, the correct options are (a) and (c).}
    \end{align*}
\end{solution}

---

**Final Check:** Ensure your output is ONLY the LaTeX snippet from `\item` to `\end{solution}` with no extra text or comments.
"""

__all__ = ["PROMPT"]
