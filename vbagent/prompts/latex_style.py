"""Shared teaching and presentation rules for generated LaTeX.

Keep generation, inline/specialist diagrams, and repair prompts in agreement.
The version also invalidates cached content made before this contract.
"""

LATEX_STYLE_CONTRACT_VERSION = 1

DISPLAY_FRACTION_RULES = r"""
## Display Fractions (MANDATORY)
- Write every fraction as `\dfrac{numerator}{denominator}`, including inline
  mathematics, final answers, tables, and graph labels. Do not emit `\frac`
  or `\tfrac`. Always brace both arguments.
- Keep PGF numeric expressions as arithmetic, such as `2/3`; a typesetting
  command belongs in a math label, not in a plot expression or coordinate.
- Do not redefine fraction commands inside generated snippets. The document
  preamble handles compatibility for older content.
"""

SOLUTION_EXPLANATION_RULES = r"""
## Explanation: Method, Essential Work, Conclusion
- When generating a solution, briefly explain WHY the chosen method applies
  before using it. Usually one or two sentences suffice. Use `\intertext{}`
  for this explanation inside `align*`; use `$...$` for any inline mathematics.
- Explain the decisive mathematical or scientific observation, not a diary of
  the solving process. Do not restate the question or narrate each equation.
- Show all logically necessary steps, assumptions, cases, domain restrictions,
  and endpoint/attainment arguments. Omit routine arithmetic and intermediate
  algebra that add no insight. Concision must not create a gap in the proof.
- One meaningful step per displayed line is a layout rule, not a demand to
  display every arithmetic operation. A direct substitution may go straight
  to its simplified result. Keep enough detail for the intended learner.
- Use further `\intertext{}` only for a new idea, a justified transition, or
  an interpretation of a diagram. Avoid repeated setup/minimum/conclusion
  sentences that state the same fact. End with the answer once in the solution;
  a separately required answer-key field is still mandatory.
- Check the answer carefully, but do not append a second proof or routine
  verification unless it resolves a real ambiguity, restriction, or edge case.
- Retain useful graphs and diagrams. Explain the feature that supports the
  reasoning; a sketch illustrates a proof and does not replace justification.
- For faithful OCR of an existing solution, preserve the source's reasoning
  and all question data. These brevity rules govern newly written explanations,
  not deletion of content the user asked to transcribe.
"""

GRAPH_CLARITY_RULES = r"""
## Graph Clarity (inline plots, graph agents, and graph repair)
- Keep the graph when it helps explain the function, domain, range, or another
  relationship. Make the existing visual simpler; do not remove it for brevity.
- Use only annotations needed to read the graph or justify the solution.
  Preserve labels/data explicitly required by the question; do not label every
  sampled point, every intercept, or every repeated branch endpoint by default.
- Prefer sparse, meaningful axis ticks and open/filled endpoint markers over
  extra coordinate nodes. Do not write "open" or "closed" beside every marker.
  If the convention needs explaining, explain it once outside the plot.
- For a hollow pgfplots endpoint over a curve, draw the marker last with
  `only marks, mark=*, mark options={fill=white}`. The stroke-only `mark=o`
  does not mask the curve underneath, even if a fill color is supplied.
- Label only the extrema, discontinuities, asymptotes, or intersections relevant
  to this question. For a single curve, omit a legend and a repeated formula
  inside the axes unless identification is otherwise ambiguous. For multiple
  curves, choose either short direct labels or a compact legend, not both.
- When requesting a specialist diagram, include only essential labels in
  `diagram_requirements.labels`; do not make every explanatory observation a
  required node. Keep reasoning in the solution text.
- Treat supplied values and solution context as construction data, not a list
  of labels to invent. "Mark the minimum" means a point marker, not the words
  "global minimum". If exact coordinates are requested as ticks, use those
  ticks without a duplicate coordinate node. An empty label list requests no
  extra text beyond necessary axis names/ticks and explicit drawing actions.
- Indicate continuation with unobtrusive curve arrows when needed; do not add
  repeated limit statements such as $y\to\infty$ beside the curve tails.
- Default to no grid for a qualitative function sketch. Use a light, sparse
  grid only when requested or needed for reading values. Add guide lines only
  when they establish a needed coordinate, bound, or asymptote.
- Keep labels clear of curves, axes, markers, and other labels. First remove
  redundant nodes, then place remaining labels in free space with sensible
  anchors/offsets. Do not solve crowding by shrinking all text or distorting
  the mathematical coordinates. Allow room for display-style fractions.
- Preserve exact geometry and data, open/closed endpoints, holes, and separate
  branches. Never connect a jump with a segment that looks part of the graph.
- Show jumps with separate branches and endpoint markers. Do not add vertical
  jump arrows or full-height symmetry guides unless specifically needed.
- Before returning, review the graph at its intended size for unnecessary
  nodes, duplicate labels, overlaps, clipping, and misleading connections.
"""

