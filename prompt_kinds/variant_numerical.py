"""Create a numerical-parameters variant of an MCQ (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** You are an expert physicist and skilled LaTeX typesetter. Your task is to take a given LaTeX-formatted physics problem and generate a **new, unique variant** by modifying **only its numerical values**. The context and physical principles must remain the same.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet for the new problem, starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required Steps & LaTeX Structure

1.  **Analyze the Input Problem:**
    *   Thoroughly understand the physics principles, variables, and solution method of the provided problem.

2.  **Create a Numerical Variant:**
    *   **Modify numerical values ONLY:** Alter the given values (e.g., mass, velocity, distance) to be realistic but different. The underlying physical context and scenario must remain the same.
    *   **Do NOT change the context:** If the problem is about a car on a road, it must remain about a car on a road.
    *   **Recalculate everything:** Based on the new values, re-solve the problem from first principles to get a new correct answer.
    *   **Generate new distractors:** Create three new incorrect options that are plausible but based on common mistakes (e.g., sign errors, unit conversion errors, wrong formula).
    *   **Prefer integer‑friendly values:** Choose parameters so that key intermediate results and the final answer come out as integers (or simple rationals) to keep arithmetic simple and let students focus on the core idea.

3.  **Format the Output:**
    *   Follow this exact LaTeX structure for your output:

    1.  **Problem Statement (`\item ...`)**
        *   Begin the output *immediately* with `\item`.
        *   Write the physics question with the new numerical values.
        *   Use inline math mode `$ ... $` for all mathematical symbols and variables.

    2.  **Diagram (`\begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center}`)**
        *   If the input problem includes a `\begin{tikzpicture}...\end{tikzpicture}` block, you **MUST** include a `tikzpicture` in your output, wrapped in a `\begin{center}` environment.
        *   The diagram should be placed between the problem statement (`\item...`) and the multiple-choice options (`\begin{tasks}...`).
        *   **Adapt the diagram to the new problem:** Modify coordinates, labels, or elements within the `tikzpicture` to reflect the new numerical values and context of your variant. For example, if you change a force from 10N to 20N, update the corresponding label in the diagram. If the setup changes, modify the drawing commands accordingly. Do not just copy the old diagram if changes are needed.

    3.  **Multiple Choice Options (`\begin{tasks}(2) ... \end{tasks}`)**
        *   Use a 1-column or 2-column `tasks` environment as in the original problem.
        *   Provide your four new options (one correct, three distractors) using `\task`.
        *   Mark the **single** correct answer by appending ` \ans` to the end of its `\task` line.

    4.  **Solution (`\begin{solution} ... \end{solution}`)**
        *   Use an `align*` environment directly inside the `solution` environment.
        *   Show the key conceptual steps and calculations for your new, modified problem.
        *   Use `\intertext{}` for brief text explanations *between* equation lines.
        *   Align equations using `&`. Use `\\` to end lines.
        *   Keep only one step in every line of calculation.
        *   Conclude with a statement indicating the correct option (e.g., `\intertext{Therefore, the correct option is (a).}`).
        *   **Strictly forbidden:** Do **not** leave any blank lines inside the `align*` environment.

---

## Strict LaTeX Formatting Rules

*   **Math Mode:** Use `$ ... $` for *all* inline math.
*   **Macros:** Always use `{}`: `\vec{a}`, `\frac{a}{b}`, `\text{m}`.
*   **Vectors:** Use `\vec{a}` for generic vectors and `\hat{i}`, `\hat{j}`, `\hat{k}` for unit vectors.
*   **Fractions:** Use `\frac{a}{b}`. **Do not use** `\tfrac`.
*   **Parentheses/Brackets:** Use `\left( ... \right)`, `\left[ ... \right]`, `\left| ... \right|`.
*   **Units:** Use `\ \text{m}`, `\ \text{s}`, `\ \text{ms}^{-1}`, `\ \text{ms}^{-2}` for units to ensure proper spacing and formatting.

---

## Example of Task

**Input Problem:**
```latex
\item At a distance of $500\ \text{m}$ from the traffic light, brakes are applied to an automobile moving at a velocity of $20\ \text{ms}^{-1}$. The position of automobile wrt traffic light $50\ \text{s}$ after applying the brakes, if its acceleration is $-0.5\ \text{ms}^{-2}$, is
    \begin{tasks}(2)
        \task $125\ \text{m}$ \ans
        \task $375\ \text{m}$
        \task $400\ \text{m}$
        \task $100\ \text{m}$
    \end{tasks}
\begin{solution}
    \begin{align*}
        u &= 20\ \text{ms}^{-1},\ a=-0.5\ \text{ms}^{-2},\ t=50\ \text{s},\ s_0=500\ \text{m}\\
        \intertext{Displacement in $t$ seconds:}
        s &= ut+\frac{1}{2}at^{2}\\
          &= 20(50)+\frac{1}{2}(-0.5)(50)^{2}\\
          &= 1000-625\\
          &= 375\ \text{m}\\
        \intertext{Distance from the traffic light after $50\ \text{s}$:}
        x &= s_0-s = 500-375 = 125\ \text{m}\\
        \intertext{Therefore, the correct option is (a).}
    \end{align*}
\end{solution}
```

**Expected Output (A well-formed numerical variant):**
```latex
\item At a distance of $600\ \text{m}$ from the traffic light, brakes are applied to an automobile moving at a velocity of $25\ \text{ms}^{-1}$. The position of automobile wrt traffic light $40\ \text{s}$ after applying the brakes, if its acceleration is $-0.5\ \text{ms}^{-2}$, is
    \begin{tasks}(2)
        \task $600\ \text{m}$
        \task $200\ \text{m}$
        \task $400\ \text{m}$ \ans
        \task $0\ \text{m}$
    \end{tasks}
\begin{solution}
    \begin{align*}
        u &= 25\ \text{ms}^{-1},\ a=-0.5\ \text{ms}^{-2},\ t=40\ \text{s},\ s_0=600\ \text{m}\\
        \intertext{Displacement in $t$ seconds:}
        s &= ut+\frac{1}{2}at^{2}\\
          &= 25(40)+\frac{1}{2}(-0.5)(40)^{2}\\
          &= 1000-400\\
          &= 600\ \text{m}\\
        \intertext{Distance from the traffic light after $40\ \text{s}$:}
        x &= s_0-s = 600-600 = 0\ \text{m}\\
        \intertext{Therefore, the correct option is (d).}
    \end{align*}
\end{solution}
```
"""

__all__ = ["PROMPT"]
