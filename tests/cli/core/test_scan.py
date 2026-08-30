"""Regression tests for the standalone problem-only scan command."""

import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from rich.console import Console

from vbagent.agents.classification.question_classifier import (
    QuestionRoutingClassification,
)
from vbagent.cli.core import scan as scan_module
from vbagent.cli.core.scan import scan


def _console() -> Console:
    return Console(file=StringIO(), force_terminal=False)


def test_classify_for_scan_uses_the_canonical_stage_without_overrides(
    monkeypatch,
):
    expected = object()
    cache = object()
    calls = []

    def fake_classify(image_path, *, cache, problem_id, console):
        calls.append((image_path, cache, problem_id, console))
        return expected

    monkeypatch.setattr(
        "vbagent.pipeline.stages.classify_question",
        fake_classify,
    )
    console = _console()

    result = scan_module._classify_for_scan(
        "problem_1.png",
        None,
        None,
        cache,
        "problem_1",
        console,
    )

    assert result is expected
    assert calls == [("problem_1.png", cache, "problem_1", console)]


def test_classify_for_scan_applies_complete_routing_override(monkeypatch):
    expected = object()
    routed = []

    def fail_automatic_classification(*args, **kwargs):
        raise AssertionError("automatic classification must not run")

    def fake_detailed_classification(image_path, *, routing, show_spinner):
        routed.append((image_path, routing, show_spinner))
        return expected

    monkeypatch.setattr(
        "vbagent.pipeline.stages.classify_question",
        fail_automatic_classification,
    )
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_route",
        fail_automatic_classification,
    )
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        fake_detailed_classification,
    )

    result = scan_module._classify_for_scan(
        "problem_1.png",
        "integer",
        "mathematics",
        object(),
        "problem_1",
        _console(),
    )

    assert result is expected
    assert len(routed) == 1
    assert routed[0][0] == "problem_1.png"
    assert routed[0][1].subject == "mathematics"
    assert routed[0][1].question_type == "integer"
    assert routed[0][2] is True


@pytest.mark.parametrize(
    "question_type, subject, expected_type, expected_subject",
    [
        ("subjective", None, "subjective", "physics"),
        (None, "biology", "mcq_sc", "biology"),
    ],
)
def test_classify_for_scan_routes_the_missing_override_field(
    monkeypatch,
    question_type,
    subject,
    expected_type,
    expected_subject,
):
    initial = QuestionRoutingClassification(
        subject="physics",
        question_type="mcq_sc",
    )
    routed = []

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_route",
        lambda image_path, show_spinner: initial,
    )

    def fake_detailed_classification(image_path, *, routing, show_spinner):
        routed.append(routing)
        return object()

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        fake_detailed_classification,
    )

    scan_module._classify_for_scan(
        "problem_1.png",
        question_type,
        subject,
        object(),
        "problem_1",
        _console(),
    )

    assert routed[0].question_type == expected_type
    assert routed[0].subject == expected_subject


@pytest.mark.parametrize(
    "environment",
    ["solution", "alternateSolution", "finalanswer"],
)
def test_problem_only_boundary_rejects_solution_environments(environment):
    with pytest.raises(ValueError, match="refusing to emit"):
        scan_module._require_problem_only(
            rf"\item Question.\begin{{{environment}}}Work.\end{{{environment}}}"
        )


