"""Shared formatting rules for multiple-choice answer labels."""


MCQ_ANSWER_FORMAT_RULES = r"""
## MCQ Option-Label Formatting (MANDATORY)

- Use lowercase option labels everywhere in the solution: `(a)`, `(b)`, `(c)`, and `(d)`.
- Never use uppercase labels such as `(A)` or `(B)`, even when the input options are uppercase.
- Keep every option label plain: do not bold, italicize, underline, or wrap it in
  `\textbf{}`, `\mathbf{}`, `$...$`, or any other formatting command.
- For a single-correct MCQ, replace the answer letter in this exact conclusion
  with the actual lowercase letter:
  `Therefore, the correct option is (a).`
- For a multiple-correct MCQ, replace the answer letters in this exact
  conclusion with the actual lowercase letters:
  `Therefore, the correct options are (a) and (c).`
- If the conclusion is inside `align*`, write it as
  `\intertext{Therefore, the correct option is (a).}` (or the plural form)
  with the actual lowercase letter(s).
- Do not output placeholders such as `(X)` or uppercase answer letters in the final solution.
"""


MATCH_OPTION_FORMAT_RULES = r"""
## Match-the-Column Option Formatting (MANDATORY)

- Always place match-code options in `\begin{tasks}(2)...\end{tasks}`.
- Put each complete matching combination inside ONE inline-math expression and
  wrap the full combination in `\mathrm{...}`.
- Keep every arrow and comma inside that same `\mathrm{...}` block. Separate
  mappings with `,\ ` and do not create a separate `$...$` expression for each
  pair.
- Preserve the labels used by the source question. For the common
  `P,Q,R,S` and `I,II,III,IV` form, use this exact style:

```latex
\begin{tasks}(2)
  \task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ R\rightarrow I,\ S\rightarrow IV}$ \ans
  \task $\mathrm{P\rightarrow III,\ Q\rightarrow II,\ R\rightarrow I,\ S\rightarrow IV}$
  \task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ R\rightarrow IV,\ S\rightarrow I}$
  \task $\mathrm{P\rightarrow III,\ Q\rightarrow II,\ R\rightarrow IV,\ S\rightarrow I}$
\end{tasks}
```

- Append `\ans` outside the closing `$` only for the correct option.
- Never format one option as separate fragments such as
  `$P \rightarrow II$, $Q \rightarrow III$, ...`.
"""


MATCH_OPTION_FORMAT_RULES_UNMARKED = r"""
## Match-the-Column Option Formatting (MANDATORY)

- Always place match-code options in `\begin{tasks}(2)...\end{tasks}`.
- Put each complete matching combination inside ONE inline-math expression and
  wrap the full combination in `\mathrm{...}`.
- Keep every arrow and comma inside that same `\mathrm{...}` block. Separate
  mappings with `,\ ` and do not create a separate `$...$` expression for each
  pair.
- Preserve the labels used by the source question. For the common
  `P,Q,R,S` and `I,II,III,IV` form, use this exact style:

```latex
\begin{tasks}(2)
  \task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ R\rightarrow I,\ S\rightarrow IV}$
  \task $\mathrm{P\rightarrow III,\ Q\rightarrow II,\ R\rightarrow I,\ S\rightarrow IV}$
  \task $\mathrm{P\rightarrow II,\ Q\rightarrow III,\ R\rightarrow IV,\ S\rightarrow I}$
  \task $\mathrm{P\rightarrow III,\ Q\rightarrow II,\ R\rightarrow IV,\ S\rightarrow I}$
\end{tasks}
```

- Do not append `\ans` during problem-only extraction; the solution agent marks
  the correct option later.
- Never format one option as separate fragments such as
  `$P \rightarrow II$, $Q \rightarrow III$, ...`.
"""


__all__ = [
    "MCQ_ANSWER_FORMAT_RULES",
    "MATCH_OPTION_FORMAT_RULES",
    "MATCH_OPTION_FORMAT_RULES_UNMARKED",
]
