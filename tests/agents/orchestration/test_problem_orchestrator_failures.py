"""Failure propagation tests for parallel problem stages."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from rich.console import Console

from vbagent.agents.orchestration.problem_orchestrator import ProblemOrchestrator
from vbagent.agents.classification.question_classifier import (
    QuestionClassification,
    classification_fingerprint,
)


class _Cache:
    def __init__(self, values, classification=None):
        self.values = values
        self.stage_data = {}
        if classification is not None:
            fingerprint = classification_fingerprint(classification)
            for stage in values:
                self.stage_data[stage] = {
                    "classification_fingerprint": fingerprint,
                }

    def has(self, problem_id, stage):
        return stage in self.values

    def get(self, problem_id, stage):
        return self.values.get(stage)

    def get_stage_data(self, problem_id, stage):
        stage_data = dict(self.stage_data.get(stage, {}))
        if stage == "scan":
            stage_data.update({
                "match_table_contract_version": 2,
                "subjective_structure_contract_version": 1,
            })
        if stage == "tikz":
            stage_data["match_table_contract_version"] = 1
        return stage_data

    def set(self, problem_id, stage, value, stage_data=None):
        self.values[stage] = value
        self.stage_data[stage] = stage_data or {}


def _main_classification(
    question_type,
    *,
    diagram_type="mechanics",
    diagram_category="mechanics",
    **kwargs,
):
    return QuestionClassification(
        subject="physics",
        question_type=question_type,
        has_diagram=True,
        diagram_type=diagram_type,
        diagram_category=diagram_category,
        diagram_complexity="moderate",
        diagram_elements=["test diagram"],
        suggested_tikz_agent=diagram_type,
        **kwargs,
    )


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
    classification = _main_classification("subjective")
    cache = _Cache({
        "scan": r"\item Example\begin{center}\input{diagram}\end{center}",
        "tikz": r"\begin{tikzpicture}\draw (0,0)--(1,1);\end{tikzpicture}",
    }, classification=classification)
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
    classification = QuestionClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
    )
    cache = _Cache({
        "scan": r"\item Example\begin{center}\input{diagram}\end{center}",
    }, classification=classification)
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
    assert cache.stage_data["tikz"]["classification_fingerprint"] == (
        classification_fingerprint(classification)
    )
    assert r"\input{diagram}" not in result.latex
    assert r"\begin{tikzpicture}" in result.latex
    assert r"\draw (0,0)--(1,1);" in result.latex


def test_option_only_question_removes_spurious_main_placeholder():
    classification = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
        has_option_diagrams=True,
        num_option_diagrams=2,
        option_diagram_type="graph",
    )
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
    }, classification=classification)
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
    classification = _main_classification(
        "mcq_sc",
        has_option_diagrams=True,
        num_option_diagrams=2,
        option_diagram_type="graph",
    )
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
    }, classification=classification)
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


def test_changed_classification_invalidates_scan_tikz_and_option_caches(
    monkeypatch,
):
    old_classification = _main_classification(
        "mcq_sc",
        has_option_diagrams=True,
        num_option_diagrams=2,
        option_diagram_type="graph",
        topic="old topic",
    )
    current_classification = old_classification.model_copy(
        update={"topic": "new topic"}
    )
    cache = _Cache(
        {
            "scan": "old scan",
            "tikz": "old main diagram",
            "options": "old option diagrams",
        },
        classification=old_classification,
    )
    captured = {}
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    def fake_parallel(*args, **kwargs):
        captured["scan_cached"] = args[4]
        captured["tikz_cached"] = args[5]
        captured["options_cached"] = args[6]
        return ("new scan", None, None)

    monkeypatch.setattr(orchestrator, "_run_parallel", fake_parallel)

    result = orchestrator.run(
        "question.png",
        current_classification,
        cache=cache,
        problem_id="changed_classification",
    )

    assert captured == {
        "scan_cached": False,
        "tikz_cached": False,
        "options_cached": False,
    }
    assert result.latex == "new scan"


def test_stage_contract_metadata_includes_classification_fingerprint():
    fingerprint = "classification-sha256"

    assert ProblemOrchestrator._scan_stage_data(
        "subjective",
        fingerprint,
    ) == {
        "subjective_structure_contract_version": 1,
        "classification_fingerprint": fingerprint,
    }
    assert ProblemOrchestrator._tikz_stage_data(
        "match",
        fingerprint,
    ) == {
        "match_table_contract_version": 1,
        "classification_fingerprint": fingerprint,
    }
    assert ProblemOrchestrator._option_stage_data(
        "passage",
        fingerprint,
    ) == {
        "passage_option_contract_version": 1,
        "classification_fingerprint": fingerprint,
    }


def test_match_diagram_description_requires_row_macros_not_montage():
    primary = SimpleNamespace(question_type="match")
    diagram = SimpleNamespace(diagram_type="graph")

    description = ProblemOrchestrator._main_diagram_description(primary, diagram)

    assert r"\def\MatchA" in description
    assert "Do not combine table rows into one montage" in description
    assert "baseline=(current bounding box.center)" in description
    assert r"do not output any \def\Option definitions" in description


def test_subjective_main_diagram_description_requires_panel_layout():
    primary = SimpleNamespace(question_type="subjective")
    diagram = SimpleNamespace(diagram_type="function_graph")

    description = ProblemOrchestrator._main_diagram_description(primary, diagram)

    assert "own locally defined panel command" in description
    assert "multicols plus enumerate" in description
    assert "Let enumerate own the labels" in description
    assert "shifted-scope TikZ canvas" in description


def test_subjective_question_refreshes_legacy_scan_cache(monkeypatch):
    class _LegacySubjectiveCache(_Cache):
        def get_stage_data(self, problem_id, stage):
            return {}

    cache = _LegacySubjectiveCache({
        "scan": (
            r"\item Which graphs? %% OPTIONS_DIAGRAMS "
            r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}"
        ),
        "tikz": r"\begin{tikzpicture}\node{main};\end{tikzpicture}",
    })
    classification = _main_classification("subjective")
    captured = {}
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )

    def fake_parallel(*args, **kwargs):
        captured["scan_cached"] = args[4]
        captured["tikz_cached"] = args[5]
        return (
            r"\item Which graphs?\begin{center}\input{diagram}\end{center}",
            cache.values["tikz"],
            None,
        )

    monkeypatch.setattr(orchestrator, "_run_parallel", fake_parallel)

    result = orchestrator.run(
        "question.png",
        classification,
        cache=cache,
        problem_id="legacy_subjective",
    )

    assert captured["scan_cached"] is False
    assert captured["tikz_cached"] is False
    assert "OPTIONS_DIAGRAMS" not in result.latex
    assert r"\begin{tasks}" not in result.latex
    assert result.latex.count(r"\begin{tikzpicture}") == 1


def test_subjective_orchestrator_rejects_option_structure(monkeypatch):
    classification = _main_classification("subjective")
    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )
    invalid = (
        r"\item Which graphs? %% OPTIONS_DIAGRAMS "
        r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}"
    )

    monkeypatch.setattr(
        orchestrator,
        "_run_parallel",
        lambda *args, **kwargs: (
            invalid,
            r"\begin{tikzpicture}\node{main};\end{tikzpicture}",
            None,
        ),
    )

    with pytest.raises(ValueError, match="forbidden MCQ option structure"):
        orchestrator.run("question.png", classification)


def test_subjective_scan_markers_never_trigger_option_diagram_fallback(monkeypatch):
    from vbagent.agents.content_generation import scanner

    invalid = (
        r"\item Which graphs? %% OPTIONS_DIAGRAMS "
        r"\begin{tasks}(2)\task[(i)] \OptionA\end{tasks}"
    )
    monkeypatch.setattr(scanner, "scan_problem", lambda *args, **kwargs: invalid)

    orchestrator = ProblemOrchestrator(
        console=Console(file=io.StringIO(), force_terminal=False)
    )
    monkeypatch.setattr(
        orchestrator,
        "_run_option_diagrams_sync",
        lambda *args, **kwargs: pytest.fail(
            "subjective scan must not trigger option diagram generation"
        ),
    )
    primary = SimpleNamespace(
        subject="mathematics",
        question_type="subjective",
    )

    latex, tikz_code, option_tikz = orchestrator._run_parallel(
        "question.png",
        primary,
        diagram_analysis=None,
        sample=None,
        scan_cached=False,
        tikz_cached=False,
        options_cached=False,
        cache=None,
        problem_id=None,
        needs_tikz=False,
        needs_options=False,
    )

    assert latex == invalid
    assert tikz_code is None
    assert option_tikz is None


def test_match_question_refreshes_legacy_scan_and_tikz_cache(monkeypatch):
    class _LegacyMatchCache(_Cache):
        def get_stage_data(self, problem_id, stage):
            return {}

    cache = _LegacyMatchCache({
        "scan": "legacy scan",
        "tikz": "legacy montage",
    })
    classification = _main_classification(
        "match",
        diagram_type="graph",
        diagram_category="graphs",
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
    classification = _main_classification("assertion_reason")
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
    assert captured["tikz_cached"] is False
    assert r"\input{diagram}" not in result.latex
    assert "[Diagram]" not in result.latex
    assert result.latex.count(r"\begin{tikzpicture}") == 1
