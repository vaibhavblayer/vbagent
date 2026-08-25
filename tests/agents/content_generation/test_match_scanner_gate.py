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


@pytest.mark.parametrize(
    "latex",
    [
        r"%% OPTIONS_DIAGRAMS",
        r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}",
        r"\OptionJ",
    ],
)
def test_subjective_structure_gate_detects_mcq_option_leakage(latex):
    assert scanner._has_forbidden_subjective_structure(latex)


def test_subjective_structure_gate_accepts_one_main_diagram():
    latex = (
        r"\item Which graphs are functions? "
        r"\begin{center}\input{diagram}\end{center}"
    )

    assert not scanner._has_forbidden_subjective_structure(latex)


def test_subjective_scanner_normalizes_enumerate_options(monkeypatch):
    generated = (
        r"\item Answer both."
        r"\begin{enumerate}[label=(\roman*), leftmargin=*]"
        r"\item First.\item Second.\end{enumerate}"
    )
    monkeypatch.setattr(scanner, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(scanner, "create_image_message", lambda path, text: text)
    monkeypatch.setattr(
        scanner,
        "run_agent_sync",
        lambda *args, **kwargs: generated,
    )

    result = scanner.scan_problem(
        "question.png",
        "subjective",
        use_context=False,
        subject="mathematics",
        show_spinner=False,
    )

    assert r"\begin{enumerate}" in result
    assert "[label=" not in result


def test_subjective_scanner_retries_without_option_structure(monkeypatch):
    valid = (
        r"\item Which graphs are functions? "
        r"\begin{center}\input{diagram}\end{center}"
    )
    responses = iter([
        r"\item Which graphs? %% OPTIONS_DIAGRAMS "
        r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}",
        valid,
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
        "subjective",
        use_context=False,
        subject="mathematics",
        show_spinner=False,
    )

    assert result == valid
    assert len(messages) == 2
    assert "classified as\nsubjective" in messages[1]
    assert "exactly one\nmain `\\input{diagram}` placeholder" in messages[1]


def test_subjective_scanner_rejects_second_option_structure(monkeypatch):
    invalid = (
        r"\item Which graphs? %% OPTIONS_DIAGRAMS "
        r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}"
    )
    monkeypatch.setattr(scanner, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(scanner, "create_image_message", lambda path, text: text)
    monkeypatch.setattr(
        scanner,
        "run_agent_sync",
        lambda *args, **kwargs: invalid,
    )

    with pytest.raises(ValueError, match="forbidden MCQ option structure"):
        scanner.scan_problem(
            "question.png",
            "subjective",
            use_context=False,
            subject="mathematics",
            show_spinner=False,
        )
