"""Prompt-driven editor for applying bounded changes to scanned LaTeX."""

from __future__ import annotations

import re

from vbagent.agents.base import create_agent, run_agent_sync
from vbagent.agents.quality.base import parse_check_result
from vbagent.prompts.quality.instruction_editor import SYSTEM_PROMPT, USER_TEMPLATE
from vbagent.utils.latex import clean_latex_output


_MATH_REGION_RE = re.compile(
    r"\\begin\{(?P<env>align\*?|equation\*?|gather\*?|multline\*?)\}"
    r".*?\\end\{(?P=env)\}"
    r"|\\\[.*?\\\]"
    r"|\\\(.*?\\\)"
    r"|\$\$.*?\$\$"
    r"|(?<!\\)\$(?!\$)(?:\\.|[^$])*?(?<!\\)\$",
    flags=re.DOTALL,
)
_MATH_TOKEN_RE = re.compile(r"VBAGENTMATHBLOCK\d+TOKEN")
_editor_agent = None


def _get_editor_agent():
    """Create the instruction editor lazily."""
    global _editor_agent
    if _editor_agent is None:
        _editor_agent = create_agent(
            name="InstructionEditor",
            instructions=SYSTEM_PROMPT,
            agent_type="instruction_editor",
        )
    return _editor_agent


def _protect_math(content: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace math regions with stable tokens before prose editing."""
    protected: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        token = f"VBAGENTMATHBLOCK{len(protected)}TOKEN"
        protected.append((token, match.group(0)))
        return token

    return _MATH_REGION_RE.sub(replace, content), protected


def _restore_math(content: str, protected: list[tuple[str, str]]) -> str:
    """Restore protected math, rejecting missing, changed, or duplicated tokens."""
    expected_tokens = [token for token, _ in protected]
    returned_tokens = _MATH_TOKEN_RE.findall(content)
    if returned_tokens != expected_tokens:
        raise ValueError(
            "Instruction editor changed, reordered, or misplaced protected mathematics"
        )
    for token, math in protected:
        if content.count(token) != 1:
            raise ValueError(
                "Instruction editor duplicated protected mathematics"
            )
        content = content.replace(token, math)
    return content


def edit_with_instruction(
    full_content: str,
    instruction: str,
    allow_math_changes: bool = False,
) -> tuple[bool, str, str]:
    """Apply one explicit instruction and return the checker-session contract."""
    if not full_content.strip():
        raise ValueError("Content cannot be empty")
    if not instruction.strip():
        raise ValueError("Instruction cannot be empty")

    if allow_math_changes:
        editable_content = full_content
        protected: list[tuple[str, str]] = []
    else:
        editable_content, protected = _protect_math(full_content)

    message = USER_TEMPLATE.replace("{instruction}", instruction.strip()).replace(
        "{full_content}", editable_content
    )
    raw_result = run_agent_sync(_get_editor_agent(), message)
    result = clean_latex_output(raw_result)
    passed, summary, corrected_content = parse_check_result(result, "EDIT_CHECK")

    if not passed and protected:
        corrected_content = _restore_math(corrected_content, protected)
    return passed, summary, corrected_content


__all__ = ["edit_with_instruction"]
