"""Regression tests for conditional alternate-solution generation."""

from vbagent.pipeline.runner import _should_generate_alternate


def test_alternate_gate_requires_explicit_request():
    assert _should_generate_alternate(False, True, True) is False


def test_alternate_gate_skips_when_solution_agent_recommends_false():
    assert _should_generate_alternate(True, True, False) is False


def test_alternate_gate_generates_when_solution_agent_recommends_true():
    assert _should_generate_alternate(True, True, True) is True


def test_alternate_gate_preserves_legacy_paths_without_solution_decision():
    assert _should_generate_alternate(True, False, False) is True


def test_solution_cache_can_store_alternate_decision_metadata(tmp_path):
    from vbagent.cache import PipelineCache

    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        r"\begin{solution}x=1\end{solution}",
        stage_data={
            "alternate_solution_recommended": True,
            "alternate_solution_hint": "Use conservation of energy.",
        },
    )

    assert cache.get_stage_data("problem_1", "solution") == {
        "alternate_solution_recommended": True,
        "alternate_solution_hint": "Use conservation of energy.",
    }


def test_cached_solution_restores_subjective_final_answer(tmp_path):
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated

    cache = PipelineCache(str(tmp_path))
    final_answer = r"$x_{\mathrm{eq}}=\frac{b}{2a}$, stable."
    cached_latex = (
        r"\item Find equilibrium."
        "\n\\begin{solution}Work.\\end{solution}"
        f"\n\\begin{{finalanswer}}\n{final_answer}\n\\end{{finalanswer}}"
    )
    cache.set(
        "problem_1",
        "solution",
        cached_latex,
        stage_data={
            "answer_type": "subjective",
            "answer_value": None,
            "final_answer_latex": final_answer,
            "alternate_solution_recommended": False,
            "alternate_solution_hint": None,
        },
    )
    primary = PrimaryClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
        confidence=1.0,
        classified_from="latex",
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == cached_latex
    assert result.answer_type == "subjective"
    assert result.final_answer_latex == final_answer


def test_solution_cache_reuses_matching_classification_fingerprint(
    tmp_path, monkeypatch
):
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    cache = PipelineCache(str(tmp_path))
    cached_latex = r"\item Q.\begin{solution}Cached.\end{solution}"
    cache.set(
        "problem_1",
        "solution",
        cached_latex,
        stage_data={
            "answer_type": "mcq",
            "answer_value": "a",
            "classification_fingerprint": "same-classification",
        },
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("matching solution cache should be reused")
        ),
    )
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        cache=cache,
        problem_id="problem_1",
        return_result=True,
        classification_fingerprint="same-classification",
    )

    assert result.latex == cached_latex
    assert result.answer_value == "a"


def test_solution_cache_refreshes_for_changed_classification(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        r"\item Old.\begin{solution}Old.\end{solution}",
        stage_data={
            "answer_type": "mcq",
            "answer_value": "a",
            "classification_fingerprint": "old-classification",
        },
    )
    new_latex = r"\item New.\begin{solution}New.\end{solution}"
    fake_orchestrator = SimpleNamespace(
        run=lambda **kwargs: SolutionResult(
            latex=new_latex,
            answer_type="mcq",
            answer_value="b",
            metadata={},
        )
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda console=None: fake_orchestrator,
    )
    primary = PrimaryClassification(
        subject="physics",
        question_type="mcq_sc",
        has_diagram=False,
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=r"\item New.",
        cache=cache,
        problem_id="problem_1",
        return_result=True,
        classification_fingerprint="new-classification",
    )

    assert result.latex == new_latex
    assert cache.get_stage_data("problem_1", "solution")[
        "classification_fingerprint"
    ] == "new-classification"


