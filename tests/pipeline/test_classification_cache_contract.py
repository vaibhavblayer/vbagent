"""Classification cache contract tests."""

from vbagent.agents.classification.question_classifier import QuestionClassification
from vbagent.pipeline import stages


class _Cache:
    def __init__(self, contract_version=None):
        self.contract_version = contract_version
        self.saved = None

    def has(self, problem_id, stage):
        return True

    def get_stage_data(self, problem_id, stage):
        if self.contract_version is None:
            return {}
        return {"contract_version": self.contract_version}

    def get(self, problem_id, stage):
        return {
            "subject": "physics",
            "question_type": "mcq_sc",
            "has_diagram": True,
            "has_option_diagrams": True,
        }

    def set(self, problem_id, stage, data, stage_data=None):
        self.saved = (data, stage_data)


def test_stale_classification_cache_is_refreshed(monkeypatch):
    cache = _Cache()
    fresh = QuestionClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
        has_option_diagrams=True,
    )
    calls = []
    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        lambda *args, **kwargs: calls.append(args) or fresh,
    )

    result = stages.classify_question(
        "question.png", cache=cache, problem_id="problem_1"
    )

    assert result is fresh
    assert len(calls) == 1
    assert cache.saved[1] == {"contract_version": 3}


def test_current_classification_cache_is_reused(monkeypatch):
    cache = _Cache(contract_version=3)

    def unexpected_call(*args, **kwargs):
        raise AssertionError("current classification cache should be reused")

    monkeypatch.setattr(
        "vbagent.agents.classification.question_classifier.classify_question_image",
        unexpected_call,
    )

    result = stages.classify_question(
        "question.png", cache=cache, problem_id="problem_1"
    )

    assert result.has_diagram is True
    assert result.has_option_diagrams is True
    assert cache.saved is None
