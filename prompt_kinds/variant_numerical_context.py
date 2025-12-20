"""Create a variant modifying both context and numbers (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** You are an expert physicist and skilled LaTeX typesetter. Your task is to take a given LaTeX-formatted physics problem and generate a **new, unique variant** of it. This involves modifying the problem's context, numerical values, and recalculating the solution and options accordingly.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet for the new problem, starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required Steps & LaTeX Structure

1.  **Analyze the Input Problem:**
    *   Thoroughly understand the physics principles, variables, and solution method of the provided problem.

2.  **Create a Variant:**
    *   **Modify the context:** Change the scenario slightly (e.g., if the original is about a car, change it to a train or a block on a surface).
    *   **Change numerical values:** Alter the given values (e.g., mass, velocity, distance) to be realistic but different.
    *   **Recalculate everything:** Based on the new values, re-solve the problem from first principles to get a new correct answer.
    *   **Generate new distractors:** Create three new incorrect options that are plausible but based on common mistakes (e.g., sign errors, unit conversion errors, wrong formula).
    *   **Prefer integer‑friendly values:** Choose parameters so that key intermediate results and the final answer come out as integers (or simple rationals) to keep arithmetic simple and let students focus on the core idea.

3.  **Format the Output:**
    *   Follow this exact LaTeX structure for your output:

    1.  **Problem Statement (`\item ...`)**
        *   Begin the output *immediately* with `\item`.
        *   Write the new, modified physics question.
        *   Use inline math mode `$ ... $` for all mathematical symbols and variables.

    2.  **Multiple Choice Options (`\begin{tasks}(2) ... \end{tasks}`)**
        *   Use a 2-column `tasks` environment.
        *   Provide your four new options (one correct, three distractors) using `\task`.
        *   Mark the **single** correct answer by appending ` \ans` to the end of its `\task` line.

    3.  **Solution (`\begin{solution} ... \end{solution}`)**
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
*   **Units:** Use `\ \text{m}`, `\ \text{s}`, `\ \text{N}`, `\ \text{J}`.

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

**Expected Output (A well-formed variant):**
```latex
\item A train, $800\ \text{m}$ away from a station, starts to slow down from an initial velocity of $30\ \text{ms}^{-1}$. If the deceleration is a constant $-0.6\ \text{ms}^{-2}$, what is the train's distance from the station after $40\ \text{s}$?
    \begin{tasks}(2)
        \task $80\ \text{m}$
        \task $720\ \text{m}$
        \task $280\ \text{m}$ \ans
        \task $520\ \text{m}$
    \end{tasks}
\begin{solution}
    \begin{align*}
        u &= 30\ \text{ms}^{-1},\ a=-0.6\ \text{ms}^{-2},\ t=40\ \text{s},\ s_0=800\ \text{m}\\
        \intertext{Displacement in $t$ seconds:}
        s &= ut+\frac{1}{2}at^{2}\\
          &= 30(40)+\frac{1}{2}(-0.6)(40)^{2}\\
          &= 1200-480\\
          &= 720\ \text{m}\\
        \intertext{Distance from the station after $40\ \text{s}$:}
        x &= s_0-s = 800-720 = 80\ \text{m}\\
        \intertext{Therefore, the correct option is (a).}
    \end{align*}
\end{solution}
```
"""

__all__ = ["PROMPT"]

