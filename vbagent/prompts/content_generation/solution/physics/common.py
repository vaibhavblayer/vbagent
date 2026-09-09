"""Common components for physics solution generation prompts.

Shared guidelines, formatting rules, and templates used across
all physics question types for solution generation.
"""

from dataclasses import dataclass

from vbagent.prompts.latex_style import solution_style_rules

from ...mcq_format import MCQ_ANSWER_FORMAT_RULES


@dataclass(frozen=True)
class PhysicsTopicPrompts:
    """The three supported prompt variants for one physics topic."""

    subjective: str
    mcq_sc: str
    mcq_mc: str

    def for_question_type(self, question_type: str) -> str:
        """Select a prompt while preserving the historical subjective fallback."""
        if question_type == "mcq_sc":
            return self.mcq_sc
        if question_type == "mcq_mc":
            return self.mcq_mc
        return self.subjective

# LaTeX formatting rules for physics solutions (matches format_checker standards)
LATEX_FORMATTING_RULES = r"""
## LaTeX Formatting Rules (CRITICAL - Follow Exactly)

### Solution Structure
- Use \begin{solution}...\end{solution} environment
- Use align* environment DIRECTLY inside solution
- Use \intertext{} for brief text between equation lines
- Multiple align* blocks ONLY when diagram/table interrupts flow
- NO blank lines inside align*
- Keep solution CONCISE - show key steps, omit trivial algebra
- Do NOT use \boxed{} for final answers - just plain result

### Align* Rules (CRITICAL)
- Align equations at = using &
- End lines with \\
- Keep ONE step per line
- Variable repetition rule (CRITICAL):
  * First line: variable &= expression
  * Intermediate lines: &= expression (NO variable on LHS)
  * Last line: can have variable for final answer
  
**BAD (repetitive variable on LHS):**
```latex
t &= \dfrac{1}{\sqrt{g}} \int_{0}^{l} x^{-1/2} \, dx \\
t &= \dfrac{1}{\sqrt{g}} \left[ 2\sqrt{x} \right]_{0}^{l} \\
t &= 2\sqrt{\dfrac{l}{g}} \\
t &= 2\sqrt{\dfrac{2.45}{9.8}} \\
t &= 1.0 \ \mathrm{s}
```

**GOOD (clean, no repetition):**
```latex
t &= \dfrac{1}{\sqrt{g}} \int_{0}^{l} x^{-1/2} \, dx \\
  &= 2\sqrt{\dfrac{l}{g}} \\
  &= 1.0 \ \mathrm{s}
```

**Another example:**
```latex
% BAD:
F &= ma \\
F &= 2 \times 5 \\
F &= 10 \ \mathrm{N}

% GOOD:
F &= ma \\
  &= 2 \times 5 \\
  &= 10 \ \mathrm{N}
```

### Math Mode
- Use $ ... $ for ALL inline math (variables, numbers with units, equations)
- Math within \intertext{} must use $ ... $
- NO \text{...} inside \intertext{} - use plain prose and wrap only math in $...$

### Physics Notation
- Vectors: \vec{v}, unit vectors: \hat{i}, \hat{j}, \hat{k}
- Fractions: Use `\dfrac{a}{b}` everywhere, including inline math.
- Parentheses: \left( ... \right), \left[ ... \right], \left| ... \right|
- NO \bigl, \bigr, \Bigl, \Bigr sizing commands
- Units: \mathrm{} for units: 10 \ \mathrm{m/s}, 5 \ \mathrm{kg}
- Spacing: spaces around = in equations

### Diagram Placement
- Place diagrams in \begin{center}...\end{center} between align* blocks
- Use \begin{tikzpicture}...\end{tikzpicture} for TikZ diagrams
- Diagrams interrupt the flow, requiring separate align* blocks before and after

### Diagram Decision (IMPORTANT)
- Before finalizing, decide whether a visual would materially simplify the
  reader's understanding of the setup, geometry, forces, motion, circuit,
  optics, graph, or other spatial relationship.
- When a diagram would clarify the reasoning, include one even if the original problem image has no diagram.
  Prefer a concise, explanatory diagram over adding decorative artwork.
- For a simple diagram, write the TikZ directly in `solution_latex`. For a
  complex diagram, use `diagram_requirements` so the specialist can generate
  it.
- Every non-empty item in `diagram_requirements` MUST have the exact matching
  marker `% DIAGRAM PLACEHOLDER: <diagram_id>` in `solution_latex`, at the
  intended location. Use the same `diagram_id` in both places.
- Never request a diagram without its marker. A requirement without a marker
  cannot be positioned reliably in the finished solution.

### Alternate Solution Decision
- Decide whether a genuinely different and useful solution method would help
  the learner. Set `alternate_solution_recommended` to `true` only when it
  would add meaningful pedagogical value; use `false` for routine, direct, or
  one-method problems.
- When it is `true`, set `alternate_solution_hint` to one concise instruction
  naming the preferred alternate method, such as "Use conservation of energy
  instead of Newton's laws". Do not write the alternate solution itself.
- When it is `false`, set `alternate_solution_hint` to `null`.

### Inline TikZ in Solutions (Encouraged)

For SIMPLE diagrams, write the TikZ code directly in the solution instead of
using DIAGRAM_REQUIREMENT placeholders. This produces better results because
the diagram is tailored exactly to the solution context.

**Write TikZ directly when:**
- Simple v-t, x-t, a-t graphs (3-5 lines of draw commands)
- Quick number lines or inequalities
- Simple force arrows or vector diagrams
- Simple mechanics geometry using tikzphysics v1.2 semantic shapes, anchors, and paths
- Basic geometric sketches (triangle, circle with labels)
- Simple circuit with 2-3 components

**Use DIAGRAM_REQUIREMENT placeholder when:**
- Complex circuits (5+ components, Wheatstone bridge, etc.)
- Detailed FBDs with many forces
- Optics ray diagrams (multiple lenses/mirrors)
- Complex organic chemistry structures

**Example: Simple v-t graph inline**
```latex
\begin{center}
\begin{tikzpicture}
\draw[thin, ->] (0,0) -- (4,0) node[right] {$t$};
\draw[thin, ->] (0,0) -- (0,2.5) node[above] {$v$};
\draw[thick] (0,0) -- (2,2) -- (4,2);
\draw[dashed, thin] (2,0) node[below, font=\tiny] {$t_1$} -- (2,2);
\node[left, font=\tiny] at (0,2) {$v_0$};
\end{tikzpicture}
\end{center}
```

**Example: Simple circuit inline**
```latex
\begin{center}
\begin{tikzpicture}
\draw (0,0) to[battery1, l={$V$}] (0,2)
      to[R, l={$R$}] (3,2) to (3,0) to (0,0);
\end{tikzpicture}
\end{center}
```

**CircuiTikZ label rule**: ALWAYS wrap `l=`, `i=`, `v=` values in `{}`:
- ✅ `l={$R_1$}`, `l={$R=5\Omega$}`, `i={$I$}`
- ❌ `l=$R_1$`, `l=$R=5\Omega$` — these BREAK

**TikZ style rules for inline diagrams:**
- NO colors (no `blue`, `red`, etc.) — use solid/dashed/dotted
- NO inline `>=latex` or `\tikzset` — already set globally
- For mechanics, preserve collision-safe tikzphysics styles (`physicsblock`,
  `physicspulley`, surfaces, wedges, and ramps). Draw springs as
  `\draw[physicsspring] (A) -- (B);` and prefer
  `\draw[rope] (A) to[over pulley=P] (B);` for pulley strings. Keep
  `\physicsstringoverpulley` only for compatibility. Do not hand-build these objects.
- Use `thin, ->` for axes, `thick` for main curves
- Use `font=\tiny` or `font=\footnotesize` for labels
- Wrap in `\begin{center}...\end{center}`
"""