def test_scan_uses_problem_orchestrator_and_saves_problem_only_latex(
    monkeypatch,
    tmp_path,
):
    image = tmp_path / "problem_1.png"
    image.touch()
    output = tmp_path / "problem_1.tex"
    cache = object()
    classification = SimpleNamespace(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
        diagram_type=None,
    )
    calls = []

    monkeypatch.setattr("vbagent.cache.PipelineCache", lambda: cache)
    monkeypatch.setattr(
        scan_module,
        "_classify_for_scan",
        lambda *args: classification,
    )
    monkeypatch.setattr(scan_module, "display_scan_result", lambda *args: None)
    monkeypatch.setattr(
        "vbagent.cli.interfaces.ui.print_classification",
        lambda *args: None,
    )

    def fake_problem_stage(
        image_path,
        received_classification,
        *,
        use_context,
        cache,
        problem_id,
        console,
    ):
        calls.append(
            (
                image_path,
                received_classification,
                use_context,
                cache,
                problem_id,
            )
        )
        return SimpleNamespace(latex=r"\item Find the range.", tikz_code=None)

    monkeypatch.setattr(
        "vbagent.pipeline.stages.run_problem_orchestrator",
        fake_problem_stage,
    )

    result = CliRunner().invoke(
        scan,
        ["-i", str(image), "-o", str(output), "--quiet"],
    )

    assert result.exit_code == 0, result.output
    assert output.read_text() == r"\item Find the range."
    assert calls == [
        (str(image), classification, True, cache, "problem_1")
    ]


def test_scan_refuses_to_write_solution_content_from_problem_stage(
    monkeypatch,
    tmp_path,
):
    image = tmp_path / "problem_1.png"
    image.touch()
    output = tmp_path / "problem_1.tex"
    classification = SimpleNamespace(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
        diagram_type=None,
    )

    monkeypatch.setattr("vbagent.cache.PipelineCache", lambda: object())
    monkeypatch.setattr(
        scan_module,
        "_classify_for_scan",
        lambda *args: classification,
    )
    monkeypatch.setattr(
        "vbagent.cli.interfaces.ui.print_classification",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "vbagent.pipeline.stages.run_problem_orchestrator",
        lambda *args, **kwargs: SimpleNamespace(
            latex=(
                r"\item Find the range."
                r"\begin{solution}Generated work.\end{solution}"
            ),
            tikz_code=None,
        ),
    )

    result = CliRunner().invoke(
        scan,
        ["-i", str(image), "-o", str(output), "--quiet"],
    )

    assert result.exit_code == 1
    assert "refusing to emit" in result.output
    assert not output.exists()


def test_scan_defaults_to_the_run_workspace_and_saves_classification(
    monkeypatch,
    tmp_path,
):
    image = tmp_path / "images" / "problem_1.png"
    image.parent.mkdir()
    image.touch()
    cache = object()

    class FakeClassification:
        subject = "mathematics"
        question_type = "subjective"
        has_diagram = False
        diagram_type = None

        def model_dump_json(self, indent=None):
            return json.dumps(
                {
                    "subject": self.subject,
                    "question_type": self.question_type,
                    "has_diagram": self.has_diagram,
                },
                indent=indent,
            )

    classification = FakeClassification()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("vbagent.cache.PipelineCache", lambda: cache)
    monkeypatch.setattr(
        scan_module,
        "_classify_for_scan",
        lambda *args: classification,
    )
    monkeypatch.setattr(scan_module, "display_scan_result", lambda *args: None)
    monkeypatch.setattr(
        "vbagent.cli.interfaces.ui.print_classification",
        lambda *args: None,
    )
    monkeypatch.setattr(
        "vbagent.pipeline.stages.run_problem_orchestrator",
        lambda *args, **kwargs: SimpleNamespace(
            latex=r"\item Find the period.",
            tikz_code=None,
        ),
    )

    result = CliRunner().invoke(
        scan,
        ["-i", str(image), "--quiet"],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "agentic/scans/problem_1.tex").read_text() == (
        r"\item Find the period."
    )
    metadata = json.loads(
        (tmp_path / "agentic/classifications/problem_1.json").read_text()
    )
    assert metadata["subject"] == "mathematics"


def test_scan_help_states_problem_only_contract_and_current_overrides():
    result = CliRunner().invoke(scan, ["--help"])

    assert result.exit_code == 0
    assert "problem-only LaTeX" in result.output
    assert "integer" in result.output
    assert "biology" in result.output
    assert "--reference" not in result.output
    assert "agentic/scans" in result.output
