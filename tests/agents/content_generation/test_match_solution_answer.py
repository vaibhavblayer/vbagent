"""Structured answer recovery for generated match solutions."""

import pytest

from vbagent.agents.content_generation import solution
from vbagent.models.solution import SolutionOutput


def test_match_solution_recovers_option_letter_from_conclusion(monkeypatch):
    monkeypatch.setattr(solution, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=(
                r"\begin{solution}"
                r"\begin{align*}"
                r"\intertext{Therefore, the correct option is (c).}"
                r"\end{align*}"
                r"\end{solution}"
            ),
        ),
    )

    result = solution.generate_solution(
        r"\item Match.\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}",
        "match",
        "physics",
        show_spinner=False,
    )

    assert result.answer_type == "mcq"
    assert result.answer_value == "c"


def test_match_solution_fails_without_structured_or_written_option(monkeypatch):
    monkeypatch.setattr(solution, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=r"\begin{solution}P\rightarrow I\end{solution}",
        ),
    )

    with pytest.raises(ValueError, match="missing the correct code option"):
        solution.generate_solution(
            r"\item Match.\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}",
            "match",
            "physics",
            show_spinner=False,
        )


def test_match_solution_preserves_valid_replacement_payload(monkeypatch):
    replacement = (
        r"$\mathrm{P\rightarrow II,\ Q\rightarrow III,\ "
        r"R\rightarrow I,\ S\rightarrow IV}$"
    )
    monkeypatch.setattr(solution, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=(
                r"\begin{solution}"
                r"\intertext{Therefore, the correct option is (d).}"
                r"\end{solution}"
            ),
            answer_type="mcq",
            answer_value="d",
            match_option_replacement_latex=replacement,
        ),
    )

    result = solution.generate_solution(
        r"\item Match.\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}",
        "match",
        "physics",
        show_spinner=False,
    )

    assert result.match_option_replacement_latex == replacement


def test_match_solution_rejects_replacement_with_task_wrapper(monkeypatch):
    monkeypatch.setattr(solution, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=(
                r"\begin{solution}"
                r"\intertext{Therefore, the correct option is (d).}"
                r"\end{solution}"
            ),
            answer_type="mcq",
            answer_value="d",
            match_option_replacement_latex=r"\task $P\rightarrow I$",
        ),
    )

    with pytest.raises(ValueError, match="only the option payload"):
        solution.generate_solution(
            r"\item Match.\begin{tasks}(2)\task A\task B\task C\task D\end{tasks}",
            "match",
            "physics",
            show_spinner=False,
        )
