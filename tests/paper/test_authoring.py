from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from vbagent.authoring.models import AuthoringRequest
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import AuthoredCandidate, CandidateStatus, GateResult
from vbagent.paper.models import ProblemEntry
from vbagent.paper.orchestrator import PaperOrchestrator


def _request(**updates):
    values = {
        "exam": "jee_main",
        "subject": "physics",
        "chapter": "kinematics",
        "topics": ["projectile motion"],
        "count": 1,
        "question_types": {"mcq_sc": 1},
        "difficulties": {5: 1},
    }
    values.update(updates)
    return AuthoringRequest(**values)


def _execution(plan, tmp_path):
    spec = plan.items[0]
    problem = (
        r"\item A projectile has range $R$."
        "\n"
        r"\begin{tasks}(2)\task $R$ \ans\task $2R$\task $R/2$\task $0$\end{tasks}"
    )
    final = problem + "\n" + r"\begin{solution}Independent solution.\end{solution}"
    candidate = AuthoredCandidate(
        spec=spec,
        status=CandidateStatus.ACCEPTED,
        problem_latex=problem,
        independent_solution_latex=r"\begin{solution}Independent solution.\end{solution}",
        final_latex=final,
        gates=[GateResult(gate="review", passed=True)],
    )
    return SimpleNamespace(
        plan=plan,
        stats={
            "status": "completed",
            "accepted": 1,
            "needs_review": 0,
            "rejected": 0,
            "failed": 0,
        },
        items=({"status": "accepted", "last_candidate_json": candidate.model_dump_json()},),
        run_dir=tmp_path / "authoring" / "runs" / plan.plan_id,
    )


def test_paper_imports_only_accepted_candidate_with_exact_provenance(tmp_path):
    request = _request()
    plan = AuthoringPlanner().plan(request)
    execution = _execution(plan, tmp_path)
    console = MagicMock()
    orch = PaperOrchestrator(base_dir=tmp_path, config=MagicMock(), console=console)

    with patch("vbagent.authoring.api.plan_authoring", return_value=plan), patch(
        "vbagent.authoring.api.execute_authoring", return_value=execution
    ):
        report = orch.author_problems(request)

    assert report.total_generated == 1
    assert report.authoring_run_id == plan.plan_id
    state = orch.manifest.load()
    assert state.exam == "jee_main"
    assert state.syllabus_version == plan.catalog_version
    assert state.syllabus_source_url == plan.catalog_source_url
    assert state.syllabus_verified_at == plan.catalog_verified_at
    assert state.syllabus_source_sha256 == plan.catalog_source_sha256
    assert state.authoring_run_ids == [plan.plan_id]
    entry = state.problems[0]
    assert entry.authoring_spec_id == plan.items[0].spec_id
    assert entry.chapter_id == plan.items[0].chapter_id
    assert entry.topic_id == plan.items[0].topic_id
    assert entry.syllabus_source_url == plan.items[0].syllabus_source_url
    assert entry.qa_status == "passed"
    assert entry.solution_status == "inline"
    assert (tmp_path / "scans" / entry.filename).read_text().count("Independent solution") == 1


def test_replaying_same_authoring_run_does_not_duplicate_paper_entries(tmp_path):
    request = _request()
    plan = AuthoringPlanner().plan(request)
    execution = _execution(plan, tmp_path)
    orch = PaperOrchestrator(base_dir=tmp_path, config=MagicMock(), console=MagicMock())

    with patch("vbagent.authoring.api.plan_authoring", return_value=plan), patch(
        "vbagent.authoring.api.execute_authoring", return_value=execution
    ):
        assert orch.author_problems(request).total_generated == 1
        assert orch.author_problems(request).total_generated == 0

    assert len(orch.manifest.load().problems) == 1


def test_paper_refuses_syllabus_snapshot_mixing_before_api_execution(tmp_path):
    request = _request()
    plan = AuthoringPlanner().plan(request)
    orch = PaperOrchestrator(base_dir=tmp_path, config=MagicMock(), console=MagicMock())
    state = orch.manifest.load()
    state.exam = "jee_main"
    state.subject = "physics"
    state.syllabus_source_sha256 = "different-snapshot"
    state.problems.append(
        ProblemEntry(
            serial=1,
            filename="Problem_1.tex",
            subject="physics",
            topic="Projectile Motion",
        )
    )
    orch.manifest.save(state)

    with patch("vbagent.authoring.api.plan_authoring", return_value=plan), patch(
        "vbagent.authoring.api.execute_authoring"
    ) as execute:
        with pytest.raises(ValueError, match="different syllabus snapshot"):
            orch.author_problems(request)

    execute.assert_not_called()
