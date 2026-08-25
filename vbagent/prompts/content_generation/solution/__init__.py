"""Solution generation prompts organized by subject and question type.

This module provides prompts for Stage 2 of the content generation pipeline:
generating solutions from scanned problems.

Unlike scanner prompts (which focus on OCR), solution prompts focus on:
- Mathematical/scientific reasoning
- Step-by-step explanations
- Diagram requirement identification
- Answer derivation
"""

from typing import Optional

from .final_answer import SUBJECTIVE_FINAL_ANSWER_RULES
from ..table_format import TABLE_FORMAT_RULES


SUBJECTIVE_MULTIPART_SOLUTION_RULES = r"""
## Multipart Subjective Solution Structure (MANDATORY)

Before writing `solution_latex`, inspect the problem's list structure.

- If the subjective problem contains a nested `enumerate` with multiple
  question parts, the solution MUST contain a corresponding `enumerate` with
  exactly one `\item` for each problem part, in the same order.
- Always use plain `\begin{enumerate}`. Do not copy or add `[label=...]`,
  `\alph`, `\roman`, `\arabic`, or counter redefinitions. The surrounding
  document and list nesting automatically determine the rendered labels.
- Put the complete reasoning for each part inside its own `\item`. An `align*`
  block inside an item is valid and is the required exception to any rule that
  says `align*` must be directly inside `solution`.
- NEVER flatten several parts into one `align*`, type labels or numbers
  manually in `\intertext`, or separate part solutions only with line breaks.
- Do not use `tasks` or `\task`; those are for selectable answer choices.

```latex
\begin{solution}
\begin{enumerate}
    \item
    \begin{align*}
    \intertext{Apply the first condition}
    x &\geq 0
    \end{align*}
    \item
    \begin{align*}
    \intertext{Apply the second condition}
    x &< 2
    \end{align*}
\end{enumerate}
\end{solution}
```
"""


def get_solution_prompt(question_type: str, subject: str, chapter: Optional[str] = None, topic: Optional[str] = None) -> str:
    """Get solution generation prompt for a question type and subject.
    
    Args:
        question_type: The type of question (mcq_sc, mcq_mc, subjective, etc.)
        subject: The subject (physics, chemistry, mathematics)
        chapter: Chapter/topic area for topic-specific routing (optional)
        topic: Specific topic for topic-specific routing (optional)
        
    Returns:
        The system prompt for solution generation
        
    Raises:
        ValueError: If subject is not supported
    """
    if subject == "physics":
        from .physics import get_prompt
        prompt = get_prompt(question_type, chapter, topic)
    elif subject == "chemistry":
        from .chemistry import get_prompt
        prompt = get_prompt(question_type)
    elif subject == "mathematics":
        from .mathematics import get_prompt
        prompt = get_prompt(question_type)
    elif subject == "biology":
        from .biology import get_prompt
        prompt = get_prompt(question_type)
    else:
        raise ValueError(f"Unsupported subject: {subject}")

    prompt += "\n\n" + TABLE_FORMAT_RULES
    if question_type == "subjective":
        prompt += "\n\n" + SUBJECTIVE_MULTIPART_SOLUTION_RULES
        prompt += "\n\n" + SUBJECTIVE_FINAL_ANSWER_RULES
    return prompt


def get_user_template(subject: str) -> str:
    """Get user message template for solution generation.
    
    Args:
        subject: The subject (physics, chemistry, mathematics)
        
    Returns:
        User message template
    """
    # Common template for all subjects
    return """Generate a detailed solution for the following problem:

{problem}

{options}

Provide:
1. Step-by-step solution with clear reasoning
2. Identify any diagrams needed in the solution
3. Final answer (if applicable)
4. Decide whether a genuinely useful alternate solution method is worth generating;
   if so, provide a short method hint only
"""


__all__ = [
    "get_solution_prompt",
    "get_user_template",
    "SUBJECTIVE_MULTIPART_SOLUTION_RULES",
    "SUBJECTIVE_FINAL_ANSWER_RULES",
]
