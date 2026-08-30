"""Tests for the prompt-driven scanned-LaTeX instruction editor."""

import pytest

from vbagent.agents.quality import instruction_editor


def test_instruction_editor_protects_math_and_restores_it_exactly(monkeypatch):
    source = (
        r"\item $f(x)=\dfrac{1}{2}\left|\sin x\right|$"
        "\n"
        r"\begin{align*}a&=b+c\end{align*}"
    )
    observed = {}

    monkeypatch.setattr(instruction_editor, "_get_editor_agent", lambda: object())

    def fake_run(agent, message):
        observed["message"] = message
        return (
            "% EDIT_CHECK: Added the requested question wording\n"
            "\\item Find the period of the function "
            "VBAGENTMATHBLOCK0TOKEN\n"
            "VBAGENTMATHBLOCK1TOKEN"
        )

    monkeypatch.setattr(instruction_editor, "run_agent_sync", fake_run)

    passed, summary, corrected = instruction_editor.edit_with_instruction(
        source,
        'Prefix the item with "Find the period of the function".',
    )

    assert passed is False
    assert summary == "Added the requested question wording"
    assert corrected == (
        r"\item Find the period of the function "
        r"$f(x)=\dfrac{1}{2}\left|\sin x\right|$"
        "\n"
        r"\begin{align*}a&=b+c\end{align*}"
    )
    assert "$f(x)" not in observed["message"]
    assert "VBAGENTMATHBLOCK0TOKEN" in observed["message"]
    assert "VBAGENTMATHBLOCK1TOKEN" in observed["message"]


def test_instruction_editor_fails_closed_when_math_token_is_lost(monkeypatch):
    monkeypatch.setattr(instruction_editor, "_get_editor_agent", lambda: object())
    monkeypatch.setattr(
        instruction_editor,
        "run_agent_sync",
        lambda *args: "% EDIT_CHECK: Changed wording\n\\item Find the period.",
    )

    with pytest.raises(ValueError, match="protected mathematics"):
        instruction_editor.edit_with_instruction(
            r"\item $f(x)=\sin x$",
            "Add a question instruction.",
        )


def test_instruction_editor_fails_closed_when_math_is_reordered(monkeypatch):
    monkeypatch.setattr(instruction_editor, "_get_editor_agent", lambda: object())
    monkeypatch.setattr(
        instruction_editor,
        "run_agent_sync",
        lambda *args: (
            "% EDIT_CHECK: Changed wording\n"
            "\\item Compare VBAGENTMATHBLOCK1TOKEN and "
            "VBAGENTMATHBLOCK0TOKEN."
        ),
    )

    with pytest.raises(ValueError, match="reordered"):
        instruction_editor.edit_with_instruction(
            r"\item Compare $x$ and $y$.",
            "Improve the wording.",
        )


def test_instruction_editor_can_explicitly_allow_math_changes(monkeypatch):
    monkeypatch.setattr(instruction_editor, "_get_editor_agent", lambda: object())
    monkeypatch.setattr(
        instruction_editor,
        "run_agent_sync",
        lambda *args: "% EDIT_CHECK: Corrected expression\n\\item $f(x)=\\cos x$",
    )

    passed, _, corrected = instruction_editor.edit_with_instruction(
        r"\item $f(x)=\sin x$",
        "Change sine to cosine.",
        allow_math_changes=True,
    )

    assert passed is False
    assert corrected == r"\item $f(x)=\cos x$"


def test_instruction_editor_requires_content_and_instruction():
    with pytest.raises(ValueError, match="Content cannot be empty"):
        instruction_editor.edit_with_instruction("", "Add wording")
    with pytest.raises(ValueError, match="Instruction cannot be empty"):
        instruction_editor.edit_with_instruction(r"\item $x$", "  ")
