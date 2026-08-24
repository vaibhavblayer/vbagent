"""Tests for generic routing and subject-specific prompt caching."""

from types import SimpleNamespace

from agents import ModelSettings

from vbagent.agents.classification import question_classifier


def _route(subject="physics", question_type="mcq_sc"):
    return question_classifier.QuestionRoutingClassification(
        subject=subject,
        question_type=question_type,
    )


def _analysis():
    return question_classifier.SubjectSpecificQuestionAnalysis(
        has_diagram=False,
    )


def test_each_uncached_classification_uses_router_then_subject_group(monkeypatch):
    groups = []

    monkeypatch.setattr(
        question_classifier,
        "create_question_router",
        lambda: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "create_question_classifier",
        lambda subject: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "_routing_message",
        lambda path, model: [path, model],
    )
    monkeypatch.setattr(
        question_classifier,
        "_classification_message",
        lambda path, subject, question_type, model: [
            path,
            subject,
            question_type,
            model,
        ],
    )

    def fake_run(agent, message, group_id, **kwargs):
        groups.append(group_id)
        return _route() if "router" in group_id else _analysis()

    monkeypatch.setattr(question_classifier, "run_agent_sync_grouped", fake_run)

    question_classifier.classify_question_image("one.png")
    question_classifier.classify_question_image("two.png")

    assert groups == [
        "vbagent:question-router:v1",
        "vbagent:question-analyzer:v1:physics",
    ] * 2


def test_generic_route_selects_subject_specific_cache_group(monkeypatch):
    groups = []

    monkeypatch.setattr(
        question_classifier,
        "create_question_router",
        lambda: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "create_question_classifier",
        lambda subject: SimpleNamespace(model="gpt-5.6-sol"),
    )
    monkeypatch.setattr(
        question_classifier,
        "_routing_message",
        lambda path, model: [path, model],
    )
    monkeypatch.setattr(
        question_classifier,
        "_classification_message",
        lambda path, subject, question_type, model: [
            path,
            subject,
            question_type,
            model,
        ],
    )

    def fake_run(agent, message, group_id, **kwargs):
        groups.append(group_id)
        return (
            _route("chemistry", "subjective")
            if len(groups) == 1
            else _analysis()
        )

    monkeypatch.setattr(question_classifier, "run_agent_sync_grouped", fake_run)

    result = question_classifier.classify_question_image("chemistry.png")

    assert groups == [
        "vbagent:question-router:v1",
        "vbagent:question-analyzer:v1:chemistry",
    ]
    assert result.subject == "chemistry"
    assert result.question_type == "subjective"


def test_cached_route_skips_generic_router(monkeypatch):
    monkeypatch.setattr(
        question_classifier,
        "classify_question_route",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("cached route should skip generic router")
        ),
    )
    monkeypatch.setattr(
        question_classifier,
        "create_question_classifier",
        lambda subject: SimpleNamespace(model="gpt-5.5"),
    )
    monkeypatch.setattr(
        question_classifier,
        "_classification_message",
        lambda *args: list(args),
    )
    monkeypatch.setattr(
        question_classifier,
        "run_agent_sync_grouped",
        lambda *args, **kwargs: _analysis(),
    )

    result = question_classifier.classify_question_image(
        "question.png",
        routing=_route("mathematics", "subjective"),
    )

    assert result.subject == "mathematics"
    assert result.question_type == "subjective"


def test_gpt56_messages_use_separate_explicit_boundaries(monkeypatch):
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

    routing = question_classifier._routing_message(
        "question.png",
        "gpt-5.6-sol",
    )
    analysis = question_classifier._classification_message(
        "question.png",
        "mathematics",
        "subjective",
        "gpt-5.6-sol",
    )

    assert routing[0].startswith("Apply the stable subject-neutral")
    assert routing[2] == "Determine only the subject and question type."
    assert analysis[0].startswith("Apply the stable subject-specific")
    assert "routed mathematics subjective" in analysis[2]


def test_non_gpt56_messages_keep_plain_image_payloads(monkeypatch):
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

    assert question_classifier._routing_message(
        "question.png",
        "gpt-5.5",
    ) == ["question.png", "Determine only the subject and question type."]
    assert "routed physics mcq_sc" in question_classifier._classification_message(
        "question.png",
        "physics",
        "mcq_sc",
        "gpt-5.5",
    )[1]


def test_gpt56_router_and_analyzer_enable_explicit_cache_mode(monkeypatch):
    captured = []
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
        captured.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(question_classifier, "create_agent", fake_create_agent)

    question_classifier.create_question_router()
    question_classifier.create_question_classifier("physics")

    assert [item["name"] for item in captured] == [
        "QuestionRouter",
        "QuestionAnalyzer-physics",
    ]
    assert all(
        item["model_settings"].prompt_cache_options
        == {"mode": "explicit", "ttl": "30m"}
        for item in captured
    )
