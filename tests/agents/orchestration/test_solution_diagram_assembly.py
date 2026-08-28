"""Regression tests for solution-diagram assembly."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vbagent.agents.orchestration.solution_orchestrator import SolutionOrchestrator
from vbagent.models.solution import DiagramRequirement


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


@pytest.mark.parametrize("marker_type", ["DIAGRAM PLACEHOLDER", "PLACEHOLDER"])
@pytest.mark.parametrize("wrapper", ["", "center", "tikzpicture", "both"])
@pytest.mark.parametrize("centered_code", [False, True])
def test_stitch_diagrams_centers_once_and_preserves_tex(marker_type, wrapper, centered_code):
    marker = f"\n% {marker_type}: graph_1\n"
    if wrapper in ("tikzpicture", "both"):
        marker = r"\begin{tikzpicture}" + marker + r"\end{tikzpicture}"
    if wrapper in ("center", "both"):
        marker = r"\begin{center}" + marker + r"\end{center}"
    code = r"\begin{tikzpicture}\node {$\dfrac{1}{2}$};\end{tikzpicture}"
    if centered_code:
        code = r"\begin{center}" + code + r"\end{center}"

    assembled = _orchestrator()._stitch_diagrams(
        r"\begin{solution}" + marker + r"\end{solution}", {"graph_1": code}
    )

    assert "PLACEHOLDER" not in assembled
    assert assembled.count(r"\begin{center}") == 1
    assert assembled.count(r"\end{center}") == 1
    assert assembled.count(r"\begin{tikzpicture}") == 1
    assert r"\node {$\dfrac{1}{2}$};" in assembled


def test_stitch_diagrams_does_not_replace_a_longer_diagram_id():
    solution = (
        "\\begin{solution}\n% DIAGRAM PLACEHOLDER: graph_10\n"
        "% DIAGRAM PLACEHOLDER: graph_1\n\\end{solution}"
    )
    assembled = _orchestrator()._stitch_diagrams(solution, {"graph_1": "GRAPH ONE"})

    assert "% DIAGRAM PLACEHOLDER: graph_10" in assembled
    assert assembled.count("GRAPH ONE") == 1


@pytest.mark.parametrize("subject", ["mathematics", "physics", "chemistry"])
def test_dispatch_preserves_drawing_actions_subject_settings_and_empty_labels(monkeypatch, subject):
    from vbagent.agents.diagram import tikz_router

    received = {}

    def generate(**kwargs):
        received.update(kwargs)
        return "DIAGRAM CODE", "function_graph"

    monkeypatch.setattr(tikz_router, "generate_tikz_with_routing", generate)
    req = DiagramRequirement(
        diagram_id="graph_1",
        diagram_type="function_graph",
        description="Show the attained minimum.",
        context="Exact function and domain.",
        values={"minimum": "(2/3, ln(11/3))"},
        labels=[],
        annotations=["Use exact axis ticks, not a coordinate node."],
        **{f"{subject}_context": {"show_grid": "no", "axis_range": "x: [-2, 10/3], y: [0, 4]"}},
    )

    result = SolutionOrchestrator(console=MagicMock())._dispatch_diagrams(
        [req], None, subject, "PROBLEM"
    )

    assert result == {"graph_1": "DIAGRAM CODE"}
    assert received["description"] == req.description
    assert received["problem_text"] == "PROBLEM"
    assert received["values"] == req.values
    assert received["labels"] == []
    context = received["solution_context"]
    assert req.context in context
    assert req.annotations[0] in context
    assert "show_grid: no" in context
    assert "axis_range: x: [-2, 10/3], y: [0, 4]" in context
    assert "Requested diagram size: medium" in context


def test_diagram_context_handles_legacy_requirements_without_optional_fields():
    assert SolutionOrchestrator._diagram_generation_context(SimpleNamespace()) == ""


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

    problem_latex = r"\begin{problem}Find x.\end{problem}"
    result = orchestrator.run(
        problem_latex=problem_latex,
        subject="physics",
        question_type="subjective",
    )

    orchestrator._dispatch_diagrams.assert_called_once_with(
        orchestrator._call_subject_agent.return_value.diagram_requirements,
        None,
        "physics",
        problem_latex,
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


def test_run_appends_multipart_subjective_answer_enumerate():
    orchestrator = _orchestrator()
    labelled_answer = (
        r"\begin{enumerate}[label=(\alph*), leftmargin=*]"
        r"\item $x=1$."
        r"\item $x=2$."
        r"\end{enumerate}"
    )
    plain_answer = labelled_answer.replace(
        r"\begin{enumerate}[label=(\alph*), leftmargin=*]",
        r"\begin{enumerate}",
    )
    orchestrator._call_subject_agent = MagicMock(
        return_value=SimpleNamespace(
            solution_latex=(
                r"\begin{solution}"
                r"\begin{enumerate}[label=(\alph*), leftmargin=*]"
                r"\item First.\item Second.\end{enumerate}"
                r"\end{solution}"
            ),
            diagram_requirements=[],
            answer_type="subjective",
            answer_value=None,
            final_answer_latex=labelled_answer,
        )
    )

    result = orchestrator.run(
        problem_latex=(
            r"\item Solve both."
            r"\begin{enumerate}[label=(\alph*), leftmargin=*]"
            r"\item First.\item Second.\end{enumerate}"
        ),
        subject="mathematics",
        question_type="subjective",
    )

    assert result.final_answer_latex == plain_answer
    assert "[label=" not in result.latex
    assert result.latex.endswith(
        "\\begin{finalanswer}\n" + plain_answer + "\n\\end{finalanswer}"
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
