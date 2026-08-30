"""Regression tests for required subjective final-answer output."""

import pytest

from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution import get_solution_prompt


@pytest.mark.parametrize(
    "subject",
    ["physics", "chemistry", "mathematics", "biology"],
)
def test_subjective_prompt_requires_direct_single_value_answers(subject):
    prompt = get_solution_prompt("subjective", subject)

    assert "For a direct single-value question" in prompt
    assert "`$2\\pi$`" in prompt
    assert "Do not restate the question with prose" in prompt


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
