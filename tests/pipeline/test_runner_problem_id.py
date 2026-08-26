"""Regression tests for image-pipeline problem identity."""

from types import SimpleNamespace

from vbagent.agents.classification import question_classifier
from vbagent.pipeline import runner, stages


def test_image_pipeline_derives_problem_id_from_source_path(monkeypatch):
    """CLI image runs omit problem_id, so the runner must derive it safely."""
    classification = SimpleNamespace(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
        diagram_type=None,
        chapter="Kinematics",
        topic="Projectile motion",
    )
    primary = SimpleNamespace(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
        confidence=1.0,
        classified_from="image",
    )
    seen_problem_ids: list[str] = []

    def classify_question(_image_path, **kwargs):
        seen_problem_ids.append(kwargs["problem_id"])
        return classification

    def run_problem_orchestrator(_image_path, _classification, **kwargs):
        seen_problem_ids.append(kwargs["problem_id"])
        return SimpleNamespace(latex=r"\item Test problem", tikz_code=None)

    monkeypatch.setattr(stages, "classify_question", classify_question)
    monkeypatch.setattr(stages, "run_problem_orchestrator", run_problem_orchestrator)
    monkeypatch.setattr(
        question_classifier,
        "classification_fingerprint",
        lambda _classification: "classification-fingerprint",
    )
    monkeypatch.setattr(
        question_classifier,
        "to_primary_classification",
        lambda _classification: primary,
    )
    monkeypatch.setattr(
        question_classifier,
        "to_diagram_analysis",
        lambda _classification: None,
    )
    monkeypatch.setattr(runner, "extract_problem_solution", lambda _latex: ("", ""))
    monkeypatch.setattr(runner, "generate_variants_stage", lambda *_args, **_kwargs: {})

    result = runner._process_image_impl(
        "images/problem_1.png",
        problem_id=None,
        use_cache=False,
        merge_metadata=False,
    )

    assert result.source_path == "images/problem_1.png"
    assert seen_problem_ids == ["problem_1", "problem_1"]