DIAGRAM_SPECIFICATION_RULES = r"""
## Diagram Specifications: Mathematical Data vs Visible Annotations
Before populating `diagram_requirements`, identify the ONE learning purpose of
each diagram: what observation should the reader be able to make from it?

- `description`: state that purpose and the essential visible features. Do not
  turn the complete solution or every computed fact into a drawing request.
- `context` and `values`: provide enough exact information to draw correctly:
  the function, valid domain, branch intervals, endpoint inclusion, relevant
  extrema/asymptotes, and any specified data. These are construction data;
  supplying a value does NOT require printing it as text on the graph.
- `labels`: a minimal list of indispensable visible text, not an inventory of
  every point or feature. An empty list is valid. Ordinary axis names and
  values already readable from ticks need no additional node. For a minimum,
  choose either exact axis ticks OR one compact coordinate label, not both.
- `annotations`: only drawing actions that support the learning purpose, such
  as marking a minimum or shading a requested region. Do not use this field
  for solution prose, repeated formulas, "open/closed" text, or decorations.
- `mathematics_context`: distinguish the full mathematical domain/range from
  the finite viewing window. Choose a window that makes the relevant feature
  legible. For a repetitive piecewise function, a few representative branches
  are normally enough; show continuation without implying a finite endpoint.
- Do not request a symmetry line, tangent, extra intercept label, grid, legend,
  or jump arrow merely because it can be drawn. For a log-quadratic range plot,
  the curve and its attained minimum usually suffice. For a floor-function
  range plot, the separate branches and correct endpoint markers usually suffice.
- Specify what must be mathematically visible; leave anchors, offsets, and
  label placement to the graph agent. Preserve labels explicitly required by
  the question. Never withhold essential data just to make the spec shorter.
- If the same diagram is written inline, apply the same selection of features
  and annotations. Do not request a second specialist copy of an inline plot.
"""

MATHEMATICS_REASONING_RULES = r"""
## Mathematical Method Selection
- For domain/range questions about explicit real functions, include a function
  sketch unless a supplied graph already serves that purpose or the user asks
  for text only. Keep the graph even when the algebraic solution is short.
- For domain and range, explain what must be excluded and why every claimed
  output is attained. A minimum and unboundedness alone do not rule out gaps.
- For floor/piecewise functions, split where the formula changes. Distinguish
  continuity and monotonicity on each branch from global behavior; check jumps,
  endpoint inclusion, and overlap/gaps between branch ranges when relevant.
- For a composition, first determine the exact attainable values of the inner
  expression and apply the outer function's domain and mapping properties.
  An increasing outer function need not make the composition increasing in x.
- Motivate completing the square by the bound and attainment it exposes; for
  a logarithm, this can establish positivity and the range in one calculation.
- Connect a range plot to output values: a height is attained when the
  horizontal line at that height intersects the graph. Do not infer behavior
  outside the plotted window solely from the drawing.
"""


def solution_style_rules(subject: str = "") -> str:
    """Return the common contract, with mathematical method guidance as needed."""
    rules = (
        DISPLAY_FRACTION_RULES
        + SOLUTION_EXPLANATION_RULES
        + GRAPH_CLARITY_RULES
        + DIAGRAM_SPECIFICATION_RULES
    )
    if not subject or subject.lower() == "mathematics":
        rules += MATHEMATICS_REASONING_RULES
    return rules
