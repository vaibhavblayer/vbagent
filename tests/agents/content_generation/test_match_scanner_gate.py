"""Fail-closed scanner gate for mandatory match code options."""

import pytest

from vbagent.agents.content_generation import scanner


VALID_MATCH = r"""\item Match the following.
\begin{tabular}{cc}P & I\end{tabular}
\begin{tasks}(2)
\task $\mathrm{P\rightarrow I}$
\task $\mathrm{P\rightarrow II}$
\task $\mathrm{P\rightarrow III}$
\task $\mathrm{P\rightarrow IV}$
\end{tasks}"""


def test_match_option_gate_requires_exactly_four_tasks():
    assert scanner._has_required_match_options(VALID_MATCH)
    assert not scanner._has_required_match_options(
        r"\begin{tasks}(2)\task A\task B\end{tasks}"
    )
    assert not scanner._has_required_match_options(
        r"\begin{tabular}{cc}P & I\end{tabular}"
    )


def test_match_scanner_retries_when_source_has_no_code_options(monkeypatch):
    responses = iter([
        r"\item Match.\begin{tabular}{cc}P & I\end{tabular}",
        VALID_MATCH,
    ])
    messages = []
    monkeypatch.setattr(scanner, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        scanner,
        "create_image_message",
        lambda path, text: messages.append(text) or text,
    )
    monkeypatch.setattr(
        scanner,
        "run_agent_sync",
        lambda *args, **kwargs: next(responses),
    )

    result = scanner.scan_problem(
        "question.png",
        "match",
        use_context=False,
        subject="physics",
        show_spinner=False,
    )

    assert result == VALID_MATCH
    assert len(messages) == 2
    assert "source image contains only the" in messages[1]


def test_match_scanner_rejects_second_response_without_options(monkeypatch):
    monkeypatch.setattr(scanner, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(scanner, "create_image_message", lambda path, text: text)
    monkeypatch.setattr(
        scanner,
        "run_agent_sync",
        lambda *args, **kwargs: r"\item Match.\begin{tabular}{cc}P & I\end{tabular}",
    )

    with pytest.raises(ValueError, match="mandatory four-option tasks block"):
        scanner.scan_problem(
            "question.png",
            "match",
            use_context=False,
            subject="physics",
            show_spinner=False,
        )