def test_stale_subjective_solution_cache_is_regenerated(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        r"\item Find x.\begin{solution}Old solution.\end{solution}",
        stage_data={
            "alternate_solution_recommended": False,
            "alternate_solution_hint": None,
        },
    )
    new_answer = r"$x=2\,\mathrm{m}$."
    new_latex = (
        r"\item Find x.\begin{solution}New solution.\end{solution}"
        f"\\begin{{finalanswer}}{new_answer}\\end{{finalanswer}}"
    )
    fake_orchestrator = SimpleNamespace(
        run=lambda **kwargs: SolutionResult(
            latex=new_latex,
            answer_type="subjective",
            final_answer_latex=new_answer,
            metadata={},
        )
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda console=None: fake_orchestrator,
    )
    primary = PrimaryClassification(
        subject="physics",
        question_type="subjective",
        has_diagram=False,
        confidence=1.0,
        classified_from="latex",
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=r"\item Find x.",
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == new_latex
    assert result.final_answer_latex == new_answer
    assert cache.get_stage_data("problem_1", "solution")["final_answer_latex"] == new_answer


def test_multipart_subjective_v2_cache_is_regenerated(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    problem = (
        r"\item Find each domain."
        "\n\\begin{enumerate}\n"
        r"\item $f(x)$\item $g(x)$"
        "\n\\end{enumerate}"
    )
    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        (
            problem
            + r"\begin{solution}\begin{enumerate}"
            + r"\item Cached first.\item Cached second."
            + r"\end{enumerate}\end{solution}"
        ),
        stage_data={
            "answer_type": "subjective",
            "final_answer_latex": (
                r"\begin{enumerate}\item Cached first.\item Cached second."
                r"\end{enumerate}"
            ),
            "subjective_multipart_solution_contract_version": 2,
        },
    )
    refreshed_latex = (
        problem
        + r"\begin{solution}\begin{enumerate}"
        + r"\item First.\item Second."
        + r"\end{enumerate}\end{solution}"
    )
    refreshed_answer = (
        r"\begin{enumerate}\item First.\item Second.\end{enumerate}"
    )
    refreshed_latex += (
        r"\begin{finalanswer}"
        + refreshed_answer
        + r"\end{finalanswer}"
    )
    fake_orchestrator = SimpleNamespace(
        run=lambda **kwargs: SolutionResult(
            latex=refreshed_latex,
            answer_type="subjective",
            final_answer_latex=refreshed_answer,
            metadata={},
        )
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda console=None: fake_orchestrator,
    )
    primary = PrimaryClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=problem,
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == refreshed_latex
    assert cache.get_stage_data("problem_1", "solution")[
        "subjective_multipart_solution_contract_version"
    ] == 3


def test_compliant_multipart_subjective_solution_is_reused_from_cache(
    tmp_path, monkeypatch
):
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    problem = (
        r"\item Find each domain."
        "\n\\begin{enumerate}\n"
        r"\item $f(x)$\item $g(x)$"
        "\n\\end{enumerate}"
    )
    cached_latex = (
        problem
        + r"\begin{solution}\begin{enumerate}"
        + r"\item First.\item Second."
        + r"\end{enumerate}\end{solution}"
    )
    cached_answer = (
        r"\begin{enumerate}\item First.\item Second.\end{enumerate}"
    )
    cached_latex += (
        r"\begin{finalanswer}"
        + cached_answer
        + r"\end{finalanswer}"
    )
    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        cached_latex,
        stage_data={
            "answer_type": "subjective",
            "final_answer_latex": cached_answer,
            "subjective_multipart_solution_contract_version": 3,
        },
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("compliant multipart cache should be reused")
        ),
    )
    primary = PrimaryClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=problem,
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == cached_latex


def test_malformed_v3_multipart_final_answer_cache_is_regenerated(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    problem = (
        r"\item Answer both."
        r"\begin{enumerate}\item First.\item Second.\end{enumerate}"
    )
    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        problem + r"\begin{solution}Cached.\end{solution}",
        stage_data={
            "answer_type": "subjective",
            "final_answer_latex": "1. First; 2. Second.",
            "subjective_multipart_solution_contract_version": 3,
        },
    )
    answer = r"\begin{enumerate}\item First.\item Second.\end{enumerate}"
    refreshed = problem + r"\begin{solution}Refreshed.\end{solution}"
    fake_orchestrator = SimpleNamespace(
        run=lambda **kwargs: SolutionResult(
            latex=refreshed,
            answer_type="subjective",
            final_answer_latex=answer,
            metadata={},
        )
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda console=None: fake_orchestrator,
    )
    primary = PrimaryClassification(
        subject="mathematics",
        question_type="subjective",
        has_diagram=False,
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=problem,
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == refreshed
    assert cache.get_stage_data("problem_1", "solution")[
        "final_answer_latex"
    ] == answer


def test_stale_match_solution_cache_is_regenerated_for_option_repair(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from vbagent.agents.orchestration.solution_orchestrator import SolutionResult
    from vbagent.cache import PipelineCache
    from vbagent.models.classification import PrimaryClassification
    from vbagent.pipeline.stages import generate_solution_orchestrated
    import vbagent.agents.orchestration.solution_orchestrator as orchestrator_module

    cache = PipelineCache(str(tmp_path))
    cache.set(
        "problem_1",
        "solution",
        r"\item Old match.\begin{solution}Old solution.\end{solution}",
        stage_data={"answer_type": "mcq", "answer_value": "a"},
    )
    new_latex = r"\item Repaired match.\begin{solution}New solution.\end{solution}"
    fake_orchestrator = SimpleNamespace(
        run=lambda **kwargs: SolutionResult(
            latex=new_latex,
            answer_type="mcq",
            answer_value="d",
            metadata={"match_option_repaired": True},
        )
    )
    monkeypatch.setattr(
        orchestrator_module,
        "create_solution_orchestrator",
        lambda console=None: fake_orchestrator,
    )
    primary = PrimaryClassification(
        subject="physics",
        question_type="match",
        has_diagram=False,
        confidence=1.0,
        classified_from="latex",
    )

    result = generate_solution_orchestrated(
        image_path="unused.png",
        primary=primary,
        problem_latex=r"\item Match.",
        cache=cache,
        problem_id="problem_1",
        return_result=True,
    )

    assert result.latex == new_latex
    stage_data = cache.get_stage_data("problem_1", "solution")
    assert stage_data["match_solution_repair_contract_version"] == 1
    assert stage_data["match_option_repaired"] is True
