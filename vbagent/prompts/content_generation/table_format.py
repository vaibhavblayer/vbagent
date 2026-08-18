"""Shared LaTeX table layout rules for generated educational content."""


TABLE_FORMAT_RULES = r"""
## General Table Formatting (MANDATORY)

- These rules apply to every table in a problem or solution, regardless of the
  question type.
- Keep the left and right outer sides open. A `tabular` column specification
  must never start or end with `|`; do not box the whole table.
- Use vertical rules only between meaningful internal column groups. For
  example, use `{c|c|c}` rather than `{|c|c|c|}`.
- When fixed-width `p{...}` columns are needed, size them with fractions of
  `\textwidth`, not hardcoded `cm` values. Leave room for `\tabcolsep`; the
  declared widths should normally total no more than `0.9\textwidth`.
- Numbering/label columns should usually be about `0.08\textwidth` to
  `0.1\textwidth`; divide the remaining declared width between content columns
  according to their relative amount of text or diagrams.
- Center the table and place `\renewcommand{\arraystretch}{2}` immediately
  before it for clean row spacing.
- Use `\hline` for the top, below the header, and at the bottom. Avoid drawing
  a boxed grid around every cell unless the source explicitly requires a grid
  as mathematical data.
- Make textual column headers bold with `\textbf{...}`.
- Choose sensible widths for ordinary data tables. Match-the-column tables
  follow their stricter four-column layout rule.

```latex
\begin{center}
  \renewcommand{\arraystretch}{2}
  \begin{tabular}{c|c|c}
    \hline
    \textbf{Quantity} & \textbf{Initial} & \textbf{Final} \\
    \hline
    Velocity & $u$ & $v$ \\
    Time & $0$ & $t$ \\
    \hline
  \end{tabular}
\end{center}
```
"""


__all__ = ["TABLE_FORMAT_RULES"]
