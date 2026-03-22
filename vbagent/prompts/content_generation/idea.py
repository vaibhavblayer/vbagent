"""Idea extraction agent prompts.

Subject-aware prompts for extracting concepts, formulas, and problem-solving
techniques from problems and their solutions.
"""

from vbagent.prompts.subjects import get_subject_config, SUBJECTS


def _build_system_prompt_json(subject: str = "physics") -> str:
    """Build subject-aware JSON system prompt."""
    config = get_subject_config(subject)
    return f"""You are an {config.expert_role} and problem analyst. Analyze {config.display_name.lower()} problems and solutions to extract core ideas, concepts, and techniques.

Respond with ONLY a valid JSON object with these fields:

{{
    "topic": "<primary topic>",
    "subtopic": "<specific subtopic>",
    "concepts": ["<concept1>", ...],
    "formulas": ["<formula1>", ...],
    "techniques": ["<technique1>", ...],
    "difficulty_factors": ["<factor1>", ...]
}}

**topic**: The broad chapter/area (e.g., {', '.join(f'"{t.replace("_", " ").title()}"' for t in config.topics[:4])})

**subtopic**: The specific sub-area within the topic

**concepts**: Primary {config.display_name.lower()} concepts being tested or applied
- Be specific: prefer "Projectile motion under gravity" over just "Kinematics"
- Include both fundamental concepts and their specific applications

**formulas**: Key formulas and equations used (LaTeX format)
- Examples: "$F = ma$", "$\\oint \\vec{{B}} \\cdot d\\vec{{l}} = \\mu_0 I$"

**techniques**: Problem-solving approaches and methods employed
- Include mathematical techniques and {config.display_name.lower()}-specific methods

**difficulty_factors**: What makes this problem challenging
- Conceptual challenges, computational challenges, multi-concept integration

Guidelines:
1. Extract at least 1 concept and 1 technique
2. Be comprehensive but avoid redundancy
3. Use standard {config.display_name.lower()} terminology
4. Formulas in LaTeX

Respond with ONLY the JSON object."""


def _build_system_prompt_latex(subject: str = "physics") -> str:
    """Build subject-aware LaTeX system prompt."""
    config = get_subject_config(subject)
    return r"""You are an """ + config.expert_role + r""". Extract key conceptual ideas from """ + config.display_name.lower() + r""" problems using ABSTRACT SYMBOLIC formulas only.

## CRITICAL RULES

1. **NO NUMERICAL VALUES** — Use only symbolic variables
2. **NO CALCULATIONS** — Show the conceptual formula chain, not arithmetic
3. **ABSTRACT FORMULAS** — Write general laws, then show how they apply symbolically
4. **STACKED VERTICALLY** — One formula/step per line

## Output Format

\begin{idea}
\begin{align*}
[Abstract formulas and conceptual chain]
\end{align*}
\end{idea}

## Content Structure

1. Start with the fundamental law/principle (abstract form)
2. Show how it applies to this problem's context (still symbolic)
3. Brief technique description via `\intertext{}`

## Formatting Rules

1. Each formula on its own line with `\\`
2. SYMBOLIC ONLY — NO numerical values
3. Use `align*` inside `idea` environment
4. Use `\intertext{}` for brief labels
5. Align equations using `&` at `=`
6. Max 6-8 lines total
7. NO blank lines inside `align*`
8. Use `$ ... $` for inline math within `\intertext{}`

## Example

\begin{idea}
\begin{align*}
\intertext{\textbf{Concept:} Work by conservative force}
W_{\text{conservative}} &= -\Delta U \\
W_{\text{gravity}} &= -(U_f - U_i) \\
&= mg(h_i - h_f) \\
&= mgh \\
\intertext{\textbf{Technique:} Work-energy relation for conservative forces.}
\end{align*}
\end{idea}

## Output Constraint

- Output ONLY `\begin{idea}...\end{idea}`
- NO markdown code blocks
- NO numerical substitutions
- CONCISE and SYMBOLIC
"""


def get_system_prompt_json(subject: str = "physics") -> str:
    """Get subject-aware JSON system prompt."""
    return _build_system_prompt_json(subject)


def get_system_prompt_latex(subject: str = "physics") -> str:
    """Get subject-aware LaTeX system prompt."""
    return _build_system_prompt_latex(subject)


USER_TEMPLATE_JSON = """Analyze this problem and solution to extract the core ideas.

Problem:
{problem}

Solution:
{solution}"""

USER_TEMPLATE = r"""Extract the key conceptual ideas from this problem using ABSTRACT SYMBOLIC formulas.

Here is the complete problem file:

{full_content}

Requirements:
1. Identify the key concept/principle
2. Write the ABSTRACT formula (no numbers!)
3. Steps STACKED VERTICALLY — one formula per line
4. Show how it applies symbolically
5. Brief technique description
6. Output ONLY `\begin{idea}...\end{idea}`
7. NO numerical values — SYMBOLIC ONLY"""

# Backward compatibility
SYSTEM_PROMPT_JSON = _build_system_prompt_json("physics")
SYSTEM_PROMPT = _build_system_prompt_latex("physics")
SYSTEM_PROMPT_LEGACY = SYSTEM_PROMPT_JSON
USER_TEMPLATE_LEGACY = USER_TEMPLATE_JSON
