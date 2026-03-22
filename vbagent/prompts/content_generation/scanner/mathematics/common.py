"""Common prompt components for mathematics scanner prompts.

Mathematics-specific TikZ guidelines, LaTeX formatting rules, and notation.
Shared constants (DIAGRAM_PLACEHOLDER, PASSAGE_DIAGRAM_INLINE, OPTIONS_WITH_DIAGRAMS)
are imported from the _shared module.
"""

from .._shared import (
    DIAGRAM_PLACEHOLDER,
    PASSAGE_DIAGRAM_INLINE,
    OPTIONS_WITH_DIAGRAMS_MATHEMATICS as OPTIONS_WITH_DIAGRAMS,
)

# Mathematics-specific TikZ guidelines
TIKZ_GUIDELINES = r"""
    **TikZ Guidelines for Mathematics Diagrams:**
    
    **PRINCIPLES:**
    1. Use TikZ for geometric figures, constructions
    2. Use pgfplots for function graphs and plots
    3. Use TikZ for number lines, Venn diagrams
    4. Keep diagrams mathematically precise
    
    **Geometric Figures (TikZ):**
    ```latex
    \begin{tikzpicture}
    % Triangle
    \coordinate (A) at (0,0);
    \coordinate (B) at (4,0);
    \coordinate (C) at (2,3);
    \draw[thick] (A) -- (B) -- (C) -- cycle;
    \node[below left] at (A) {$A$};
    \node[below right] at (B) {$B$};
    \node[above] at (C) {$C$};
    \end{tikzpicture}
    ```
    
    **Function Graphs (pgfplots):**
    ```latex
    \begin{tikzpicture}
    \begin{axis}[
        axis lines = middle,
        xlabel = {$x$},
        ylabel = {$y$},
        domain = -2:2,
    ]
    \addplot[thick,blue] {x^2};
    \end{axis}
    \end{tikzpicture}
    ```
    
    **Number Lines (TikZ):**
    ```latex
    \begin{tikzpicture}
    \draw[<->,thick] (-3,0) -- (3,0);
    \foreach \x in {-2,-1,0,1,2}
        \draw (\x,0.1) -- (\x,-0.1) node[below] {$\x$};
    \end{tikzpicture}
    ```
"""


# Shorter version
TIKZ_GUIDELINES_SHORT = r"""
    **TikZ Guidelines for Mathematics:**
    *   Use TikZ for geometric figures and constructions
    *   Use pgfplots for function graphs
    *   Use TikZ for number lines and Venn diagrams
    *   Keep diagrams mathematically precise
"""

# Mathematics-specific LaTeX formatting rules
LATEX_FORMATTING_RULES = r"""
## Mathematics LaTeX Formatting Rules

**Mathematical Notation:**
*   Use `$ ... $` for inline math
*   Use `\frac{a}{b}` for fractions
*   Use `\left( ... \right)` for parentheses
*   Use `\left[ ... \right]` for brackets
*   Use `\left| ... \right|` for absolute value

**Set Notation:**
*   $\in$ for element of: $x \in \mathbb{R}$
*   $\subset$ for subset: $A \subset B$
*   $\cup$ for union: $A \cup B$
*   $\cap$ for intersection: $A \cap B$
*   $\emptyset$ for empty set

**Logic Symbols:**
*   $\implies$ for implies
*   $\iff$ for if and only if
*   $\forall$ for for all
*   $\exists$ for there exists

**Calculus:**
*   $\lim_{x \to a} f(x)$ for limits
*   $\frac{d}{dx}$ or $f'(x)$ for derivatives
*   $\int f(x) \, dx$ for integrals
*   $\sum_{i=1}^{n}$ for summation
*   $\prod_{i=1}^{n}$ for product

**Geometry:**
*   $\angle ABC$ for angles
*   $\overline{AB}$ for line segments
*   $\triangle ABC$ for triangles
*   $\parallel$ for parallel
*   $\perp$ for perpendicular
*   $\cong$ for congruent
*   $\sim$ for similar

**Number Sets:**
*   $\mathbb{N}$ for natural numbers
*   $\mathbb{Z}$ for integers
*   $\mathbb{Q}$ for rationals
*   $\mathbb{R}$ for reals
*   $\mathbb{C}$ for complex numbers
"""




# Mathematics solution structure guidelines
SOLUTION_STRUCTURE = r"""
## Mathematics Solution Structure

**For Algebraic Problems:**
```latex
\begin{solution}
\begin{align*}
    2x + 3 &= 7 \\
    2x &= 4 \\
    x &= 2
\end{align*}
\end{solution}
```

**For Proofs:**
```latex
\begin{solution}
\textbf{Given:} $a > 0$ and $b > 0$

\textbf{To Prove:} $\frac{a+b}{2} \geq \sqrt{ab}$

\textbf{Proof:}
\begin{align*}
    (\sqrt{a} - \sqrt{b})^2 &\geq 0 \\
    a - 2\sqrt{ab} + b &\geq 0 \\
    a + b &\geq 2\sqrt{ab} \\
    \frac{a+b}{2} &\geq \sqrt{ab}
\end{align*}
Hence proved. $\blacksquare$
\end{solution}
```

**For Calculus:**
```latex
\begin{solution}
\begin{align*}
    f(x) &= x^2 + 3x + 2 \\
    f'(x) &= 2x + 3 \\
    \intertext{Setting $f'(x) = 0$:}
    2x + 3 &= 0 \\
    x &= -\frac{3}{2}
\end{align*}
\end{solution}
```
"""

__all__ = [
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "DIAGRAM_PLACEHOLDER",
    "PASSAGE_DIAGRAM_INLINE",
    "OPTIONS_WITH_DIAGRAMS",
    "SOLUTION_STRUCTURE",
]
