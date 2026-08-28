# Image Processing

## Solution explanations

Generated solutions briefly explain why the chosen method applies, then show
the essential calculations and conclusion. Routine arithmetic may be omitted;
necessary assumptions, cases, domain restrictions, and endpoint arguments must
remain. `\intertext{}` introduces a method or explains a meaningful transition,
rather than narrating every equation. Faithful transcription of a supplied
solution still preserves the source's reasoning.

For domain and range problems, a bound alone is not enough: the solution must
justify which values are attained. Piecewise functions require checking branch
ranges and possible gaps; compositions require checking the inner expression's
values and the outer function's domain and mapping properties.

## Graphs

Keep useful graphs, with only the labels needed to read the function or support
the answer. Prefer sparse ticks and open/filled endpoint markers. Avoid repeated
coordinate labels, a legend for a single curve, and unnecessary grids or guide
lines. Required problem data, discontinuities, and endpoint inclusion must be
preserved. The same rules apply to inline plots, specialist graph generation,
and TikZ review/repair.

The solution agent first states the diagram's learning purpose. Its `context`
and `values` provide exact construction data; they are not a request to print
every value. `labels` contains only indispensable visible text and may be empty.
`annotations` contains necessary drawing actions. For a minimum, request either
exact axis ticks or one coordinate label, not both. The diagram agent chooses
placement without changing the supplied mathematics. The specification's field
names and types are unchanged.

The dispatcher forwards the drawing actions and subject settings (including
the plot window and grid preference) with the construction context. An empty
label list remains an explicit preference. Generators without separate context
arguments receive that information in the drawing description instead. Diagram
assembly adds centering only once.

## Fractions

New LaTeX uses `\dfrac{a}{b}` everywhere, including inline mathematics, graph
labels, tables, and answer keys. PGF arithmetic such as `2/3` stays arithmetic.

All VBAgent-owned document preambles make legacy `\frac` and `\tfrac` calls
render like `\dfrac`, without redefining `\dfrac` itself or rewriting stored
source files. This also applies to previews, exports, practice sets, notes,
revision sheets, and archive renders. Display fractions are taller, so labels
and tables need sufficient space.

Custom export templates remain under the caller's control. Load `amsmath` and
include `DISPLAY_FRACTION_PREAMBLE` from `vbagent.utils.latex` if the template
should follow the same policy.

Cached scans, solutions, alternate solutions, and diagrams from an older style
contract are regenerated when those stages are next requested. Existing saved
documents and published content are not rewritten automatically.
