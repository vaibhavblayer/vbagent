"""Truly shared scanner prompt components.

Constants that are identical (or near-identical) across all subjects.
Subject-specific constants live in each subject's common.py.
"""

# Diagram placeholder instruction - scanner outputs placeholder, TikZ agent generates actual code
DIAGRAM_PLACEHOLDER = r"""
    **Diagram Handling (IMPORTANT):**
    *   If the image contains a diagram, output ONLY a placeholder:
        ```latex
        \begin{center}
            \input{diagram}
        \end{center}
        ```
    *   Do NOT generate TikZ/chemfig code during scanning - the diagram agent will generate it separately.
    *   Place the placeholder immediately after the `\item` line (before options/tasks).
"""

# Passage diagram - generate actual TikZ inline (not placeholder)
PASSAGE_DIAGRAM_INLINE = r"""
    **Diagram Handling for Passage (IMPORTANT):**
    *   If the passage contains a diagram, generate the ACTUAL TikZ code inline:
        ```latex
        \begin{center}
        \begin{tikzpicture}
            % Your TikZ code here
        \end{tikzpicture}
        \end{center}
        ```
    *   Do NOT use `\input{diagram}` placeholder for passage diagrams.
    *   Generate complete, compilable TikZ code directly in the passage.
    *   Place the diagram after the passage text, before the questions.
"""


def options_with_diagrams(forbidden_examples: str = "") -> str:
    """Build the OPTIONS_WITH_DIAGRAMS prompt with subject-specific forbidden examples.

    Args:
        forbidden_examples: Subject-specific forbidden code examples.
            Physics/Math: tikzpicture blocks.
            Chemistry: chemfig commands.
            If empty, uses a generic default.

    Returns:
        Complete OPTIONS_WITH_DIAGRAMS prompt string.
    """
    if not forbidden_examples:
        forbidden_examples = r"""    ❌ \begin{tikzpicture}...\end{tikzpicture}
    ❌ \chemfig{...}
    ❌ \def\OptionA{\begin{tikzpicture}...}
    ❌ Any actual TikZ/chemfig/diagram code for options
    ❌ Extracting the diagram code yourself"""

    return r"""
    **CRITICAL - Options with Diagrams/Graphs:**
    
    **ABSOLUTE RULE: If MCQ options show diagrams/graphs, you MUST use placeholders ONLY.**
    
    **STEP 1: Detect if options have diagrams**
    - Look for: graphs, diagrams, structures, figures in options (a), (b), (c), (d)
    - If YES → Follow STEP 2
    - If NO (text-only options) → Extract text normally
    
    **EXCEPTION — Truth tables and data tables in options:**
    Truth tables, data tables, and simple grids are NOT diagrams.
    Extract them as plain LaTeX using the tabular environment.
    Place `\ans` AFTER `\end{tabular}`, not inside it:
    ```latex
    \task \begin{tabular}{|c|c|c|} \hline $A$ & $B$ & $Y$ \\ \hline 0 & 0 & 0 \\ \hline 0 & 1 & 1 \\ \hline 1 & 0 & 1 \\ \hline 1 & 1 & 1 \\ \hline \end{tabular} \ans
    ```
    Do NOT use \OptionA placeholders or TikZ for tables.
    
    **STEP 2: Use ONLY placeholders (NO actual code)**
    ```latex
    %% OPTIONS_DIAGRAMS: [brief description of what options show]
    \begin{tasks}(2)
        \task \OptionA
        \task \OptionB  
        \task \OptionC \ans
        \task \OptionD
    \end{tasks}
    ```
    
    **ABSOLUTELY FORBIDDEN when options have diagrams:**
""" + forbidden_examples + r"""
    
    **ONLY ALLOWED when options have diagrams:**
    ✅ \task \OptionA (placeholder)
    ✅ \task \OptionB (placeholder)
    ✅ %% OPTIONS_DIAGRAMS: [description]
    
    **Why:** The diagram agent will generate \def\OptionA{...} definitions separately.
    **Your job:** Identify which options have diagrams and use placeholders.
    **Not your job:** Extract or generate the actual diagram code.
"""


# Pre-built subject variants for backward compatibility
OPTIONS_WITH_DIAGRAMS_PHYSICS = options_with_diagrams(r"""    ❌ \begin{tikzpicture}...\end{tikzpicture}
    ❌ \def\OptionA{\begin{tikzpicture}...}
    ❌ Any actual TikZ/diagram code for options
    ❌ Extracting the diagram code yourself""")

OPTIONS_WITH_DIAGRAMS_CHEMISTRY = options_with_diagrams(r"""    ❌ \chemfig{-[:30]-[:-30]-[:30]}
    ❌ \chemfig{*6(=-=-=-)}
    ❌ \def\OptionA{\chemfig{...}}
    ❌ Any actual chemfig/TikZ code for options
    ❌ Extracting the structure code yourself""")

OPTIONS_WITH_DIAGRAMS_MATHEMATICS = options_with_diagrams(r"""    ❌ \begin{tikzpicture}...\end{tikzpicture}
    ❌ \def\OptionA{\begin{tikzpicture}...}
    ❌ Any actual TikZ/diagram code for options
    ❌ Extracting the diagram code yourself""")


__all__ = [
    "DIAGRAM_PLACEHOLDER",
    "PASSAGE_DIAGRAM_INLINE",
    "options_with_diagrams",
    "OPTIONS_WITH_DIAGRAMS_PHYSICS",
    "OPTIONS_WITH_DIAGRAMS_CHEMISTRY",
    "OPTIONS_WITH_DIAGRAMS_MATHEMATICS",
    "PROBLEM_FORMATTING_RULES",
    "SOLUTION_FORMATTING_RULES",
]


# Problem-only formatting rules (no solution instructions)
PROBLEM_FORMATTING_RULES = r"""
## Problem Extraction Rules

- Do NOT include `\begin{solution}` or any solution content.
- Do NOT include exam metadata (year, paper name, question number).
- Do NOT include example/exercise numbering prefixes (e.g., `Example 25.4`, `Q.5`).
- Use `$ ... $` for all inline math.
- Use `\frac{a}{b}` (not `\tfrac`).
- Use `\left( ... \right)` for auto-sized delimiters.
- Use `\vec{a}` for vectors, `\hat{i}` for unit vectors.
- Use `\,` for thin space before units: `10\,\mathrm{m/s}`.
- **Fill-in-the-blank answers:** Use `\underline{\hfill}` or `\underline{\hspace{2cm}}` for blank spaces. NEVER use raw underscores `____` (causes rendering errors).
"""

# Solution-only formatting rules
SOLUTION_FORMATTING_RULES = r"""
## Solution Formatting Rules

- Wrap solution in `\begin{solution} ... \end{solution}`.
- Use `align*` environment for multi-step calculations.
- Use `\intertext{...}` for brief text between equation lines.
- Inside `\intertext{}`, use plain text with `$...$` for math. Do NOT nest `\text{...}`.
- Keep one calculation step per line.
- No blank lines inside `align*`.
- State the final answer clearly (e.g., "Therefore, the correct option is (c).").
"""
