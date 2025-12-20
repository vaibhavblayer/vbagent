"""Create a conceptual variant MCQ (embedded)."""

PROMPT = r"""
## Overall Task & Output Format

**Goal:** You are an expert physicist and skilled LaTeX typesetter. Your task is to take a given LaTeX-formatted physics problem and generate a **new, unique variant** by making a **conceptual modification**. This means changing the core principles being tested, not just the surface details.

**CRITICAL OUTPUT CONSTRAINT:** You MUST return *only* the raw LaTeX code snippet for the new problem, starting precisely with `\item` and ending precisely after `\end{solution}`. Do **NOT** include *any* preamble, `\documentclass`, `\begin{document}`, explanations, comments, or any text outside of this exact snippet.

---

## Required Steps & LaTeX Structure

1.  **Analyze the Input Problem:**
    *   Thoroughly understand the physics principles, variables, and solution method of the provided problem.

2.  **Create a Conceptual Variant:**
    *   **Perform a conceptual modification:** Instead of just changing the story or numbers, alter a core concept or the setup of the problem. For example:
        *   If the original problem uses constant acceleration, make it a problem with acceleration as a function of time (e.g., $a(t) = kt$).
        *   If the original is about linear motion, change it to rotational motion.
        *   If the original is about projectile motion on a flat surface, change it to an inclined plane.
        *   If the original asks for a final position, ask for the time taken to stop or the work done by the brakes instead.
    *   **Change numerical values:** You will likely need to introduce new values or change existing ones to fit the new concept.
    *   **Recalculate everything:** Solve the new, conceptually different problem from first principles.
    *   **Generate new distractors:** Create plausible incorrect options for your new problem.
    *   **Prefer integer‑friendly values:** Choose parameters so that key intermediate results and the final answer come out as integers (or simple rationals) to keep arithmetic simple and let students focus on the core idea.

3.  **Format the Output:**
    *   Follow this exact LaTeX structure for your output:

    1.  **Problem Statement (`\item ...`)**
        *   Begin the output *immediately* with `\item`.
        *   Write the new, conceptually modified physics question.
        *   Use inline math mode `$ ... $` for all mathematical symbols and variables.

    2.  **Diagram (`\begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center}`)**
        *   If relevant, include an adapted `tikzpicture` that correctly represents the new problem's setup.

    3.  **Multiple Choice Options (`\begin{tasks}(2) ... \end{tasks}`)**
        *   Provide your four new options (one correct, three distractors) using `\task`.
        *   Mark the **single** correct answer by appending ` \ans` to the end of its `\task` line.

    4.  **Solution (`\begin{solution} ... \end{solution}`)**
        *   Use an `align*` environment to show the derivation for the new problem. This will likely involve different formulas (e.g., integration if acceleration is not constant).
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

**Expected Output (A well-formed conceptual variant):**
```latex
\item Brakes are applied to an automobile moving at $20\ \text{ms}^{-1}$. The acceleration of the automobile is given by $a(t) = -0.1t \ \text{ms}^{-2}$. How much time does it take for the automobile to come to a complete stop?
    \begin{tasks}(2)
        \task $10\ \text{s}$
        \task $40\ \text{s}$
        \task $20\ \text{s}$ \ans
        \task $15\ \text{s}$
    \end{tasks}
\begin{solution}
    \begin{align*}
        u &= 20\ \text{ms}^{-1} \\
        a(t) &= -0.1t \\
        \intertext{To find the velocity $v(t)$, we integrate the acceleration:} \\
        v(t) &= v(0) + \int_{0}^{t} a(t') \,dt' \\
              &= 20 + \int_{0}^{t} -0.1t' \,dt' \\
              &= 20 - 0.1 \left[ \frac{t'^2}{2} \right]_{0}^{t} \\
              &= 20 - 0.05t^2 \\
        \intertext{The automobile stops when $v(t) = 0$:} \\
        0 &= 20 - 0.05t^2 \\
        0.05t^2 &= 20 \\
        t^2 &= \frac{20}{0.05} = 400 \\
        t &= 20\ \text{s} \\
        \intertext{Therefore, the correct option is (c).}
    \end{align*}
\end{solution}
```
"""

__all__ = ["PROMPT"]

