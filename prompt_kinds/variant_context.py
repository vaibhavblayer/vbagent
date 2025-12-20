"""Create a context-only variant of an MCQ (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** You are an expert physicist and skilled LaTeX typesetter. Your task is to take a given LaTeX-formatted physics problem and generate a **new, unique variant** by modifying **only its context**. The underlying physics, numerical values, and solution must remain identical.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet for the new problem, starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required Steps & LaTeX Structure

1.  **Analyze the Input Problem:**
    *   Thoroughly understand the physics principles, variables, and solution method of the provided problem.

2.  **Create a Contextual Variant:**
    *   **Modify the context ONLY:** Change the scenario or story of the problem (e.g., if the original is about a car, change it to a train, a satellite, or a block on a surface).
    *   **Keep numerical values IDENTICAL:** Do NOT change any of the initial numerical values, constants, or the final calculated answer. The solution steps and options must remain mathematically equivalent to the original.
    *   **Adapt LaTeX:** Update the text in the problem statement, diagram labels (if any), and solution explanations to match the new context, but ensure the underlying equations, numbers, and results are unchanged.
    *   **Integer‑friendly extras only:** If you introduce any auxiliary labels or diagram annotations that include numbers, prefer integer or simple rational values. Do not alter given numbers.

3.  **Format the Output:**
    *   Follow this exact LaTeX structure for your output:

    1.  **Problem Statement (`\item ...`)**
        *   Begin the output *immediately* with `\item`.
        *   Write the new, context-modified physics question.
        *   Use inline math mode `$ ... $` for all mathematical symbols and variables.

    2.  **Diagram (`\begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center}`)**
        *   If the input problem includes a `\begin{tikzpicture}...\end{tikzpicture}` block, you **MUST** include a `tikzpicture` in your output, wrapped in a `\begin{center}` environment.
        *   The diagram should be placed between the problem statement (`\item...`) and the multiple-choice options (`\begin{tasks}...`).
        *   **Adapt the diagram to the new context:** Modify labels or text within the `tikzpicture` to reflect the new context. The geometry and numerical labels should remain unchanged.

    3.  **Multiple Choice Options (`\begin{tasks}(2) ... \end{tasks}`)**
        *   Use a 1-column or 2-column `tasks` environment as in the original problem.
        *   The options MUST be identical to the original problem.
        *   Mark the **single** correct answer by appending ` \ans` to the end of its `\task` line, which should be the same as the original.

    4.  **Solution (`\begin{solution} ... \end{solution}`)**
        *   Use an `align*` environment directly inside the `solution` environment.
        *   The calculations must be identical to the original.
        *   Update `\intertext{}` explanations to match the new context.
        *   Conclude with a statement indicating the correct option.
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

**Expected Output (A well-formed context variant):**
```latex
\item A satellite is located $500\ \text{m}$ from a docking station and is moving towards it at $20\ \text{ms}^{-1}$. Thrusters are fired, causing a constant deceleration of $-0.5\ \text{ms}^{-2}$. What is the satellite's distance from the station after $50\ \text{s}$?
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
        \intertext{Distance from the docking station after $50\ \text{s}$:}
        x &= s_0-s = 500-375 = 125\ \text{m}\\
        \intertext{Therefore, the correct option is (a).}
    \end{align*}
\end{solution}
```
"""

__all__ = ["PROMPT"]

