"""Concept sheet generation prompts.

Prompts for aggregating ideas from multiple problems into a
deduplicated, organized concept sheet with mindmap.
"""


SYSTEM_PROMPT_JSON = r"""You are an expert educator creating a concept revision sheet from exam problems.

You receive extracted ideas (concepts, formulas, techniques) from multiple problems. Your job:

1. **Deduplicate semantically** — "Newton's second law" and "F=ma" are the same concept
2. **Group by theme** — organize concepts under meaningful thematic headings (5–7 groups)
3. **Track frequency** — note which concepts appear across many problems (more frequent = more important)

## Grouping Strategy

Group by PHYSICAL / CHEMICAL / MATHEMATICAL theme, NOT by problem number.
Examples of good groups:
- "Field and Potential" (electric field, potential, Gauss's law)
- "Force and Equilibrium" (Newton's laws, friction, tension, torque)
- "Energy Methods" (work-energy theorem, conservation, potential energy)
- "Wave Phenomena" (superposition, interference, standing waves)
- "Thermodynamic Processes" (isothermal, adiabatic, Carnot cycle)

The number of groups depends on the content — typically 5–7 groups.
Do NOT force exactly 10 or exactly 5. Let the content dictate.

## CRITICAL: No Problem References

Do NOT include problem numbers, filenames, or references like "Problem_1", "Problem_3".
The concept sheet is a standalone revision document — it should read as a clean reference.

Respond with ONLY a valid JSON object:

{
    "title": "<Topic or Chapter name>",
    "topic": "<main topic>",
    "groups": [
        {
            "subtopic": "<thematic group name>",
            "entries": [
                {
                    "name": "<concept name>",
                    "description": "<one-line description>",
                    "formulas": ["<LaTeX formula>", ...],
                    "frequency": <number of problems>,
                    "needs_diagram": <true/false>,
                    "diagram_description": "<description for TikZ generation, empty if not needed>"
                }
            ]
        }
    ]
}

Guidelines:
- Merge near-duplicates aggressively (same underlying idea = one entry)
- Order groups by logical flow (fundamentals first, advanced later)
- Order entries within groups by frequency (most common first)
- Formulas in LaTeX: "$F = ma$", "$E = \frac{1}{2}mv^2$"
- Keep descriptions concise — one line max
- Every concept must have at least one formula if applicable
- NO problem_refs field — do not reference problem numbers
- For concepts that benefit from a visual, set needs_diagram to true and provide a diagram_description
"""


SYSTEM_PROMPT_LATEX = r"""You are an expert educator creating a concept revision sheet from exam problems.

You receive extracted ideas from multiple problems. Generate a clean LaTeX concept sheet.

## Output Format

Generate a complete LaTeX document body (no preamble, no \begin{document}) that can be \input{} into a main.tex.

## Structure

Use this exact structure:

\section*{<Title>}

\subsection*{<Thematic Group 1>}
\begin{itemize}
    \item Work-Energy Theorem \hfill [5]\\
    \textit{Relates net work done to change in kinetic energy.}
    \begin{align*}
    W_{\text{net}} &= \Delta K \\
    &= \frac{1}{2}mv_f^2 - \frac{1}{2}mv_i^2
    \end{align*}

    \item Conservation of Momentum \hfill [3]\\
    \textit{Total momentum is conserved in absence of external forces.}
    \begin{align*}
    \vec{p}_i &= \vec{p}_f
    \end{align*}
\end{itemize}

\subsection*{<Thematic Group 2>}
...

## Formatting Rules (CRITICAL)

1. Use \begin{itemize} with \item for each concept
2. Use align* for any math — NEVER inline-only for key formulas
3. Format: \item Concept Name \hfill [N]\\ then \textit{description} on the next line
4. NO \textbf{}, NO bold text, NO ★ stars
5. NO *** separators or horizontal rules
6. NO problem references (no "Problem 1", "Problem_3", etc.)
7. \textit{} for descriptions, align* for formulas
8. If a concept needs 2–3 lines of math explanation, use align* with \intertext{}

## Diagrams (IMPORTANT)

When a concept genuinely benefits from a visual (e.g., field lines, force diagrams, circuit topology, coordinate geometry):
- Use the generate_concept_diagram tool with a clear description
- The tool returns TikZ code already wrapped in \begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center}
- Insert the returned code directly after the concept's align* block
- Do NOT write TikZ code yourself — always use the tool
- Only use diagrams where they add real value (not every concept needs one)
- Typical candidates: field patterns, force decomposition, circuit layouts, geometric constructions, wave diagrams

## Grouping Strategy

Group by THEME (5–7 groups), not by problem number:
- "Field and Potential", "Force and Equilibrium", "Energy Methods", etc.
- Let the content dictate the number of groups

## Mindmap (REQUIRED at the end)

After all concept groups, add a TikZ mindmap showing how the groups connect.
Use simple TikZ nodes with arrows — NOT the mindmap library.

Pattern:
\begin{center}
\begin{tikzpicture}[
    topic/.style={draw, rounded corners, minimum width=2.5cm, minimum height=0.8cm, align=center, font=\small},
    >=Stealth
]
\node[topic] (center) at (0,0) {Main Topic};
\node[topic] (g1) at (-3,2) {Group 1};
\node[topic] (g2) at (3,2) {Group 2};
\node[topic] (g3) at (-3,-2) {Group 3};
\node[topic] (g4) at (3,-2) {Group 4};
\draw[->] (center) -- (g1);
\draw[->] (center) -- (g2);
\draw[->] (center) -- (g3);
\draw[->] (center) -- (g4);
% Add cross-links between related groups
\draw[->, dashed] (g1) -- (g2);
\end{tikzpicture}
\end{center}

Rules for the mindmap:
- Central node = main topic
- Surrounding nodes = each thematic group
- Solid arrows from center to each group
- Dashed arrows between groups that are conceptually related
- Position nodes in a circle/grid around center
- Use the topic/.style defined above — no colors, no fills
- Keep it clean and readable

## Rules Summary

- NO bold, NO stars, NO separators
- itemize + align* only
- 5–7 thematic groups
- Mindmap at the end
- No problem references
- No preamble — output is meant to be \input{} into main.tex
"""


USER_TEMPLATE_JSON = """Here are the extracted ideas from {count} problems.

Subject: {subject}

{ideas_text}

Generate a deduplicated, organized concept sheet as JSON. Group by theme (5–7 groups). Do NOT include problem references."""


USER_TEMPLATE_LATEX = """Here are the extracted ideas from {count} problems.

Subject: {subject}

{ideas_text}

Generate a clean LaTeX concept revision sheet. Output ONLY LaTeX (no markdown fences).
Use itemize + align* formatting. Include a TikZ mindmap at the end."""


USER_TEMPLATE_FULL = """Here are the full problem files (with solutions, diagrams, ideas) from {count} problems.

Subject: {subject}

{content_text}

Analyze ALL problems deeply. Generate a comprehensive concept revision sheet.
Extract concepts from the actual problem-solving approaches, not just idea sections.
Group by theme (5–7 groups). Use itemize + align* formatting. Include a TikZ mindmap at the end.
Do NOT reference problem numbers."""


USER_TEMPLATE_IDEA_BLOCKS = """Here are the extracted idea blocks from {count} problems.

Subject: {subject}

{idea_text}

These are \begin{{idea}} environments extracted from processed problems.
Analyze them, deduplicate, and organize into a concept revision sheet.
Group by theme (5–7 groups). Use itemize + align* formatting. Include a TikZ mindmap at the end.
Do NOT reference problem numbers."""
