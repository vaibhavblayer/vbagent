"""Agent for fixing LaTeX compilation errors.

Takes a LaTeX snippet and pdflatex error output, returns corrected LaTeX.
"""

from vbagent.agents.base import create_agent, run_agent_sync


SYSTEM_PROMPT = r"""You are a LaTeX error fixer. You receive LaTeX code that failed to compile and the pdflatex error output.

Your job:
1. Read the error messages carefully
2. Fix ONLY the errors — do not change the content or structure
3. Common fixes: missing braces, undefined commands, wrong environment names, missing $ delimiters
4. Output ONLY the corrected LaTeX code — no explanations, no markdown, no code blocks

CRITICAL: Output the EXACT same content with ONLY the compilation errors fixed. Do not add \documentclass, preamble, or any wrapping."""

USER_TEMPLATE = """Fix the compilation errors in this LaTeX code.

**Errors from pdflatex:**
```
{errors}
```

**LaTeX code to fix:**
```latex
{latex}
```

Output ONLY the corrected LaTeX code:"""


def fix_latex(error_summary: str, latex: str) -> str:
    """Send LaTeX + errors to agent and get fixed version.

    Args:
        error_summary: Parsed pdflatex error output
        latex: The LaTeX code that failed to compile

    Returns:
        Corrected LaTeX code
    """
    agent = create_agent(
        name="LaTeX-Fixer",
        instructions=SYSTEM_PROMPT,
        agent_type="latex_fixer",
    )

    prompt = USER_TEMPLATE.format(errors=error_summary, latex=latex)
    result = run_agent_sync(agent, prompt)

    # Clean markdown artifacts
    import re
    result = re.sub(r'^```(?:latex|tex)?\s*\n?', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\n?```\s*$', '', result)
    return result.strip()
