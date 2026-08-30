"""Shared structured-output guidance for subjective final answers."""

SUBJECTIVE_FINAL_ANSWER_RULES = r"""
## Subjective Final Answer Field (REQUIRED)

For every subjective problem, return a separate `final_answer_latex` field in
the JSON object.

- It must contain only concise, answer-key-ready LaTeX, suitable for placing
  directly after `\item`.
- Use valid inline LaTeX for variables, formulas, units, and scientific
  notation.
- For a direct single-value question, return only the requested value (and
  units when needed), such as `$2\pi$`, `$\left[1,\infty\right)$`, or
  `$5\,\mathrm{m\,s^{-1}}$`. Do not restate the question with prose such as
  `The fundamental period is ...`, `The range is ...`, or `The answer is ...`.
  Do not add a full stop when the field contains only displayed inline math.
- Include a short identifier such as `$x=2$` only when the bare value would be
  ambiguous. When one question requests several named quantities, label each
  result concisely so the answer mapping remains clear.
- For any other single-part problem, return one concise answer as plain LaTeX.
- For a multipart problem whose question parts use `enumerate`, this field MUST
  be a complete matching `enumerate` block with exactly one concise `\item` per
  answer, in the same order. Always use plain `\begin{enumerate}` with no
  optional label argument or counter command; nesting automatically determines
  the rendered labels. Never type `(a)`, `(b)`, `1.`, `2.`, and so on manually,
  and never flatten multipart answers into a semicolon-separated sentence.
- Preserve meaningful capitalization, such as point labels $A$, $B$, and $C$,
  vector names, and commands such as `\Delta`.
- Do not include derivation, reasoning, `\boxed{}`, a `solution` environment,
  or a `finalanswer` environment.
- Do not write the alternate solution itself in this field.
- Do not put the answer in `answer_value`; keep `answer_type` as `"subjective"`
  and `answer_value` as `null`.

Examples:
- `"$2\pi$"`
- `"$\left[1,\infty\right)$"`
- `"Stable: $C$; unstable: $A$ and $E$."`
- `"$x_{\mathrm{eq}}=\dfrac{b}{2a}$, stable."`
- `"\\begin{enumerate}\\item Unstable along
  the $x$-axis.\\item Stable along the $y$-axis.\\end{enumerate}"`

The JSON object must therefore include:
- `answer_type`: `"subjective"`
- `answer_value`: `null`
- `final_answer_latex`: A non-empty concise LaTeX answer string
"""


__all__ = ["SUBJECTIVE_FINAL_ANSWER_RULES"]
