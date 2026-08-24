"""Two-stage classification cache contract tests."""

from vbagent.agents.classification.question_classifier import (
    QuestionClassification,
    QuestionRoutingClassification,
)
from vbagent.pipeline import stages


def _cached_classification():
    return {
        "subject": "physics",
        "question_type": "mcq_sc",
        "has_diagram": True,
        "diagram_type": "mechanics",
        "diagram_category": "mechanics",
        "diagram_complexity": "moderate",
        "diagram_elements": ["block and pulley"],
        "suggested_tikz_agent": "mechanics",
        "has_option_diagrams": True,
    }


class _Cache:
    def __init__(
        self,
        *,
        classification_contract=None,
        routing_contract=None,
        include_classification=True,
        include_routing=True,
    ):
        self.contracts = {
            "classification": classification_contract,
            "routing": routing_contract,
        }
        self.values = {}
        if include_classification:
            self.values["classification"] = _cached_classification()
        if include_routing:
            self.values["routing"] = {
                "subject": "physics",
                "question_type": "mcq_sc",
            }
        self.saved = {}

    def has(self, problem_id, stage):
        return stage in self.values

    def get_stage_data(self, problem_id, stage):
        contract = self.contracts.get(stage)
        return {} if contract is None else {"contract_version": contract}

    def get(self, problem_id, stage):
        return self.values.get(stage)

    def set(self, problem_id, stage, data, stage_data=None):
        self.values[stage] = data
        self.saved[stage] = (data, stage_data)


def test_stale_full_cache_runs_generic_route_and_subject_analysis(monkeypatch):
    cache = _Cache(
        include_routing=False,
        classification_contract=5,
    )
    route = QuestionRoutingClassification(
        subject="mathematics",
        question_type="subjective",
    )
    fresh = QuestionClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
    )
    calls = []
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_route",
        lambda *args, **kwargs: calls.append("routing") or route,
    )

    def analyze(*args, **kwargs):
        calls.append("analysis")
        assert kwargs["routing"] is route
        return fresh

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        analyze,
    )

    result = stages.classify_question(
        "question.png",
        cache=cache,
        problem_id="problem_1",
    )

    assert result is fresh
    assert calls == ["routing", "analysis"]
    assert cache.saved["routing"][1] == {"contract_version": 1}
    assert cache.saved["classification"][1] == {"contract_version": 6}


def test_current_routing_is_reused_when_full_analysis_is_stale(monkeypatch):
    cache = _Cache(
        classification_contract=5,
        routing_contract=1,
    )
    fresh = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
    )
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_route",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("current routing should be reused")
        ),
    )

    def analyze(*args, **kwargs):
        assert kwargs["routing"].subject == "physics"
        return fresh

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        analyze,
    )

    result = stages.classify_question(
        "question.png",
        cache=cache,
        problem_id="problem_1",
    )

    assert result is fresh
    assert "routing" not in cache.saved
    assert cache.saved["classification"][1] == {"contract_version": 6}


def test_current_full_classification_cache_skips_both_api_stages(monkeypatch):
    cache = _Cache(
        classification_contract=6,
        routing_contract=1,
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("full cache hit should make no classification call")

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_route",
        unexpected_call,
    )
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        unexpected_call,
    )

    result = stages.classify_question(
        "question.png",
        cache=cache,
        problem_id="problem_1",
    )

    assert result.has_diagram is True
    assert result.has_option_diagrams is True
    assert cache.saved == {}


def test_pipeline_cache_stores_routing_as_independent_json_stage(tmp_path):
    from vbagent.cache import PipelineCache

    cache = PipelineCache(str(tmp_path))
    route = {
        "subject": "mathematics",
        "question_type": "subjective",
    }

    cache.set(
        "problem_1",
        "routing",
        route,
        stage_data={"contract_version": 1},
    )

    assert cache.has("problem_1", "routing")
    assert cache.get("problem_1", "routing") == route
    assert cache.get_stage_data("problem_1", "routing") == {
        "contract_version": 1,
    }
    assert "routing" in cache.get_cached_stages("problem_1")
