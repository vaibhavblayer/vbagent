"""Common prompt components for physics scanner prompts.

Physics-specific TikZ guidelines, LaTeX formatting rules, and notation.
Shared constants (DIAGRAM_PLACEHOLDER, PASSAGE_DIAGRAM_INLINE, OPTIONS_WITH_DIAGRAMS)
are imported from the _shared module.
"""

from .._shared import (
    DIAGRAM_PLACEHOLDER,
    PASSAGE_DIAGRAM_INLINE,
    OPTIONS_WITH_DIAGRAMS_PHYSICS as OPTIONS_WITH_DIAGRAMS,
)

# TikZ Variable Guidelines - shared across all scanner prompts
TIKZ_GUIDELINES = r"""
    **TikZ Variable Guidelines (CRITICAL - CLEAN, MINIMAL VARIABLES):**
    
    **PRINCIPLES:**
    1. Define only BASE dimensions as variables (things you might adjust)
    2. Use NODES with anchors for objects (blocks, shapes) - enables relative positioning
    3. Use TikZ RELATIVE POSITIONING: `below of=`, `above of=`, `xshift`, `yshift`
    4. Use `node[midway]` for labels on lines/springs - NO position calculations
    5. Use SCOPES for repeated structures - avoids coordinate bloat
    
    *   Use `\pgfmathsetmacro` for base dimensions only:
        ```latex
        \pgfmathsetmacro{\containerWidth}{3.8}
        \pgfmathsetmacro{\containerHeight}{2.6}
        \pgfmathsetmacro{\waterLevel}{1.6}
        ```
    *   Define reusable styles with `\tikzset` only for custom objects. Preserve
        tikzphysics v1.2 public mechanics styles, path connections, and semantic anchors.

    **Use Calc-Based Relative Positioning (CRITICAL - PREFERRED):**
    *   Use `$(node.anchor)+(x,y)$` to chain nodes from each other:
        ```latex
        \node[physicsceiling, minimum width=3cm] (C) at (0,0) {};
        \draw (C.surface) -- ++(0,-0.5) coordinate (mount);
        \node[physicspulley] (P) at (mount) {};
        \node[physicsblock] (R) at ($(P.east)+(0,-2)$) {$m_1$};
        \node[physicsblock] (L) at ($(P.west)+(0,-2.5)$) {$m_2$};
        \draw[rope] (L.north) to[over pulley=P] (R.north);
        ```
    *   Do not approximate the string with lines meeting pulley compass anchors.

    **Use Semantic Anchors for Labels and Connections:**
        ```latex
        \draw[physicsspring] (wall) -- node[midway, above=3pt] {$k$} (mass.west);
        \draw[dashed] (A) -- (B) node[midway, above] {$d$};
        ```
    *   Springs are path decorations in v1.2: use `\draw[physicsspring] (A) -- (B);`
        with `node[midway]` for labels. Do not treat a spring as a node or use
        the removed `start`, `end`, or `coil-*` anchors.

    **Repeated Structures - Use Scope with Shift:**
    *   For similar structures side-by-side (e.g., two containers), use `\begin{scope}[xshift=...]` instead of duplicating code:
        ```latex
        \pgfmathsetmacro{\scopeShift}{\containerWidth + 1.5}
        \begin{scope}[xshift=0cm]
            \draw (0,0) rectangle (\containerWidth, \containerHeight);
            \node[physicsblock] (blockA) at (...) {};
        \end{scope}
        \begin{scope}[xshift=\scopeShift cm]  % Same code, just shifted!
            \draw (0,0) rectangle (\containerWidth, \containerHeight);
            \node[physicsblock] (blockB) at (...) {};
        \end{scope}
        ```
    *   BAD: Duplicating code with `(5.2+\blockX, \blockY)` everywhere
    *   GOOD: Use scope to shift, then use same local coordinates inside each scope
    
    **Simple Plots - Use \draw plot with domain/samples:**
    *   For schematic curves, use `\draw plot` with actual functions:
        ```latex
        \draw[thin, ->] (0,0) -- (3,0) node[right] {$t$};
        \draw[thin, ->] (0,-1) -- (0,1) node[above] {$y$};
        \draw[thick] plot[domain=0:2.5, samples=50] (\x, {sin(4*\x r)*exp(-0.5*\x)});
        ```
    *   Use `plot[domain=a:b, samples=N]` - NOT `plot[smooth, tension=...]`
    *   Keep axes `thin`, data curves `thick`
    
    **tikzphysics v1.2 (for mechanical diagrams):**
    *   Use collision-safe shapes such as `physicsblock`, `physicsspring`,
        `physicspulley`, `physicsground`, `physicswedge`, `physicsramp`, and
        `physicscurvedramp`.
    *   Use semantic anchors for contact geometry and
        `\draw[rope] (start) to[over pulley=pulley] (end)` for exact tangent strings.
    *   Do not recreate these objects with local `\tikzset` styles or approximate
        pulley ropes. Use `kinematikz` only for a pivot or specialized support glyph.
        ```latex
        \node[physicsground, minimum width=5cm] (G) at (0,0) {};
        \node[physicsblock, anchor=south] (B) at (G.top-40) {$m$};
        \node[physicspulley] (P) at ($(G.top-right)+(0.5,0.2)$) {};
        ```
"""