LATEX_FORMATTING_RULES += MCQ_ANSWER_FORMAT_RULES + solution_style_rules("physics")

# Solution quality guidelines
SOLUTION_QUALITY = """
## Solution Quality Guidelines

### Clarity
- Start with given information
- State assumptions clearly
- Explain why the method applies; add text only for a new idea or a necessary transition
- Connect steps logically

### Rigor
- Use proper physics principles and laws
- Show dimensional analysis when helpful
- Verify answer makes physical sense
- Check limiting cases if applicable

### Completeness
- Address all parts of the question
- Show all significant steps
- Include units in final answer
- State answer clearly

### Pedagogy
- Explain WHY, not just HOW
- Highlight key concepts
- Point out common mistakes to avoid
- Provide physical intuition where possible
"""


def build_topic_prompts(
    *,
    subjective_intro: str,
    mcq_intro: str,
    mcq_mc_intro: str,
    topic_concepts: str,
    common_patterns: str,
    diagram_guidance: str,
    typical_mistakes: str,
    subjective_diagram_requirements: str = "List of diagrams needed",
) -> PhysicsTopicPrompts:
    """Compose the shared physics prompt structure around topic knowledge."""
    shared_guidance = (
        topic_concepts
        + "\n\n"
        + common_patterns
        + "\n\n"
        + diagram_guidance
        + "\n\n"
        + typical_mistakes
        + "\n\n"
        + LATEX_FORMATTING_RULES
    )

    subjective = (
        subjective_intro
        + "\n\n"
        + shared_guidance
        + "\n\n"
        + SOLUTION_QUALITY
        + """

## Output Format

Return a JSON object with:
- `solution_latex`: Complete solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: """
        + subjective_diagram_requirements
        + """
- `answer_type`: "subjective" or "integer"
- `answer_value`: Final numerical answer if integer type, null otherwise
- `alternate_solution_recommended`: `true` or `false`
- `alternate_solution_hint`: A string or `null`
"""
    )
    mcq_sc = (
        mcq_intro
        + "\n\n"
        + shared_guidance
        + """

## MCQ-Specific Guidelines

- Show key steps that lead to answer
- Eliminate obviously wrong options when helpful
- Verify answer matches one of the given options
- Keep solution concise but complete

## Output Format

Return a JSON object with:
- `solution_latex`: Solution in LaTeX with \\begin{solution}...\\end{solution}
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Correct lowercase option letter (e.g., "a", "b", "c", "d")
- `alternate_solution_recommended`: `true` or `false`
- `alternate_solution_hint`: A string or `null`
"""
    )
    mcq_mc = (
        mcq_mc_intro
        + "\n\n"
        + shared_guidance
        + """

## MCQ-MC Specific Guidelines

- Check each option independently
- Show reasoning for why each is correct/incorrect
- Multiple options can be correct

## Output Format

Return a JSON object with:
- `solution_latex`: Solution in LaTeX
- `diagram_requirements`: List of diagrams if needed
- `answer_type`: "mcq"
- `answer_value`: Comma-separated lowercase options (e.g., "a,c" or "b,d")
- `alternate_solution_recommended`: `true` or `false`
- `alternate_solution_hint`: A string or `null`
"""
    )
    return PhysicsTopicPrompts(subjective, mcq_sc, mcq_mc)

