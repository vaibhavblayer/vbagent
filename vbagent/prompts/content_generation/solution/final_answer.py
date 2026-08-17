"""Shared structured-output guidance for subjective final answers."""

SUBJECTIVE_FINAL_ANSWER_RULES = r"""
## Subjective Final Answer Field (REQUIRED)

For every subjective problem, return a separate `final_answer_latex` field in
the JSON object.

- It must contain only concise, answer-key-ready LaTeX, suitable for placing
  directly after `\item`.
- Use valid inline LaTeX for variables, formulas, units, and scientific
  notation.
- Include every requested part, separated clearly with semicolons when useful.
- Preserve meaningful capitalization, such as point labels $A$, $B$, and $C$,
  vector names, and commands such as `\Delta`.
- Do not include derivation, reasoning, `\boxed{}`, a `solution` environment,
  or a `finalanswer` environment.
- Do not write the alternate solution itself in this field.
- Do not put the answer in `answer_value`; keep `answer_type` as `"subjective"`
  and `answer_value` as `null`.

Examples:
- `"Stable: $C$; unstable: $A$ and $E$."`
- `"(a) Unstable along the $x$-axis; (b) stable along the $y$-axis."`
- `"$x_{\mathrm{eq}}=\frac{b}{2a}$, stable."`

The JSON object must therefore include:
- `answer_type`: `"subjective"`
- `answer_value`: `null`
- `final_answer_latex`: A non-empty concise LaTeX answer string
"""


__all__ = ["SUBJECTIVE_FINAL_ANSWER_RULES"]
