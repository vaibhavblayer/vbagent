"""Tests for subject-scoped question-classifier prompt caching."""

from types import SimpleNamespace

from agents import ModelSettings

from vbagent.agents.classification import question_classifier


def _result(subject: str):
    return SimpleNamespace(subject=subject)


def test_same_subject_reuses_classifier_cache_group(monkeypatch):
    groups = []

    monkeypatch.setattr(
        question_classifier,
        "create_question_classifier",
        lambda subject: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "_classification_message",
        lambda path, subject, model: [path, subject, model],
    )

    def fake_run(agent, message, group_id, **kwargs):
        groups.append(group_id)
        return _result("physics")

    monkeypatch.setattr(question_classifier, "run_agent_sync_grouped", fake_run)

    question_classifier.classify_question_image("one.png", subject="physics")
    question_classifier.classify_question_image("two.png", subject="physics")

    assert groups == ["vbagent:question-classifier:v3:physics"] * 2


def test_subject_correction_switches_cache_group(monkeypatch):
    groups = []
    results = iter([_result("chemistry"), _result("chemistry")])

    monkeypatch.setattr(question_classifier, "_initial_subject", lambda *args: "physics")
    monkeypatch.setattr(
        question_classifier,
        "create_question_classifier",
        lambda subject: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "_classification_message",
        lambda path, subject, model: [path, subject, model],
    )

    def fake_run(agent, message, group_id, **kwargs):
        groups.append(group_id)
        return next(results)

    monkeypatch.setattr(question_classifier, "run_agent_sync_grouped", fake_run)

    question_classifier.classify_question_image("chemistry.png")

    assert groups == [
        "vbagent:question-classifier:v3:physics",
        "vbagent:question-classifier:v3:chemistry",
    ]


def test_gpt56_classifier_uses_explicit_boundary_before_image(monkeypatch):
    monkeypatch.setattr(
        question_classifier,
        "get_config",
        lambda: SimpleNamespace(base_url=None),
    )
    monkeypatch.setattr(
        question_classifier,
        "create_cacheable_image_message",
        lambda path, text, boundary: [boundary, path, text],
    )

    message = question_classifier._classification_message(
        "question.png", "physics", "gpt-5.6-sol",
    )

    assert message[0].startswith("Apply the stable classifier instructions")
    assert message[1:] == ["question.png", "Classify and analyze this physics question."]


def test_non_gpt56_classifier_keeps_plain_image_message(monkeypatch):
    monkeypatch.setattr(
        question_classifier,
        "get_config",
        lambda: SimpleNamespace(base_url=None),
    )
    monkeypatch.setattr(
        question_classifier,
        "create_image_message",
        lambda path, text: [path, text],
    )

    assert question_classifier._classification_message(
        "question.png", "physics", "gpt-5.5",
    ) == ["question.png", "Classify and analyze this physics question."]


def test_gpt56_classifier_enables_explicit_cache_mode(monkeypatch):
    captured = {}
    monkeypatch.setattr(question_classifier, "get_model", lambda _: "gpt-5.6-sol")
    monkeypatch.setattr(
        question_classifier,
        "get_model_settings",
        lambda _: ModelSettings(reasoning={"effort": "high"}),
    )
    monkeypatch.setattr(
        question_classifier,
        "get_config",
        lambda: SimpleNamespace(base_url=None),
    )

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(question_classifier, "create_agent", fake_create_agent)

    question_classifier.create_question_classifier("physics")

    assert captured["model"] == "gpt-5.6-sol"
    assert captured["model_settings"].prompt_cache_options == {
        "mode": "explicit",
        "ttl": "30m",
    }