# Common physics packages needed
PHYSICS_PACKAGES = r"""
% Common packages for physics solutions
\usepackage{amsmath}      % align*, equation*
\usepackage{siunitx}      % \si{}, \unit{}
\usepackage{tikz}         % diagrams
\usepackage{tikzphysics}  % mechanics shapes and anchors
\usepackage{circuitikz}   % circuit diagrams
\usepackage{pgfplots}     % graphs
"""

# Template for solution with diagram
SOLUTION_WITH_DIAGRAM_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Initial reasoning about the setup}
\sum F &= ma \\
T - mg &= ma
\end{align*}

\begin{center}
\begin{tikzpicture}
% TikZ diagram code here
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{Continue from diagram}
a &= \dfrac{T - mg}{m} \\
  &= \dfrac{20 - 2 \times 9.8}{2} \\
  &= 0.2 \ \mathrm{m/s^2}
\end{align*}
\end{solution}
"""

# Template for simple solution (no diagram)
SOLUTION_SIMPLE_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Use Newton's second law for a mass of $2\,\mathrm{kg}$ with acceleration $5\,\mathrm{m/s^2}$.}
F &= ma \\
  &= 10 \ \mathrm{N}
\end{align*}
\end{solution}
"""

# Template for MCQ solution
SOLUTION_MCQ_TEMPLATE = r"""
\begin{solution}
\begin{align*}
\intertext{Brief analysis of the problem}
E &= \dfrac{kQ}{r^2} \\
  &= \dfrac{9 \times 10^9 \times 2 \times 10^{-6}}{(0.1)^2} \\
  &= 1.8 \times 10^6 \ \mathrm{N/C}
\end{align*}

Therefore, the correct option is (c).
\end{solution}
"""

__all__ = [
    "PhysicsTopicPrompts",
    "build_topic_prompts",
    "LATEX_FORMATTING_RULES",
    "SOLUTION_QUALITY",
    "PHYSICS_PACKAGES",
    "SOLUTION_WITH_DIAGRAM_TEMPLATE",
    "SOLUTION_SIMPLE_TEMPLATE",
    "SOLUTION_MCQ_TEMPLATE",
]
