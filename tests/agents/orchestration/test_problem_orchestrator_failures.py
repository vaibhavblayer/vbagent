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

    def get_stage_data(self, problem_id, stage):
        if stage == "scan":
            return {"match_table_contract_version": 2}
        if stage == "tikz":
            return {"match_table_contract_version": 1}
        return {}

    def set(self, problem_id, stage, value, stage_data=None):
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


def test_match_diagram_description_requires_row_macros_not_montage():
    primary = SimpleNamespace(question_type="match")
    diagram = SimpleNamespace(diagram_type="graph")

    description = ProblemOrchestrator._main_diagram_description(primary, diagram)

    assert r"\def\MatchA" in description
    assert "Do not combine table rows into one montage" in description
    assert "baseline=(current bounding box.center)" in description
    assert r"do not output any \def\Option definitions" in description


def test_match_question_refreshes_legacy_scan_and_tikz_cache(monkeypatch):
    class _LegacyMatchCache(_Cache):
        def get_stage_data(self, problem_id, stage):
            return {}

    cache = _LegacyMatchCache({
        "scan": "legacy scan",
        "tikz": "legacy montage",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="match",
        has_diagram=True,
        diagram_type="graph",
    )
    captured = {}
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    def fake_parallel(*args, **kwargs):
        captured["scan_cached"] = args[4]
        captured["tikz_cached"] = args[5]
        return (
            r"\item Match.\begin{tabular}{cc}(A)&\MatchA\end{tabular}",
            r"\def\MatchA{\begin{tikzpicture}\draw(0,0)--(1,1);\end{tikzpicture}}",
            None,
        )

    monkeypatch.setattr(orchestrator, "_run_parallel", fake_parallel)

    result = orchestrator.run(
        "question.png", classification, cache=cache, problem_id="legacy_match"
    )

    assert captured["scan_cached"] is False
    assert captured["tikz_cached"] is False
    assert "legacy montage" not in result.latex
    assert result.latex.count(r"\def\MatchA") == 1


def test_match_question_assembles_column_two_p_to_s_macros():
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )
    latex = r"""\item Match.
\begin{tabular}{cc|cc}
(A) & First & (P) & \MatchP \\
(B) & Second & (Q) & \MatchQ \\
(C) & Third & (R) & \MatchR \\
(D) & Fourth & (S) & \MatchS \\
\end{tabular}"""
    tikz_code = r"""\def\MatchP{\begin{tikzpicture}\node{P};\end{tikzpicture}}
\def\MatchQ{\begin{tikzpicture}\node{Q};\end{tikzpicture}}
\def\MatchR{\begin{tikzpicture}\node{R};\end{tikzpicture}}
\def\MatchS{\begin{tikzpicture}\node{S};\end{tikzpicture}}"""

    assembled = orchestrator._assemble_latex(latex, tikz_code)

    for letter in "PQRS":
        assert assembled.count(rf"\def\Match{letter}") == 1
    assert assembled.index(r"\def\MatchP") < assembled.index(
        r"\begin{tabular}"
    )


def test_passage_refreshes_legacy_scan_and_option_diagram_cache(monkeypatch):
    class _LegacyPassageCache(_Cache):
        def get_stage_data(self, problem_id, stage):
            return {}

    cache = _LegacyPassageCache({
        "scan": r"\item Old.\begin{tasks}(2)\task Graph (a)\end{tasks}",
        "options": r"\def\OptionA{old}",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="passage",
        has_diagram=False,
        has_option_diagrams=True,
        num_option_diagrams=8,
        option_diagram_type="graph",
    )
    captured = {}
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    def fake_parallel(*args, **kwargs):
        captured["scan_cached"] = args[4]
        captured["options_cached"] = args[6]
        return (
            r"\item Passage.\begin{tasks}(2)\task \OptionA\task \OptionH\end{tasks}",
            r"\def\OptionA{new A}\def\OptionH{new H}",
            r"\def\OptionA{new A}\def\OptionH{new H}",
        )

    monkeypatch.setattr(orchestrator, "_run_parallel", fake_parallel)

    result = orchestrator.run(
        "question.png", classification, cache=cache, problem_id="passage_1"
    )

    assert captured["scan_cached"] is False
    assert captured["options_cached"] is False
    assert "old" not in result.latex
    assert result.latex.count(r"\def\OptionH") == 1


def test_assertion_reason_refreshes_scan_from_old_diagram_contract(monkeypatch):
    class _LegacyAssertionCache(_Cache):
        def get_stage_data(self, problem_id, stage):
            return {}

    cache = _LegacyAssertionCache({
        "scan": r"\item Old.\begin{center}\text{[Diagram]}\end{center}",
        "tikz": r"\begin{tikzpicture}\node{motion};\end{tikzpicture}",
    })
    classification = QuestionClassification(
        subject="physics",
        question_type="assertion_reason",
        has_diagram=True,
        diagram_type="mechanics",
    )
    captured = {}
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    def fake_parallel(*args, **kwargs):
        captured["scan_cached"] = args[4]
        captured["tikz_cached"] = args[5]
        return (
            r"\item New.\begin{center}\input{diagram}\end{center}",
            cache.values["tikz"],
            None,
        )

    monkeypatch.setattr(orchestrator, "_run_parallel", fake_parallel)

    result = orchestrator.run(
        "question.png", classification, cache=cache, problem_id="problem_68"
    )

    assert captured["scan_cached"] is False
    assert captured["tikz_cached"] is True
    assert r"\input{diagram}" not in result.latex
    assert "[Diagram]" not in result.latex
    assert result.latex.count(r"\begin{tikzpicture}") == 1
