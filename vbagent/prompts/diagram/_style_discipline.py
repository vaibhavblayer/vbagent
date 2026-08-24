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

### 6. Vector Notation — Always `\vec{}`
Use `\vec{}` for ALL vector quantities. NEVER use `\mathbf{}`, `\boldsymbol{}`,
or `\textbf{}` for vectors.

- ✅ `$\vec{B}$`, `$\vec{F}$`, `$\vec{v}$`, `$\vec{E}$`, `$\vec{p}$`
- ❌ `$\mathbf{B}$`, `$\boldsymbol{F}$`, `$\textbf{v}$`

### 7. Coordinate Discipline — Build Geometry, Do Not Guess It
Prefer coordinates that reveal the construction. Start from one or a few named
base points, then build nearby geometry with relative moves, node anchors, and
the `calc`/`intersections` libraries.

**Preferred order:**
1. Named nodes and anchors: `(block.east)`, `(pulley.south)`, `(O)`
2. Relative movement: `-- ++(1,0)`, `-- ++(0,1)`, `-- ++(45:2)`
3. Exact TikZ calculations: `($(A)!0.5!(B)$)`, `($(P)+(0,1)$)`, `(A -| B)`
4. Named-path intersections for points determined by two lines or curves
5. Absolute coordinates only for essential base points and actual plotted data

For schematic spacing, prefer integers and simple fractions such as `0.25`,
`0.5`, `1`, `1.5`, `2`, and `3`. Do NOT invent precision with values such as
`0.145`, `0.27`, or `(2.347,-1.892)` merely to make elements meet visually.

**BAD — repeated origins and guessed derived points:**
```latex
\draw (0,0) -- (1,0);
\draw (0,0) -- (0,1);
\coordinate (meeting) at (2.347,-1.892);
\draw (0.145,0.27) -- (1.73,2.18);
```

**GOOD — one base point, simple relative vectors, exact relationships:**
```latex
\coordinate (O) at (0,0);
\draw (O) -- ++(1,0);
\draw (O) -- ++(0,1);
\coordinate (M) at ($(A)!0.5!(B)$);
\draw (block.east) -- ++(1.5,0) coordinate (ropeEnd);
\path[name intersections={of=lineA and lineB, by=meeting}];
```

Use polar relative coordinates when direction and length are known; for example,
`(O) -- ++(30:2)` is clearer and more exact than `-- ++(1.732,1)`. If the same
dimension appears three or more times, define it once and reuse it.

**Important exception:** do not round coordinates that are actual problem data,
measured values, roots/intersections being plotted, or necessary curve-control
parameters. Keep those exact with expressions such as `{sqrt(5)}` or compute
them with PGF/TikZ. Simplify construction geometry, not mathematical content.

### 8. Output Cleanliness
- No `\usepackage` commands (preamble handles this)
- No `\documentclass`, `\begin{document}`, etc.
- No markdown code fences
- No explanatory text — just the TikZ code
- Start with `\begin{tikzpicture}` and end with `\end{tikzpicture}`
  (or separate `\def\OptionA{...}` definitions for MCQ option diagrams, or
  separate `\def\MatchA{...}` definitions for diagrams consumed inside a
  match-the-column table). An independent labeled-panel collection is the
  additional exception described below and starts with `\begingroup`.

### 9. Independent Labeled Panels — Let LaTeX Own the Layout
When a problem contains several independent figures labeled (a), (b), ... or
(i), (ii), ... for the student to compare, classify, or discuss, do NOT draw
one giant TikZ canvas and position the figures with `scope[shift=...]`.

Instead:
- Give every panel its own self-contained `tikzpicture` and local coordinates.
- Define reusable panel commands such as `\DiagramOne`, `\DiagramTwo`, etc.
  Never write `\Diagram_1`: the underscore is not part of a normal TeX command
  name.
- Wrap the definitions and their use in `\begingroup ... \endgroup`, so common
  names cannot collide with diagrams from another question.
- Let `enumerate` own the visible labels; do not draw `(i)` or `(a)` as TikZ
  nodes.
- Use `multicols` for the page layout, normally two columns, and use local
  enumitem labels such as `[label=(\roman*), leftmargin=*]`.
- Put shared drawing primitives such as axes in one local macro and reuse them.
- A panel command may be reused later in the same grouped artifact; do not
  redraw the same panel with a second set of coordinates.

```latex
\begingroup
\def\PanelAxes{%
  \draw[thin,<->] (-2,0) -- (2,0) node[right] {$X$};
  \draw[thin,<->] (0,-1.5) -- (0,1.5) node[above] {$Y$};
  \node[below right] at (0,0) {$O$};
}
\def\DiagramOne{%
  \begin{tikzpicture}[x=0.75cm,y=0.75cm,
      baseline=(current bounding box.center)]
    \PanelAxes
    \draw[thick] plot[domain=-1.2:1.2,samples=80]
      ({\x*\x},{\x});
  \end{tikzpicture}%
}
\def\DiagramTwo{%
  \begin{tikzpicture}[x=0.75cm,y=0.75cm,
      baseline=(current bounding box.center)]
    \PanelAxes
    \draw[thick] (0,0) circle[radius=0.8];
  \end{tikzpicture}%
}
\begin{multicols}{2}
\begin{enumerate}[label=(\roman*),leftmargin=*,itemsep=1em]
  \item {\centering\DiagramOne\par}
  \item {\centering\DiagramTwo\par}
\end{enumerate}
\end{multicols}
\endgroup
```

This rule is for independent panels. Within one coherent physical setup or one
single diagram containing repeated internal structures, shifted scopes can
still be appropriate.

### 10. Centering — Always Wrap in `\begin{center}`
Every `\begin{tikzpicture}...\end{tikzpicture}` block MUST be wrapped in
`\begin{center}...\end{center}` so diagrams are horizontally centered in the
document. The exceptions are MCQ option diagrams (inside `\def\OptionA{...}`)
matching-table cell diagrams (inside `\def\MatchA{...}`), and independent panel
commands consumed by the grouped `multicols`/`enumerate` structure above; those
stay inline and are centered locally by their list items.

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

**GOOD (matching-table cell — no center):**
```latex
\def\MatchA{\begin{tikzpicture}[baseline=(current bounding box.center)]...\end{tikzpicture}}
```

When asked for diagrams embedded in a match-the-column table, create one
self-contained `\def\MatchX{...}` per diagram-bearing row. Never combine the
rows into one large TikZ picture, never include the row label inside the
diagram, and never use `\OptionX` for table cells.
"""
