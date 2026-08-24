"""Regression tests for multipart subjective solution structure."""

import pytest

from vbagent.agents.content_generation.solution.structure import (
    has_matching_multipart_structure,
    has_multipart_subjective_problem,
    multipart_enumerate_counts,
    multipart_enumerate_shapes,
)
from vbagent.models.solution import SolutionOutput
from vbagent.prompts.content_generation.solution import get_solution_prompt


MULTIPART_PROBLEM = r"""
\item Find the domain of each function.
\begin{enumerate}
    \item $f(x)=\sqrt{x}$
    \item $g(x)=\log x$
    \item $h(x)=\frac{1}{x}$
\end{enumerate}
"""


def _valid_output() -> SolutionOutput:
    return SolutionOutput(
        solution_latex=r"""
\begin{solution}
\begin{enumerate}
    \item \begin{align*}D_f&=[0,\infty)\end{align*}
    \item \begin{align*}D_g&=(0,\infty)\end{align*}
    \item \begin{align*}D_h&=\mathbb{R}\setminus\{0\}\end{align*}
\end{enumerate}
\end{solution}
""",
        answer_type="subjective",
        final_answer_latex=r"""
\begin{enumerate}
    \item $D_f=[0,\infty)$.
    \item $D_g=(0,\infty)$.
    \item $D_h=\mathbb{R}\setminus\{0\}$.
\end{enumerate}
""",
    )


@pytest.mark.parametrize(
    "subject",
    ["physics", "chemistry", "mathematics", "biology"],
)
def test_subjective_prompts_require_matching_solution_enumerate(subject):
    prompt = get_solution_prompt("subjective", subject)

    assert "Multipart Subjective Solution Structure (MANDATORY)" in prompt
    assert "exactly one `\\item` for each problem part" in prompt
    assert "NEVER flatten several parts into one `align*`" in prompt
    assert r"\begin{enumerate}[label=(\alph*), leftmargin=*]" in prompt
    assert "`final_answer_latex`" in prompt
    assert "complete matching `enumerate` block" in prompt
    assert "Never type `(a)`, `(b)`" in prompt


def test_structure_parser_counts_only_direct_items():
    latex = r"""
\begin{enumerate}
  \item First
  \item Second
  \begin{enumerate}
    \item Inner one
    \item Inner two
    \item Inner three
  \end{enumerate}
\end{enumerate}
"""

    assert multipart_enumerate_counts(latex) == (3, 2)


def test_matching_structure_preserves_local_label_option():
    problem = r"""
\item Answer both parts.
\begin{enumerate}[label=(\alph*), leftmargin=*]
    \item First
    \item Second
\end{enumerate}
"""
    matching = r"""
\begin{solution}
\begin{enumerate}[label=(\alph*), leftmargin=*]
    \item First solution
    \item Second solution
\end{enumerate}
\end{solution}
"""
    wrong_labels = matching.replace(r"label=(\alph*)", r"label=(\roman*)")

    assert multipart_enumerate_shapes(problem) == (
        (r"label=(\alph*),leftmargin=*", 2),
    )
    assert has_matching_multipart_structure(problem, matching) is True
    assert has_matching_multipart_structure(problem, wrong_labels) is False


def test_matching_structure_rejects_flattened_solution():
    flattened = r"""
\begin{solution}
\begin{align*}
\intertext{1. First domain}
D_1&=[0,\infty)
\intertext{2. Second domain}
D_2&=(0,\infty)
\intertext{3. Third domain}
D_3&=\mathbb{R}\setminus\{0\}
\end{align*}
\end{solution}
"""

    assert has_multipart_subjective_problem(MULTIPART_PROBLEM) is True
    assert has_matching_multipart_structure(MULTIPART_PROBLEM, flattened) is False
    assert (
        has_matching_multipart_structure(
            MULTIPART_PROBLEM,
            _valid_output().solution_latex,
        )
        is True
    )


def test_generate_solution_retries_flattened_multipart_output(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    flattened = SolutionOutput(
        solution_latex=(
            r"\begin{solution}\begin{align*}"
            r"\intertext{1. First}\intertext{2. Second}"
            r"\intertext{3. Third}\end{align*}\end{solution}"
        ),
        answer_type="subjective",
        final_answer_latex="First; second; third.",
    )
    outputs = iter([flattened, _valid_output()])
    calls = []
    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())

    def fake_run(*args, **kwargs):
        calls.append(args[1])
        return next(outputs)

    monkeypatch.setattr(solution_module, "run_agent_sync", fake_run)

    result = solution_module.generate_solution(
        problem_text=MULTIPART_PROBLEM,
        question_type="subjective",
        subject="mathematics",
        show_spinner=False,
    )

    assert result is not flattened
    assert len(calls) == 2
    assert "Required direct item count(s): 3" in calls[1][0]["content"]
    assert has_matching_multipart_structure(
        MULTIPART_PROBLEM,
        result.solution_latex,
    )
    assert has_matching_multipart_structure(
        MULTIPART_PROBLEM,
        result.final_answer_latex or "",
    )


def test_generate_solution_retries_only_flattened_final_answer(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    valid = _valid_output()
    flattened_answer = valid.model_copy(
        update={"final_answer_latex": "1. First; 2. Second; 3. Third."}
    )
    outputs = iter([flattened_answer, valid])
    calls = []
    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())

    def fake_run(*args, **kwargs):
        calls.append(args[1])
        return next(outputs)

    monkeypatch.setattr(solution_module, "run_agent_sync", fake_run)

    result = solution_module.generate_solution(
        problem_text=MULTIPART_PROBLEM,
        question_type="subjective",
        subject="mathematics",
        show_spinner=False,
    )

    assert result is valid
    assert len(calls) == 2
    assert "In `final_answer_latex`" in calls[1][0]["content"]


def test_generate_solution_fails_closed_after_invalid_retry(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    flattened = SolutionOutput(
        solution_latex=r"\begin{solution}1. First; 2. Second; 3. Third.\end{solution}",
        answer_type="subjective",
        final_answer_latex="First; second; third.",
    )
    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())
    monkeypatch.setattr(
        solution_module,
        "run_agent_sync",
        lambda *args, **kwargs: flattened,
    )

    with pytest.raises(
        ValueError,
        match="do not mirror the problem's enumerate/item structure",
    ):
        solution_module.generate_solution(
            problem_text=MULTIPART_PROBLEM,
            question_type="subjective",
            subject="mathematics",
            show_spinner=False,
        )


def test_single_part_subjective_solution_does_not_require_enumerate(monkeypatch):
    import vbagent.agents.content_generation.solution as solution_module

    output = SolutionOutput(
        solution_latex=r"\begin{solution}x=2\end{solution}",
        answer_type="subjective",
        final_answer_latex=r"$x=2$.",
    )
    calls = []
    monkeypatch.setattr(solution_module, "create_agent", lambda **kwargs: object())

    def fake_run(*args, **kwargs):
        calls.append(args[1])
        return output

    monkeypatch.setattr(solution_module, "run_agent_sync", fake_run)

    result = solution_module.generate_solution(
        problem_text=r"\item Solve $x+1=3$.",
        question_type="subjective",
        subject="mathematics",
        show_spinner=False,
    )

    assert result is output
    assert len(calls) == 1
