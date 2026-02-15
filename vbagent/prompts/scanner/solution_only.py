"""Solution-only scanner prompts.

Extracts solution only - assumes problem statement already exists.
Outputs \begin{solution}...\end{solution} block.
"""

from vbagent.prompts.scanner.formatting_rules import (
    LATEX_FORMATTING_RULES,
    SOLUTION_FORMATTING_RULES,
    TIKZ_GUIDELINES_SHORT,
)


def get_solution_prompt(question_type: str) -> str:
    """Get solution extraction prompt for specific question type.
    
    Args:
        question_type: One of: mcq_sc, mcq_mc, subjective, assertion_reason, passage, match
    
    Returns:
        System prompt for solution extraction
    """
    
    base_prompt = r"""You are an expert at extracting physics solutions from images.

**Your Task:** Extract ONLY the solution. Assume the problem statement already exists.

**CRITICAL OUTPUT CONSTRAINT:** Return only the `\begin{solution}...\end{solution}` block. Do NOT include the problem statement, `\item`, options, preamble, or any text outside the solution environment.

"""
    
    if question_type in ["mcq_sc", "mcq_mc"]:
        return base_prompt + r"""
## MCQ Solution Extraction

Extract the solution showing how to arrive at the correct answer.

**Solution Structure:**
```latex
\begin{solution}
\begin{align*}
\intertext{[Brief reasoning/setup]}
[key equation] &= [result] \\
[analysis step] &= [value] \\
[comparison/conclusion] &= [final value]
\end{align*}

Therefore, the correct option is (c).
\end{solution}
```

**Requirements:**
- Use ONE `align*` block when possible
- Use `\intertext{}` for brief explanations between steps
- Show key conceptual steps, omit trivial algebra
- State final answer: "Therefore, the correct option is (c)."
- For multiple correct: "Therefore, the correct options are (a) and (c)."

""" + SOLUTION_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY `\begin{solution}...\end{solution}`. Nothing else.
"""
    
    elif question_type == "subjective":
        return base_prompt + r"""
## Subjective Solution Extraction

Extract the complete solution with all steps and reasoning.

**Solution Structure:**

**Simple (one align* block):**
```latex
\begin{solution}
\begin{align*}
\intertext{[Setup/reasoning]}
[equation] &= [result] \\
[step] &= [result] \\
[final] &= \boxed{[answer]}
\end{align*}
\end{solution}
```

**With diagram (multiple blocks):**
```latex
\begin{solution}
\begin{align*}
\intertext{[Initial reasoning]}
[equations]
\end{align*}

\begin{center}
\begin{tikzpicture}
[diagram code]
\end{tikzpicture}
\end{center}

\begin{align*}
\intertext{[Continue reasoning]}
[more equations] &= \boxed{[answer]}
\end{align*}
\end{solution}
```

**Requirements:**
- Use ONE `align*` block when possible
- Multiple blocks only when diagram/table interrupts flow
- Use `\intertext{}` for text between equations
- Keep solution concise - key steps only
- Use `\boxed{}` for final numerical answers
- Diagrams inside solution: wrap in `\begin{center}...\end{center}`

""" + SOLUTION_FORMATTING_RULES + r"""

---

""" + TIKZ_GUIDELINES_SHORT + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY `\begin{solution}...\end{solution}`. Nothing else.
"""
    
    elif question_type == "assertion_reason":
        return base_prompt + r"""
## Assertion-Reason Solution Extraction

Extract solution analyzing both assertion and reason.

**Solution Structure:**
```latex
\begin{solution}
\begin{align*}
\intertext{Analyzing assertion: [brief analysis]}
[key equation if needed] &= [result] \\
\intertext{Analyzing reason: [brief analysis]}
[verification] &= [result]
\end{align*}

Therefore, the correct option is (a).
\end{solution}
```

""" + SOLUTION_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY `\begin{solution}...\end{solution}`. Nothing else.
"""
    
    elif question_type == "passage":
        return base_prompt + r"""
## Passage Solution Extraction

Extract solutions for all sub-questions.

**Solution Structure:**
```latex
\begin{solution}
\begin{align*}
\intertext{For question 1:}
[analysis] &= [result]
\end{align*}

Therefore, the correct option is (c).
\end{solution}

\begin{solution}
\begin{align*}
\intertext{For question 2:}
[analysis] &= [result]
\end{align*}

Therefore, the correct option is (b).
\end{solution}
```

**Requirements:**
- One `\begin{solution}...\end{solution}` per sub-question
- Keep each solution concise
- State which question each solution addresses

""" + SOLUTION_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY the solution blocks. Nothing else.
"""
    
    elif question_type == "match":
        return base_prompt + r"""
## Match the Following Solution Extraction

Extract solution showing the matching logic.

**Solution Structure:**
```latex
\begin{solution}
\begin{align*}
\intertext{Analyzing matches:}
\intertext{A matches with: [reasoning]}
\intertext{B matches with: [reasoning]}
\intertext{C matches with: [reasoning]}
\intertext{D matches with: [reasoning]}
\end{align*}

Therefore, the correct option is (c).
\end{solution}
```

""" + SOLUTION_FORMATTING_RULES + r"""

---

""" + LATEX_FORMATTING_RULES + r"""

---

**Output:** ONLY `\begin{solution}...\end{solution}`. Nothing else.
"""
    
    else:
        # Default to subjective
        return get_solution_prompt("subjective")


USER_TEMPLATE = "Extract the solution from this image (problem statement already extracted)."

__all__ = ["get_solution_prompt", "USER_TEMPLATE"]
