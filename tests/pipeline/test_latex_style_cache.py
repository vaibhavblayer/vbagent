"""Old teaching/graph output must not bypass a changed style contract."""

from types import SimpleNamespace

import pytest

from vbagent.agents.orchestration.problem_orchestrator import ProblemOrchestrator
from vbagent.cache import PipelineCache
from vbagent.prompts.latex_style import LATEX_STYLE_CONTRACT_VERSION


@pytest.mark.parametrize("stage", ("scan", "tikz", "options"))
@pytest.mark.parametrize("version", (None, 0, LATEX_STYLE_CONTRACT_VERSION))
def test_scan_and_diagram_cache_checks_style_as_well_as_classification(stage, version):
    data = {"classification_fingerprint": "same"}
    if version is not None:
        data["latex_style_contract_version"] = version
    cache = SimpleNamespace(get_stage_data=lambda *args: data)

    assert ProblemOrchestrator._cache_matches_classification(
        cache, "q", stage, "same"
    ) is (version == LATEX_STYLE_CONTRACT_VERSION)


@pytest.mark.parametrize("version", (None, 0))
def test_old_solution_style_regenerates_even_with_current_answer_and_classification(
    tmp_path, monkeypatch, version
):
    import vbagent.agents.orchestration.solution_orchestrator as module
    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated

    cache = PipelineCache(str(tmp_path))
    data = {
        "classification_fingerprint": "same",
        "answer_type": "subjective",
        "final_answer_latex": r"$[1,\infty)$",
    }
    if version is not None:
        data["latex_style_contract_version"] = version
    cache.set("q", "solution", "Old verbose output", stage_data=data)
    fresh = SolutionResult(
        latex="Fresh explanation and graph", final_answer_latex=r"$[1,\infty)$"
    )
    monkeypatch.setattr(
        module,
        "create_solution_orchestrator",
        lambda **kwargs: SimpleNamespace(run=lambda **kwargs: fresh),
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=PrimaryClassification(
            subject="mathematics", question_type="subjective", has_diagram=False
        ),
        problem_latex="Question",
        cache=cache,
        problem_id="q",
        return_result=True,
        classification_fingerprint="same",
    )

    assert result.latex == fresh.latex
    assert (
        cache.get_stage_data("q", "solution")["latex_style_contract_version"]
        == LATEX_STYLE_CONTRACT_VERSION
    )


def test_alternate_cache_regenerates_old_style_and_reuses_current_style(
    tmp_path, monkeypatch
):
    from vbagent.agents.content_generation import alternate
    from vbagent.pipeline.stages import generate_alternate_stage

    cache = PipelineCache(str(tmp_path))
    cache.set("q", "alternate", "Old explanation")
    calls = []

    def generate(*args, **kwargs):
        calls.append(True)
        return "New explanation"

    monkeypatch.setattr(alternate, "generate_alternate", generate)
    for _ in range(2):
        assert generate_alternate_stage(
            "Q", "S", None, cache=cache, problem_id="q"
        ) == ["New explanation"]
    assert len(calls) == 1


def test_generation_fingerprint_depends_on_style_version(monkeypatch):
    from vbagent.pipeline import generate

    args = (
        ["idea"],
        ["concept"],
        "functions",
        "easy",
        "subjective",
        "mathematics",
        True,
        True,
    )
    current = generate._idea_hash(*args)
    monkeypatch.setattr(
        generate, "LATEX_STYLE_CONTRACT_VERSION", LATEX_STYLE_CONTRACT_VERSION + 1
    )
    assert generate._idea_hash(*args) != current
