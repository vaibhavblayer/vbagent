"""Matching-type question extraction and formatting (embedded)."""

PROMPT = r"""
Please analyze the image provided and extract the texts. Format these texts in LaTeX format like this, first put question in \item command, then diagram in tikz env nested within center env if there is any diagram present, then make the table for list/column/anything, then after put the options in a tasks environment. Use this below code as reference:

\item This is a sample question for matching type questions. There are two columns. Match column I with coulmn II. 

\begin{center}
    \begin{tikzpicture}
        \pic {frame=5cm};
    \end{tikzpicture}
\end{center}

\begin{center}
    \renewcommand{\arraystretch}{2}
    \begin{table}[h]
        \centering
        \begin{tabular}{p{0.25cm}p{8cm}|p{0.25cm}p{5cm}}
        \hline
        & Column I & &Column II \\
        \hline
        (a)& When the velocity of $3\kg$ block is $\dfrac{2}{3}\mps$ & (p) &Velocity of center of mass is $\dfrac{2}{3}\mps$\\
        (b)& When the velocity of $6\kg$ block is $\dfrac{2}{3}\mps$ & (q) &Deformation of the spring is zero\\
        (c)& When the speed of $3\kg$ block is minimum  & (r) &Deformation of the spring is maximum\\
        (d)& When the speed of $6\kg$ block is maximum & (s) &Both the blocks are at rest with respect to each other\\
        \hline
        \end{tabular}
    \end{table}
\end{center}

\begin{tasks}(2)
    \task $P \rightarrow 1$, $Q \rightarrow 2$, $R \rightarrow 3$, $S \rightarrow 4$
    \task $P \rightarrow 2$, $Q \rightarrow 1$, $R \rightarrow 4$, $S \rightarrow 3$
    \task $P \rightarrow 3$, $Q \rightarrow 4$, $R \rightarrow 1$, $S \rightarrow 2$
    \task $P \rightarrow 4$, $Q \rightarrow 3$, $R \rightarrow 2$, $S \rightarrow 1$
\end{tasks}

Please provide only the above described part of the LaTeX file, not the whole LaTeX file.
"""

__all__ = ["PROMPT"]