# Shorter version for prompts that don't need full examples
TIKZ_GUIDELINES_SHORT = r"""
    **TikZ Variable Guidelines (CRITICAL):**
    *   Use `\pgfmathsetmacro` for base dimensions with camelCase names.
    *   Use tikzphysics v1.2 shapes (`physicsblock`, `physicspulley`,
        `physicsground`, `physicswedge`, and ramps) for mechanics objects.
    *   **Calc-based positioning (PREFERRED):** Use `$(node.anchor)+(x,y)$` to chain nodes.
    *   **Also OK:** Use `[below of=node, xshift=..., yshift=...]` for relative positioning.
    *   **Labels on lines/springs:** Use `node[midway, right]` - NOT separate position calculations.
    *   **Springs/Coils:** Use `\draw[physicsspring] (A) -- (B);` with
        `node[midway]` labels. The spring is a path decoration, not a node.
    *   **Repeated Structures:** Use `\begin{scope}[xshift=...]` instead of duplicating code.
    *   **Simple plots:** Use `\draw plot[domain=0:2, samples=50] (\x, {sin(\x r)});` - thin axes, thick curves.
    *   **KinemaTikZ:** Reserve it for pivots and specialized support glyphs not
        supplied by tikzphysics.
"""

# LaTeX formatting rules - shared across all scanner prompts
LATEX_FORMATTING_RULES = r"""
## Strict LaTeX Formatting Rules

Adhere to these rules meticulously:

*   **Math Mode:** Use `$ ... $` for *all* inline math.
*   **Macros:** Always use `{}`: `\vec{a}`, `\dfrac{a}{b}`.
*   **Vectors:** Use `\vec{a}` for generic vectors and `\hat{i}`, `\hat{j}`, `\hat{k}` for unit vectors.
- Fractions: Use `\dfrac{a}{b}` everywhere, including inline math.
*   **Parentheses/Brackets:** Use `\left( ... \right)`, `\left[ ... \right]`, `\left| ... \right|`. **Do not use** `\bigl`, `\bigr`, `\Bigl`, `\Bigr`, etc.
*   **Intertext rule:** Inside `\intertext{...}`, do not use `\text{...}`. Use plain text and wrap math with `$...$`.
"""

# pgfplots axis environment example
PGFPLOTS_EXAMPLE = r"""
    *   **For graphs/plots with axes:** Use pgfplots `axis` environment:
        ```latex
        \begin{center}
        \begin{tikzpicture}
        \begin{axis}[
            axis lines = middle,
            xlabel = {$t$ (s)},
            ylabel = {$x$ (m)},
            xmin = 0, xmax = 10,
            ymin = -5, ymax = 10,
            grid = major,
            grid style = {dashed, line width=0.1pt, black!20},
            xtick = {0,1,2,3,4,5,6,7,8,9,10},
            ytick = {-5,0,5,10},
            tick label style = {font=\footnotesize},
            width = 8cm,
            height = 5cm,
        ]
        \addplot[thick] coordinates {(0,0) (1,-5) (2,0) (3,5)};
        \end{axis}
        \end{tikzpicture}
        \end{center}
        ```
"""

# Physics solution structure guidelines
SOLUTION_STRUCTURE = r"""
## Physics Solution Structure

**For Kinematics/Dynamics:**
```latex
\begin{solution}
\begin{align*}
    \intertext{Using Newton's second law:}
    F &= ma \\
      &= 2 \times 5 \\
      &= 10 \ \mathrm{N}
\end{align*}
\end{solution}
```

**For Energy/Work Problems:**
```latex
\begin{solution}
\begin{align*}
    \intertext{By conservation of energy:}
    \dfrac{1}{2}mv^2 &= mgh \\
    v &= \sqrt{2gh} \\
      &= \sqrt{2 \times 9.8 \times 5} \\
      &= 9.9 \ \mathrm{m/s}
\end{align*}
\end{solution}
```

**For Circuit Problems:**
```latex
\begin{solution}
\begin{align*}
    \intertext{Using Kirchhoff's voltage law:}
    \mathcal{E} - IR_1 - IR_2 &= 0 \\
    I &= \dfrac{\mathcal{E}}{R_1 + R_2} \\
      &= \dfrac{12}{4 + 6} \\
      &= 1.2 \ \mathrm{A}
\end{align*}
\end{solution}
```
"""

__all__ = [
    "TIKZ_GUIDELINES",
    "TIKZ_GUIDELINES_SHORT",
    "LATEX_FORMATTING_RULES",
    "PGFPLOTS_EXAMPLE",
    "DIAGRAM_PLACEHOLDER",
    "PASSAGE_DIAGRAM_INLINE",
    "OPTIONS_WITH_DIAGRAMS",
    "SOLUTION_STRUCTURE",
]
