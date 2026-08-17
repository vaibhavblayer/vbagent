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


__all__ = ["MCQ_ANSWER_FORMAT_RULES"]
