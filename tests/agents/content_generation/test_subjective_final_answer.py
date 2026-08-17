"""Regression tests for required subjective final-answer output."""

import pytest

from vbagent.models.solution import SolutionOutput


def test_generate_solution_rejects_missing_subjective_final_answer(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution_module,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=r"\begin{solution}x=2\end{solution}",
            answer_type="subjective",
        ),
    )

    with pytest.raises(
        ValueError,
        match="missing required final_answer_latex",
    ):
        solution_module.generate_solution(
            problem_text=r"\item Find x.",
            question_type="subjective",
            subject="physics",
            show_spinner=False,
        )


def test_generate_solution_accepts_subjective_final_answer(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    expected = r"$x=2\,\mathrm{m}$."
    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution_module,
        "run_agent_sync",
        lambda *args, **kwargs: SolutionOutput(
            solution_latex=r"\begin{solution}x=2\end{solution}",
            answer_type="subjective",
            final_answer_latex=expected,
        ),
    )

    result = solution_module.generate_solution(
        problem_text=r"\item Find x.",
        question_type="subjective",
        subject="physics",
        show_spinner=False,
    )

    assert result.final_answer_latex == expected
