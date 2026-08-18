"""Failure propagation tests for parallel problem stages."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from rich.console import Console

from vbagent.agents.orchestration.problem_orchestrator import ProblemOrchestrator
from vbagent.agents.classification.question_classifier import QuestionClassification


class _Cache:
    def __init__(self, values):
        self.values = values

    def has(self, problem_id, stage):
        return stage in self.values

    def get(self, problem_id, stage):
        return self.values.get(stage)

    def set(self, problem_id, stage, value):
        self.values[stage] = value


def test_parallel_tikz_failure_is_not_silently_dropped(monkeypatch):
    from vbagent.agents.content_generation import scanner
    from vbagent.agents.diagram import tikz_router

    monkeypatch.setattr(scanner, "scan_problem", lambda *a, **k: "problem latex")

    def fail_tikz(*args, **kwargs):
        raise RuntimeError("tikz response failed")

    monkeypatch.setattr(tikz_router, "generate_tikz_with_routing", fail_tikz)

    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )
    primary = SimpleNamespace(subject="physics", question_type="subjective")
    diagram = SimpleNamespace(
        suggested_tikz_agent="generic",
        diagram_type="generic",
        diagram_draw_description=None,
    )

    with pytest.raises(RuntimeError, match="tikz response failed"):
        orchestrator._run_parallel(
            "question.png",
            primary,
            diagram,
            sample=None,
            scan_cached=False,
            tikz_cached=False,
            options_cached=False,
            cache=None,
            problem_id=None,
            needs_tikz=True,
            needs_options=False,
        )


def test_full_cache_hit_still_assembles_scan_and_tikz():
    cache = _Cache({
        "scan": r"\item Example\begin{center}\input{diagram}\end{center}",
        "tikz": r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=True,
    )
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    result = orchestrator.run(
        "question.png",
        classification,
        cache=cache,
        problem_id="problem_1",
    )

    assert r"\input{diagram}" not in result.latex
    assert r"\begin{tikzpicture}" in result.latex


def test_scan_placeholder_self_heals_no_diagram_classification(monkeypatch):
    from vbagent.agents.diagram import tikz_router

    generated = r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}"
    calls = []

    def generate(*args, **kwargs):
        calls.append(kwargs)
        return generated, "generic"

    monkeypatch.setattr(tikz_router, "generate_tikz_with_routing", generate)
    cache = _Cache({
        "scan": r"\item Example\begin{center}\input{diagram}\end{center}",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
    )
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    result = orchestrator.run(
        "question.png",
        classification,
        cache=cache,
        problem_id="problem_10",
    )

    assert len(calls) == 1
    assert calls[0]["diagram_context"] == "problem"
    assert cache.values["tikz"] == generated
    assert r"\input{diagram}" not in result.latex
    assert r"\begin{tikzpicture}" in result.latex
    assert r"\draw (0,0)--(1,1);" in result.latex


def test_option_only_question_removes_spurious_main_placeholder():
    cache = _Cache({
        "scan": r"""\item Choose the graph.
\begin{center}\input{diagram}\end{center}
\begin{tasks}(2)
\task \OptionA
\task \OptionB \ans
\end{tasks}""",
        # A stale main artifact from an older classification must be ignored.
        "tikz": r"\begin{tikzpicture}\node{duplicate composite};\end{tikzpicture}",
        "options": r"""\def\OptionA{\begin{tikzpicture}\node{A};\end{tikzpicture}}
\def\OptionB{\begin{tikzpicture}\node{B};\end{tikzpicture}}""",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
        has_option_diagrams=True,
        num_option_diagrams=2,
        option_diagram_type="graph",
    )
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    result = orchestrator.run(
        "question.png", classification, cache=cache, problem_id="problem_18"
    )

    assert r"\input{diagram}" not in result.latex
    assert "duplicate composite" not in result.latex
    assert result.latex.count(r"\def\OptionA") == 1
    assert result.latex.count(r"\def\OptionB") == 1


def test_main_and_option_diagrams_are_both_preserved_once():
    cache = _Cache({
        "scan": r"""\item Use the setup and choose the graph.
\begin{center}\input{diagram}\end{center}
\begin{tasks}(2)
\task \OptionA
\task \OptionB \ans
\end{tasks}""",
        # Main-agent leakage is discarded when the dedicated option artifact
        # is merged.
        "tikz": r"""\begin{tikzpicture}\node{main setup};\end{tikzpicture}
\def\OptionA{\begin{tikzpicture}\node{wrong A};\end{tikzpicture}}
\def\OptionB{\begin{tikzpicture}\node{wrong B};\end{tikzpicture}}""",
        "options": r"""\def\OptionA{\begin{tikzpicture}\node{A};\end{tikzpicture}}
\def\OptionB{\begin{tikzpicture}\node{B};\end{tikzpicture}}""",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=True,
        diagram_type="mechanics",
        has_option_diagrams=True,
        num_option_diagrams=2,
        option_diagram_type="graph",
    )
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    result = orchestrator.run(
        "question.png", classification, cache=cache, problem_id="problem_both"
    )

    assert r"\input{diagram}" not in result.latex
    assert result.latex.count("main setup") == 1
    assert result.latex.count(r"\def\OptionA") == 1
    assert result.latex.count(r"\def\OptionB") == 1
    assert "wrong A" not in result.latex
    assert "wrong B" not in result.latex
