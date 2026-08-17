"""Regression tests for solution-diagram assembly."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from vbagent.agents.orchestration.solution_orchestrator import SolutionOrchestrator


def _orchestrator():
    orchestrator = object.__new__(SolutionOrchestrator)
    orchestrator.console = MagicMock()
    return orchestrator


def test_stitch_diagrams_replaces_matching_placeholder():
    orchestrator = _orchestrator()
    solution = (
        r"\begin{solution}"
        "\n% DIAGRAM PLACEHOLDER: fbd_1\n"
        r"\end{solution}"
    )

    assembled = orchestrator._stitch_diagrams(
        solution,
        {"fbd_1": r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"},
    )

    assert "% DIAGRAM PLACEHOLDER: fbd_1" not in assembled
    assert r"\draw (0,0) -- (1,1);" in assembled


def test_stitch_diagrams_falls_back_when_placeholder_is_missing():
    orchestrator = _orchestrator()
    solution = r"\begin{solution}\begin{align*}x &= 1\end{align*}\end{solution}"
    requirement = SimpleNamespace(diagram_id="fbd_1", location="inline")
    tikz = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"

    assembled = orchestrator._stitch_diagrams(
        solution,
        {"fbd_1": tikz},
        diagram_requirements=[requirement],
    )

    assert "% Auto-inserted solution diagram: fbd_1" in assembled
    assert tikz in assembled
    assert assembled.index(tikz) < assembled.rindex(r"\end{solution}")
    orchestrator.console.print.assert_called_once()


def test_run_returns_final_latex_with_fallback_inserted_diagram():
    """The persisted pipeline payload must contain the assembled diagram."""
    orchestrator = _orchestrator()
    tikz = r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"
    orchestrator._call_subject_agent = MagicMock(
        return_value=SimpleNamespace(
            solution_latex=r"\begin{solution}x=1\end{solution}",
            diagram_requirements=[
                SimpleNamespace(diagram_id="d1", location="inline")
            ],
            answer_type="subjective",
            answer_value=None,
        )
    )
    orchestrator._dispatch_diagrams = MagicMock(return_value={"d1": tikz})

    result = orchestrator.run(
        problem_latex=r"\begin{problem}Find x.\end{problem}",
        subject="physics",
        question_type="subjective",
    )

    assert tikz in result.latex
    assert "% Auto-inserted solution diagram: d1" in result.latex


def test_run_skips_diagram_agent_and_removes_solution_placeholder():
    orchestrator = _orchestrator()
    orchestrator._call_subject_agent = MagicMock(
        return_value=SimpleNamespace(
            solution_latex=(
                r"\begin{solution}\begin{center}"
                "\n% DIAGRAM PLACEHOLDER: d1\n"
                r"\end{center}\end{solution}"
            ),
            diagram_requirements=[SimpleNamespace(diagram_id="d1")],
            answer_type="subjective",
            answer_value=None,
        )
    )
    orchestrator._dispatch_diagrams = MagicMock()

    result = orchestrator.run(
        problem_latex=r"\begin{problem}Find x.\end{problem}",
        subject="biology",
        question_type="subjective",
        generate_diagrams=False,
    )

    orchestrator._dispatch_diagrams.assert_not_called()
    assert "DIAGRAM PLACEHOLDER" not in result.latex
    assert "\\begin{center}" not in result.latex


def test_run_appends_separate_subjective_final_answer():
    orchestrator = _orchestrator()
    orchestrator._call_subject_agent = MagicMock(
        return_value=SimpleNamespace(
            solution_latex=r"\begin{solution}x=2\end{solution}",
            diagram_requirements=[],
            answer_type="subjective",
            answer_value=None,
            final_answer_latex=r"$x_{\mathrm{eq}}=2\,\mathrm{m}$, stable.",
        )
    )

    result = orchestrator.run(
        problem_latex=r"\item Find the equilibrium.",
        subject="physics",
        question_type="subjective",
    )

    assert result.final_answer_latex == r"$x_{\mathrm{eq}}=2\,\mathrm{m}$, stable."
    assert result.latex.endswith(
        "\\begin{finalanswer}\n"
        r"$x_{\mathrm{eq}}=2\,\mathrm{m}$, stable."
        "\n\\end{finalanswer}"
    )
    assert result.latex.index(r"\end{solution}") < result.latex.index(
        r"\begin{finalanswer}"
    )


def test_run_replaces_existing_subjective_final_answer():
    orchestrator = _orchestrator()
    orchestrator._call_subject_agent = MagicMock(
        return_value=SimpleNamespace(
            solution_latex=r"\begin{solution}New solution.\end{solution}",
            diagram_requirements=[],
            answer_type="subjective",
            answer_value=None,
            final_answer_latex=(
                r"\begin{finalanswer}Stable: $C$; unstable: $A,E$."
                r"\end{finalanswer}"
            ),
        )
    )

    result = orchestrator.run(
        problem_latex=(
            r"\item Find equilibrium."
            "\n\\begin{finalanswer}\nOld answer.\n\\end{finalanswer}"
        ),
        subject="physics",
        question_type="subjective",
    )

    assert "Old answer" not in result.latex
    assert result.latex.count(r"\begin{finalanswer}") == 1
    assert "Stable: $C$; unstable: $A,E$." in result.latex
