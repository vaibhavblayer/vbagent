"""Regression tests for repairing incorrect scanned match-code options."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vbagent.agents.orchestration.solution_orchestrator import SolutionOrchestrator


def _orchestrator(solution_output):
    orchestrator = object.__new__(SolutionOrchestrator)
    orchestrator.console = MagicMock()
    orchestrator._call_subject_agent = MagicMock(return_value=solution_output)
    return orchestrator


PROBLEM = r"""\item Match the columns.
\begin{tasks}(2)
  \task $\mathrm{P\rightarrow I,\ Q\rightarrow II,\ R\rightarrow III,\ S\rightarrow IV}$ \ans
  \task $\mathrm{P\rightarrow II,\ Q\rightarrow I,\ R\rightarrow IV,\ S\rightarrow III}$
  \task $\mathrm{P\rightarrow III,\ Q\rightarrow IV,\ R\rightarrow I,\ S\rightarrow II}$
  \task $\mathrm{P\rightarrow IV,\ Q\rightarrow III,\ R\rightarrow II,\ S\rightarrow I}$
\end{tasks}"""


def test_run_replaces_wrong_match_option_and_marks_repaired_slot():
    replacement = (
        r"$\mathrm{P\rightarrow\{I,III\},\ Q\rightarrow II,\ "
        r"R\rightarrow IV,\ S\rightarrow I}$"
    )
    orchestrator = _orchestrator(
        SimpleNamespace(
            solution_latex=(
                r"\begin{solution}\begin{align*}"
                r"\intertext{Therefore, the correct option is (A).}"
                r"\end{align*}\end{solution}"
            ),
            diagram_requirements=[],
            answer_type="mcq",
            answer_value="d",
            match_option_replacement_latex=replacement,
        )
    )

    result = orchestrator.run(
        problem_latex=PROBLEM,
        subject="physics",
        question_type="match",
    )

    assert rf"\task {replacement} \ans" in result.latex
    assert r"P\rightarrow IV,\ Q\rightarrow III" not in result.latex
    assert result.latex.count(r"\ans") == 1
    assert "correct option is (d)" in result.latex
    assert result.metadata["match_option_repaired"] is True


def test_run_keeps_existing_options_when_no_repair_is_requested():
    orchestrator = _orchestrator(
        SimpleNamespace(
            solution_latex=(
                r"\begin{solution}\begin{align*}"
                r"\intertext{Therefore, the correct option is (b).}"
                r"\end{align*}\end{solution}"
            ),
            diagram_requirements=[],
            answer_type="mcq",
            answer_value="b",
            match_option_replacement_latex=None,
        )
    )

    result = orchestrator.run(
        problem_latex=PROBLEM.replace(r" \ans", ""),
        subject="physics",
        question_type="match",
    )

    assert r"P\rightarrow IV,\ Q\rightarrow III" in result.latex
    assert result.metadata["match_option_repaired"] is False


def test_match_option_repair_rejects_nested_tasks_payload():
    with pytest.raises(ValueError, match="one option payload"):
        SolutionOrchestrator._replace_match_option(
            PROBLEM,
            "d",
            r"\begin{tasks}(2)\task invalid\end{tasks}",
        )
