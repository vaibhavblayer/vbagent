"""Common prompt components for biology scanner prompts.

Biology-specific TikZ guidelines, LaTeX formatting rules, and notation.
"""

from .._shared import (
    DIAGRAM_PLACEHOLDER,
    PASSAGE_DIAGRAM_INLINE,
    OPTIONS_WITH_DIAGRAMS_BIOLOGY as OPTIONS_WITH_DIAGRAMS,
)

# Biology-specific TikZ guidelines
TIKZ_GUIDELINES = r"""
    **TikZ Guidelines for Biology Diagrams:**

    **PRINCIPLES:**
    1. Use TikZ for cell diagrams, flowcharts, life cycles, and graphs
    2. Keep diagrams clean and biologically accurate
    3. Label all structures clearly
    4. Use arrows to show processes and relationships

    **Cell/Organelle Diagrams (TikZ):**
    ```latex
    \begin{tikzpicture}
    \draw[thick] (0,0) ellipse (2 and 1.2);  % Cell membrane
    \draw[thick,fill=gray!20] (0,0) circle (0.5);  % Nucleus
    \node at (0,0) {\small Nucleus};
    \end{tikzpicture}
    ```

    **Flowcharts (TikZ):**
    ```latex
    \begin{tikzpicture}[node distance=1.2cm]
    \node[draw,rounded corners] (a) {Step 1};
    \node[draw,rounded corners,below of=a] (b) {Step 2};
    \draw[->] (a) -- (b);
    \end{tikzpicture}
    ```

    **Graphs (pgfplots):**
    ```latex
    \begin{tikzpicture}
    \begin{axis}[xlabel={Time},ylabel={Population}]
    \addplot coordinates {(0,10)(1,20)(2,40)(3,80)};
    \end{axis}
    \end{tikzpicture}
    ```
"""

TIKZ_GUIDELINES_SHORT = r"""
    **TikZ Guidelines for Biology:**
    *   Use TikZ for cell diagrams, flowcharts, life cycles
    *   Label all structures clearly
    *   Use arrows for processes and relationships
"""

# Biology-specific LaTeX formatting rules
LATEX_FORMATTING_RULES = r"""
## Biology LaTeX Formatting Rules

**Scientific Names:**
*   Italicise genus and species: \textit{Homo sapiens}, \textit{Escherichia coli}
*   Genus capitalised, species lowercase: \textit{Rana tigrina}

**Key Terms:**
*   Bold key biological terms on first use: \textbf{mitosis}, \textbf{photosynthesis}

**Chemical Formulas in Biology:**
*   Use mhchem for molecules: \ce{CO2}, \ce{O2}, \ce{H2O}, \ce{ATP}, \ce{NADH}
*   Glucose: \ce{C6H12O6}

**Units:**
*   Temperature: $37\,^\circ\text{C}$
*   Concentration: $\mu\text{mol/L}$, $\text{mg/dL}$
*   Length: $\mu\text{m}$, $\text{nm}$

**Processes and Reactions:**
*   Use arrows for processes: $A \rightarrow B$
*   Reversible: $A \rightleftharpoons B$
*   Enzyme above arrow: $A \xrightarrow{\text{enzyme}} B$

**General Math:**
*   Use $...$ for inline math
*   Use \frac{a}{b} for fractions
*   Use \times for multiplication
"""

SOLUTION_STRUCTURE = r"""
## Biology Solution Structure

**For Conceptual MCQs:**
```latex
\begin{solution}
\begin{align*}
\intertext{Identify the key concept being tested.}
\intertext{Option (a): Incorrect — mitosis produces diploid cells, not haploid.}
\intertext{Option (b): Correct — meiosis produces haploid gametes.}
\intertext{Option (c): Incorrect — DNA replication occurs in S phase, not M phase.}
\intertext{Option (d): Incorrect — cytokinesis follows karyokinesis.}
\intertext{Therefore, the correct option is (b).}
\end{align*}
\end{solution}
```

**For Calculation-Based MCQs:**
```latex
\begin{solution}
\begin{align*}
\intertext{Apply the relevant formula.}
\text{Cardiac output} &= \text{Heart rate} \times \text{Stroke volume} \\
&= 72 \times 70 \\
&= 5040 \text{ mL/min}
\end{align*}
Therefore, the correct option is (c).
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
