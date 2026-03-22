"""Common prompt components for chemistry scanner prompts.

Chemistry-specific TikZ guidelines, LaTeX formatting rules, and notation.
Shared constants (DIAGRAM_PLACEHOLDER, PASSAGE_DIAGRAM_INLINE, OPTIONS_WITH_DIAGRAMS)
are imported from the _shared module.
"""

from .._shared import (
    DIAGRAM_PLACEHOLDER,
    PASSAGE_DIAGRAM_INLINE,
    OPTIONS_WITH_DIAGRAMS_CHEMISTRY as OPTIONS_WITH_DIAGRAMS,
)

# Chemistry-specific TikZ guidelines
TIKZ_GUIDELINES = r"""
    **TikZ Guidelines for Chemistry Diagrams:**
    
    **PRINCIPLES:**
    1. Use chemfig for organic structures and Lewis structures
    2. Use mhchem for chemical equations
    3. Use TikZ for energy diagrams, orbital diagrams, and reaction coordinates
    4. Keep diagrams clean and chemically accurate
    
    **Organic Structures (chemfig):**
    ```latex
    \chemfig{H-C(-[2]H)(-[6]H)-C(-[2]H)(-[6]H)-H}  % Ethane
    \chemfig{*6(=-=-=-)}  % Benzene
    \chemfig{-[:30]-[:-30]-[:30]}  % Zigzag chain
    ```
    
    **Lewis Structures (chemfig with \lewis):**
    ```latex
    \chemfig{H-\lewis{2:4:,O}-H}  % Water with lone pairs
    \chemfig{\lewis{0:2:4:6:,N}(-[2]H)(-[4]H)(-[6]H)}  % Ammonia
    ```
    
    **Chemical Equations (mhchem):**
    ```latex
    \ce{2H2 + O2 -> 2H2O}
    \ce{H2SO4 + 2NaOH -> Na2SO4 + 2H2O}
    \ce{CH4 + 2O2 -> CO2 + 2H2O}
    ```
    
    **Energy Diagrams (TikZ/pgfplots):**
    ```latex
    \begin{tikzpicture}
    \draw[->] (0,0) -- (5,0) node[right] {Reaction coordinate};
    \draw[->] (0,0) -- (0,4) node[above] {Energy};
    \draw[thick,blue] (0.5,1) -- (2,1) node[midway,above] {Reactants};
    \draw[thick,blue] (2,1) .. controls (2.5,3) .. (3,1.5);
    \draw[thick,blue] (3,1.5) -- (4.5,1.5) node[midway,above] {Products};
    \end{tikzpicture}
    ```
"""


# Shorter version for prompts that don't need full examples
TIKZ_GUIDELINES_SHORT = r"""
    **TikZ Guidelines for Chemistry:**
    *   Use chemfig for organic structures: `\chemfig{-[:30]-[:-30]}`
    *   Use mhchem for equations: `\ce{H2 + O2 -> H2O}`
    *   Use TikZ for energy/orbital diagrams
    *   Keep structures chemically accurate
"""

# Chemistry-specific LaTeX formatting rules
LATEX_FORMATTING_RULES = r"""
## Chemistry LaTeX Formatting Rules

**Chemical Equations (mhchem package):**
*   Use `\ce{}` for all chemical formulas and equations
*   Examples:
    - `\ce{H2O}` for water
    - `\ce{H2SO4}` for sulfuric acid
    - `\ce{2H2 + O2 -> 2H2O}` for reactions
    - `\ce{CH3-CH2-OH}` for structural formulas
    - `\ce{Fe^{2+}}` for ions with charges
    - `\ce{<=>}` for equilibrium arrows

**Oxidation States:**
*   Use superscripts: `\ce{Fe^{3+}}`, `\ce{Mn^{7+}}`
*   In text: $\ce{Fe}$ has oxidation state $+3$

**Electron Configurations:**
*   Use: $1s^2 2s^2 2p^6 3s^2 3p^6$
*   Or: $[\ce{Ar}] 3d^{10} 4s^2$

**Thermodynamic Quantities:**
*   $\Delta H$ for enthalpy change
*   $\Delta G$ for Gibbs free energy
*   $\Delta S$ for entropy change
*   $K_{\text{eq}}$ for equilibrium constant
*   $K_{\text{a}}$ for acid dissociation constant

**Reaction Mechanisms:**
*   Use chemfig for arrow-pushing
*   Curved arrows: `\chemfig{-[:30]@{a}-[:-30]@{b}}` with `\chemmove`
*   Or describe mechanism steps in text

**General Math:**
*   Use `$ ... $` for inline math
*   Use `\frac{a}{b}` for fractions
*   Use `\left( ... \right)` for parentheses
"""




# Chemistry solution structure guidelines
SOLUTION_STRUCTURE = r"""
## Chemistry Solution Structure

**For Chemical Equations and Stoichiometry:**
```latex
\begin{solution}
\begin{align*}
    \ce{2H2 + O2 &-> 2H2O} \\
    \intertext{Molar ratio: 2:1:2}
    \text{Moles of } \ce{H2O} &= 2 \times \text{moles of } \ce{H2}
\end{align*}
\end{solution}
```

**For Equilibrium Problems:**
```latex
\begin{solution}
\begin{align*}
    K_{\text{eq}} &= \frac{[\ce{C}][\ce{D}]}{[\ce{A}][\ce{B}]} \\
    \intertext{At equilibrium:}
    K_{\text{eq}} &= \frac{(0.5)(0.5)}{(0.2)(0.3)} = 4.17
\end{align*}
\end{solution}
```

**For Thermodynamics:**
```latex
\begin{solution}
\begin{align*}
    \Delta G &= \Delta H - T\Delta S \\
    &= -285 - (298)(0.163) \\
    &= -333.6 \text{ kJ/mol}
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
