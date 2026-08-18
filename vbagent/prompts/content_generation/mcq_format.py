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

- Every match-type question MUST contain exactly four match-code options inside
  `\begin{tasks}(2)...\end{tasks}`, even when the source question shows only
  the two columns and provides no code options.
- If the source provides four options, preserve them faithfully. If it provides
  fewer than four or none, first determine the correct complete matching, then
  synthesize distinct, plausible alternatives by permuting/swapping matches.
  Include the correct complete matching exactly once and append `\ans` to it.
- Never omit the `tasks` block and never return a match question as a bare table
  followed only by a prose answer.
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
- Every option must map every item from Column-I/List-I.
- For one-to-many matching, keep the full target set on the right side of the
  same arrow using escaped braces. For example:
  `\task $\mathrm{P\rightarrow\{I,III\},\ Q\rightarrow\{II,IV\},\ R\rightarrow I,\ S\rightarrow III}$`
  Do not split one-to-many matches into separate math fragments or prose.
"""


MATCH_OPTION_FORMAT_RULES_UNMARKED = r"""
## Match-the-Column Option Formatting (MANDATORY)

- Every match-type question MUST contain exactly four match-code options inside
  `\begin{tasks}(2)...\end{tasks}`, even when the source question shows only
  the two columns and provides no code options.
- If the source provides four options, preserve them faithfully. If it provides
  fewer than four or none, infer the correct complete matching from the visible
  column content, include it exactly once, and synthesize three distinct,
  plausible alternatives by permuting/swapping matches.
- Never omit the `tasks` block and never return a match question as a bare table.
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
- Every option must map every item from Column-I/List-I.
- For one-to-many matching, keep the full target set on the right side of the
  same arrow using escaped braces. For example:
  `\task $\mathrm{P\rightarrow\{I,III\},\ Q\rightarrow\{II,IV\},\ R\rightarrow I,\ S\rightarrow III}$`
  Do not split one-to-many matches into separate math fragments or prose.
"""


MATCH_TABLE_DIAGRAM_RULES = r"""
## Diagrams Inside Match-the-Column Tables (MANDATORY)

- Every matching table, whether its cells contain text or diagrams, MUST use
  four columns in this open-sided form, for example:
  `\begin{tabular}{@{}p{0.1\textwidth}p{0.3\textwidth}|p{0.1\textwidth}p{0.4\textwidth}@{}}`.
- Express `p{...}` widths as fractions of `\textwidth`, never fixed `cm`
  measurements. Keep each narrow label/numbering column close to
  `0.1\textwidth`, then adjust the two content-column fractions according to
  their material.
- Keep the sum of the four declared widths at or below `0.9\textwidth` so
  LaTeX's internal column padding does not push the table beyond the page.
- Keep both outer sides open: never put a vertical rule before the first column
  or after the last column. Use exactly one vertical separator between the two
  column groups, as shown by the single `|` above.
- Use `\renewcommand{\arraystretch}{2}`, top/header/bottom `\hline` rules, and
  bold headers written as `\textbf{Column-I}` and `\textbf{Column-II}` (or the
  source's corresponding List-I/List-II names).
- A diagram that belongs to a Column-I or Column-II row MUST remain inside
  that row's table cell. Never move the row diagrams into one large centered
  montage above the table.
- Do NOT use `\input{diagram}` for diagrams that belong to matching-table
  cells. That placeholder is only for a separate standalone diagram outside
  the table.
- Use `\MatchA`, `\MatchB`, ... placeholders in the corresponding table cells.
  The suffix follows the source row label when it is a single Latin letter.
- Do NOT generate `\def\MatchA{...}` while scanning. The diagram agent defines
  each macro separately, and the pipeline inserts the definitions before the
  table.
- Keep `\OptionA`, `\OptionB`, ... reserved for MCQ answer choices in the
  `tasks` environment. Never use `\OptionA` for a matching-table row diagram.
- If the source contains BOTH a separate standalone diagram and diagrams in
  table cells, emit one `\input{diagram}` placeholder for the standalone
  diagram and `\MatchX` placeholders inside the appropriate cells.

Use this structure:

```latex
\item Match Column-I with Column-II.

%% MATCH_DIAGRAMS: Column-I rows (A)--(D) contain diagrams
\begin{center}
  \renewcommand{\arraystretch}{2}
  \begin{tabular}{@{}p{0.1\textwidth}p{0.3\textwidth}|p{0.1\textwidth}p{0.4\textwidth}@{}}
    \hline
    & \textbf{Column-I} & & \textbf{Column-II} \\
    \hline
    (A) & \MatchA & (P) & First statement \\
    (B) & \MatchB & (Q) & Second statement \\
    (C) & \MatchC & (R) & Third statement \\
    (D) & \MatchD & (S) & Fourth statement \\
    \hline
  \end{tabular}
\end{center}
```

The assembled LaTeX will contain definitions such as
`\def\MatchA{\begin{tikzpicture}[baseline=(current bounding box.center)]...\end{tikzpicture}}`
before the table, while the table consumes them as `(A) & \MatchA & ...`.
"""


__all__ = [
    "MCQ_ANSWER_FORMAT_RULES",
    "MATCH_OPTION_FORMAT_RULES",
    "MATCH_OPTION_FORMAT_RULES_UNMARKED",
    "MATCH_TABLE_DIAGRAM_RULES",
]
