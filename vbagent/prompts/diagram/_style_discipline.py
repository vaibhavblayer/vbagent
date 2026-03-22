"""Shared style discipline rules for all TikZ diagram agents.

These rules enforce clean, minimal, document-uniform TikZ output.
Injected automatically by DiagramAgent.create_agent() into every
diagram agent's system prompt.
"""

STYLE_DISCIPLINE = r"""
## Style Discipline (MANDATORY — applies to ALL diagrams)

### 1. NO Colors — Document-Level Uniformity
Do NOT apply any color to draws, fills, or nodes. No `blue`, `red`, `orange`,
`green`, `blue!70!black`, `red!70!black`, etc. The document preamble defines a
global `\tikzset` with consistent colors for forces, labels, and annotations.
Your job is structure and geometry — color is handled at the document level.

**BAD:**
```latex
\draw[->, thick, blue!70!black] (block.south) -- ++(0,-1.5) node[right] {$mg$};
\draw[->, thick, red!70!black] (block.east) -- ++(1.5,0) node[above] {$F$};
```

**GOOD:**
```latex
\draw[->, thick] (block.south) -- ++(0,-1.5) node[right] {$mg$};
\draw[->, thick] (block.east) -- ++(1.5,0) node[above] {$F$};
```

Exception: `fill=white` for backgrounds (pulleys, blocks) is fine.
Exception: `fill=blue!8` or similar very light fills for fluid/shading are fine.

### 2. NO Inline Arrow/Style Overrides
Do NOT set `>=latex`, `>=stealth`, `>=Stealth`, or `every node/.style` inside
`\begin{tikzpicture}`. These are set globally in the document preamble via
`\tikzset{>=latex, thick, every node/.append style={font=\small}}`.

**BAD:**
```latex
\begin{tikzpicture}
\tikzset{>=latex}  % Already set globally!
\tikzstyle{force}=[->, thick, draw=blue!70!black]  % No colors, no inline styles!
```

**GOOD:**
```latex
\begin{tikzpicture}
% Just draw — global styles handle arrow tips, thickness, node font
\draw[->] (0,0) -- (2,0) node[midway, above] {$F$};
```

Functional styles you SHOULD use: `->`, `<->`, `|<->|`, `dashed`, `dotted`,
`thick`, `very thick`, `thin`, `node[midway, right]`, `node[above]`,
`node[below left]`, `decorate`, `fill=white`.

### 3. Minimal Variables — Don't Over-Engineer
For diagrams under ~10 lines of draw commands, do NOT define `\pgfmathsetmacro`
variables. Just use literal coordinates. Variables are for repeated or
parameterized structures (3+ uses of the same dimension).

**BAD (for a simple 5-line FBD):**
```latex
\pgfmathsetmacro{\blockW}{2}
\pgfmathsetmacro{\blockH}{1.5}
\pgfmathsetmacro{\forceLen}{1.5}
\pgfmathsetmacro{\surfaceW}{5}
\node[draw, thick, minimum width=\blockW cm, minimum height=\blockH cm] ...
```

**GOOD:**
```latex
\node[draw, thick, minimum width=2cm, minimum height=1.5cm] (block) at (0,1.5) {$m$};
\draw[->] (block.south) -- ++(0,-1.5) node[right] {$mg$};
```

### 4. Prefer Simple TikZ Over pgfplots
For schematic graphs (v-t, x-t, phase diagrams, qualitative curves), use plain
TikZ `\draw` with `plot[domain=..., samples=...]`. Reserve `\begin{axis}` from
pgfplots ONLY for data-heavy plots that need grid, precise tick marks, or
multiple datasets with legends.

**Simple v-t graph — use TikZ:**
```latex
\begin{tikzpicture}
\draw[thin, ->] (0,0) -- (4,0) node[right] {$t$};
\draw[thin, ->] (0,0) -- (0,2.5) node[above] {$v$};
\draw[thick] (0,0) -- (1.5,2) -- (3.5,2);
\node[below, font=\tiny] at (1.5,0) {$t_1$};
\draw[dashed, thin] (1.5,0) -- (1.5,2);
\end{tikzpicture}
```

**Data plot with grid — use pgfplots:**
```latex
\begin{tikzpicture}
\begin{axis}[axis lines=middle, xlabel={$t$ (s)}, ylabel={$x$ (m)},
    xmin=0, xmax=10, ymin=0, ymax=50, grid=major,
    grid style={very thin, black!15}, width=7cm, height=5cm]
\addplot[thick, smooth] coordinates {(0,0)(2,8)(4,20)(6,32)(8,44)(10,50)};
\end{axis}
\end{tikzpicture}
```

### 5. Proportional Dimensions — Think Artistically
Before drawing, mentally lay out the diagram's bounding box and decide
proportional sizes for each element. The diagram should look balanced and
readable at typical document width (~12cm usable).

**Sizing guidelines:**
- Blocks/boxes: 1–2 cm wide, 0.8–1.5 cm tall (scale with context)
- Pulleys: 0.8–1.2 cm diameter
- Force arrows: 1–2 cm length (proportional to magnitude if multiple)
- Springs: 2–3 cm natural length
- Axes: 3–5 cm for simple plots, 6–8 cm for detailed plots
- Labels: use `font=\small` or `font=\footnotesize` for annotations
- Overall diagram: aim for 5–10 cm wide, 4–8 cm tall

**Think about vertical and horizontal balance:**
- If two blocks are side by side, make them the same size unless physics
  dictates otherwise (e.g., different masses shown by different sizes)
- Pulleys should be smaller than blocks they support
- Leave breathing room — don't cram elements together
- Inclined planes: use realistic angles (not too steep, not too shallow)

**BAD (disproportionate):**
```latex
\node[draw, minimum width=4cm, minimum height=3cm] (block) {};  % Giant block
\node[circle, draw, minimum size=0.3cm] (pulley) {};  % Tiny pulley
```

**GOOD (proportional):**
```latex
\node[draw, thick, minimum width=1.5cm, minimum height=1cm] (block) {$m$};
\node[circle, draw, thick, minimum size=1cm, fill=white] (pulley) {};
```

### 6. Output Cleanliness
- No `\usepackage` commands (preamble handles this)
- No `\documentclass`, `\begin{document}`, etc.
- No markdown code fences
- No explanatory text — just the TikZ code
- Start with `\begin{tikzpicture}` and end with `\end{tikzpicture}`
  (or `\def\OptionA{...}` for MCQ option diagrams)

### 7. Centering — Always Wrap in `\begin{center}`
Every `\begin{tikzpicture}...\end{tikzpicture}` block MUST be wrapped in
`\begin{center}...\end{center}` so diagrams are horizontally centered in the
document. The ONLY exception is MCQ option diagrams (inside `\def\OptionA{...}`
or `\task` environments) — those stay inline.

**GOOD (main/solution diagram):**
```latex
\begin{center}
\begin{tikzpicture}
\draw[->] (0,0) -- (2,0);
\end{tikzpicture}
\end{center}
```

**GOOD (MCQ option — no center):**
```latex
\def\OptionA{\begin{tikzpicture}...\end{tikzpicture}}
```
"""
