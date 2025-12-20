"""Comprehension/passage with per-question solutions (embedded)."""

PROMPT = r"""
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

---

## Detailed LaTeX Structure

1.  **Title (optional)**
    ```latex
    \item[]
    \begin{center}
        \textsc{<Title from image>}
    \end{center}
    ```

2.  **Passage** – Write the paragraph exactly as-is (no surrounding environment).

3.  **Optional Diagram** (placeholder only, if a diagram exists OR is essential):
    ```latex
    \begin{center}
        \begin{tikzpicture}
            \pic {frame=3cm};
        \end{tikzpicture}
    \end{center}
    ```

4.  **Each Question-Solution pair**
    *   Begin with `\item` followed by the question text.
    *   Provide the options in a `tasks` environment.  Use two columns unless the image shows otherwise.
    *   Append ` \ans` to every correct option (single- or multi-correct).
    *   Insert a `solution` environment directly after the `tasks` block.  Inside it use **one** `align*` environment.
    *   Use `\intertext{}` to mix concise prose with math lines.  Keep **one logical step per line** and **no blank lines** inside `align*`.

---

## Strict Formatting Rules

* **Inline math:** Always wrap inline maths in `$ … $`.
* **Macros:** Use curly braces – e.g. `\vec{a}`, `\frac{a}{b}`.
* **Fractions:** Use `\frac{…}{…}` (never `\tfrac`).
* **Delimiters:** Use `\left( … \right)` etc.; avoid size macros like `\bigl`.
* **No blank lines** inside any `align*` environment.

---

## Mini Example

```latex
\item[]
\begin{center}
    \textsc{Comprehension-X}
\end{center}

A block of mass $m$ is projected up a rough incline… (passage continues).

\item The work done by friction until the block stops is
    \begin{tasks}(4)
        \task $mg\mu L$
        \task $-mg\mu L$ \ans
        \task $2mg\mu L$
        \task $0$
    \end{tasks}
\begin{solution}
    \begin{align*}
        \intertext{Friction opposes motion; work = $-\mu mg \cos\theta \times L$.  Here $\cos\theta = 1$ (horizontal example).}
        W_{\text{fr}} &= -\mu mg L
    \end{align*}
\end{solution}

\item The time taken for the block to return to the base is
    \begin{tasks}(4)
        \task $\sqrt{\dfrac{2L}{g\sin\theta}}$ \ans
        \task $\sqrt{\dfrac{L}{g\sin\theta}}$
        \task $\dfrac{2L}{g\sin\theta}$
        \task $\dfrac{L}{g\sin\theta}$
    \end{tasks}
\begin{solution}
    \begin{align*}
        \intertext{Using $s = ut + \tfrac12 a t^{2}$ with $u=0$ and $a=g\sin\theta$:}
        L &= \tfrac12 g\sin\theta\, t^{2} \\
        t &= \sqrt{\frac{2L}{g\sin\theta}}
    \end{align*}
\end{solution}
```

---

**Final Check:** Return only the LaTeX snippet from the first line shown above through the last `\end{solution}` with nothing extra.
"""

__all__ = ["PROMPT"]
