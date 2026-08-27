import json

import pytest

from vbagent.authoring.application import (
    AuthoringApplication,
    AuthoringIntent,
    WorkerLaunch,
)
from vbagent.authoring.paths import generated_output_root, generated_problem_path
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.service import RunLeaseError
from vbagent.authoring.store import AuthoringStore


def _intent(*, count=3):
    return AuthoringIntent(
        exam="jee_main",
        subject="physics",
        chapter="kinematics",
        topics=["projectile motion"],
        count=count,
        question_types={"mcq_sc": 1},
        difficulties={5: 1},
        seed=17,
    )


def test_application_previews_natural_language_mathematics_scope(tmp_path):
    app = AuthoringApplication(tmp_path)
    preview = app.preview(
        AuthoringIntent(
            exam="jee_main",
            subject="mathematics",
            chapter="limit continuity and differentiability",
            topics=["greatest integer function"],
            required_concepts=["greatest integer function"],
            question_types={"mcq_sc": 1},
        )
    )

    assert preview.request.subject == "mathematics"
    assert preview.items[0].topic == (
        "Real-valued functions, algebra of functions and graphs of simple functions"
    )
    assert preview.items[0].required_concepts == ("greatest integer function",)
    assert preview.allowed_question_types[0].value == "mcq_sc"
    assert preview.catalog_official_source_sha256 == (
        "7cad9da2a12065444828f744bd9f1a93a2dd0d9bd54c32a6d92d94a769e4f905"
    )
    assert preview.items[0].syllabus_official_source_sha256 == (
        preview.catalog_official_source_sha256
    )


def test_application_searches_catalog_without_returning_full_tree(tmp_path):
    result = AuthoringApplication(tmp_path).search_catalog(
        "jee_main",
        "mathematics",
        "greatest integer function",
    )

    assert result.total == 1
    assert result.truncated is False
    assert result.allowed_question_types == ["mcq_sc", "integer"]
    assert result.matches[0].kind == "topic"
    assert result.matches[0].chapter == "LIMIT, CONTINUITY AND DIFFERENTIABILITY"
    assert "chapters" not in result.model_dump()


def test_application_progressively_discloses_chapters_then_selected_topics(tmp_path):
    app = AuthoringApplication(tmp_path)

    inspection = app.inspect_catalog("jee_main", "mathematics")
    assert len(inspection.chapters) == 14
    assert inspection.chapters[6].topic_count == 12
    assert all("topics" not in chapter.model_dump() for chapter in inspection.chapters)

    first = app.list_catalog_topics(
        "jee_main",
        "mathematics",
        "limit continuity and differentiability",
        limit=3,
    )
    second = app.list_catalog_topics(
        "jee_main",
        "mathematics",
        first.chapter_id,
        offset=first.next_offset,
        limit=3,
    )

    assert first.total == 12
    assert len(first.topics) == 3
    assert first.next_offset == 3
    assert second.offset == 3
    assert len(second.topics) == 3


def test_application_plans_paginates_and_dispatches_only_after_confirmation(tmp_path):
    launches = []

    def launcher(output_root, run_id, concurrency, resume, dispatch_token):
        launches.append((output_root, run_id, concurrency, resume, dispatch_token))
        return WorkerLaunch(
            pid=4321,
            log_path=str(output_root / "runs" / run_id / "worker.log"),
        )

    app = AuthoringApplication(tmp_path, launcher=launcher)
    planned = app.plan(_intent(), max_attempts=2, concurrency=3)

    assert planned.created is True
    assert planned.total_items == 3
    assert planned.status == "pending"
    assert planned.current_stage == "awaiting_start"
    assert planned.chapters == ["KINEMATICS"]
    assert planned.topics == ["Motion in a plane, Projectile Motion"]
    assert planned.generated_output_dir == str(
        generated_output_root(tmp_path)
    )
    assert planned.requires_confirmation is True
    assert planned.estimated_agent_calls > 0
    assert app.plan(_intent(), max_attempts=2, concurrency=3).created is False

    first_page = app.list_items(planned.run_id, limit=2)
    assert first_page.total == 3
    assert len(first_page.items) == 2
    assert first_page.next_offset == 2
    second_page = app.list_items(planned.run_id, offset=2, limit=2)
    assert len(second_page.items) == 1
    assert second_page.next_offset is None

    with pytest.raises(ValueError, match="explicit user authorization"):
        app.start(planned.run_id, confirmed=False)
    assert launches == []

    started = app.start(planned.run_id, confirmed=True, concurrency=1)
    assert started.dispatched is True
    assert started.worker.pid == 4321
    assert len(launches) == 1
    assert launches[0][:4] == (tmp_path.resolve(), planned.run_id, 1, False)
    assert launches[0][4]

    reconnected = AuthoringApplication(tmp_path, launcher=launcher)
    durable_status = reconnected.status(planned.run_id)
    assert durable_status.chapters == ["KINEMATICS"]
    assert durable_status.topics == ["Motion in a plane, Projectile Motion"]
    assert durable_status.generated_output_dir == planned.generated_output_dir
    assert durable_status.current_stage == "launching_worker"
    assert durable_status.active_stages == []
    assert durable_status.stage_counts == {}
    assert durable_status.worker.pid == 4321
    duplicate = reconnected.start(planned.run_id, confirmed=True, concurrency=1)
    assert duplicate.dispatched is False
    assert len(launches) == 1
    with pytest.raises(RunLeaseError, match="active detached worker"):
        reconnected.execute_foreground(planned.run_id)


def test_application_cancel_and_resume_are_durable_and_explicit(tmp_path):
    launches = []

    def launcher(output_root, run_id, concurrency, resume, dispatch_token):
        launches.append((run_id, concurrency, resume, dispatch_token))
        return WorkerLaunch(
            pid=99,
            log_path=str(output_root / "worker.log"),
        )

    app = AuthoringApplication(tmp_path, launcher=launcher)
    planned = app.plan(_intent(count=1))

    cancelled = app.cancel(planned.run_id, "operator stopped the run")
    assert cancelled.status.status == "cancelled"
    assert cancelled.status.stats["cancelled"] == 1

    with pytest.raises(ValueError, match="explicit user authorization"):
        app.resume(planned.run_id, confirmed=False)
    resumed = app.resume(planned.run_id, confirmed=True, concurrency=4)
    assert resumed.dispatched is True
    assert len(launches) == 1
    assert launches[0][:3] == (planned.run_id, 4, True)


def test_application_requires_readable_artifact_status_and_exposes_evidence(tmp_path):
    app = AuthoringApplication(tmp_path)
    planned = app.plan(_intent(count=1), max_attempts=1)
    page = app.list_items(planned.run_id)
    spec_id = page.items[0].spec_id

    with pytest.raises(ValueError, match="readable artifacts require"):
        app.read_final_artifact(planned.run_id, spec_id)

    with AuthoringStore(tmp_path) as store:
        claimed = store.claim_next(planned.run_id, "test-worker")
        problem = (
            r"\item A projectile is launched horizontally. Its range is"
            "\n"
            r"\begin{tasks}(2)\task $R$ \ans\task $2R$\task $R/2$\task $0$\end{tasks}"
        )
        final = problem + "\n" + r"\begin{solution}The range is $R$.\end{solution}"
        candidate = AuthoredCandidate(
            spec=claimed.spec,
            status=CandidateStatus.ACCEPTED,
            problem_latex=problem,
            draft_solution_latex=r"\begin{solution}The range is $R$.\end{solution}",
            independent_solution_latex=(
                r"\begin{solution}The range is $R$.\end{solution}"
            ),
            final_latex=final,
            gates=[
                GateResult(gate=gate, passed=True)
                for gate in REQUIRED_ACCEPTANCE_GATES
            ],
        )
        artifact_dir, digest = store.write_candidate_artifacts(claimed, candidate)
        store.record_candidate(
            claimed,
            candidate,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
        )

    assert app.read_final_artifact(planned.run_id, spec_id) == final + "\n"
    artifact = app.get_final_artifact(planned.run_id, spec_id)
    assert artifact.mime_type == "text/x-tex"
    assert artifact.content == final + "\n"
    expected_path = generated_problem_path(tmp_path, 1)
    assert artifact.path == str(expected_path)
    assert expected_path.read_text(encoding="utf-8") == final + "\n"
    accepted_item = app.list_items(planned.run_id, status="accepted").items[0]
    assert accepted_item.saved_path == str(expected_path)
    status = app.status(planned.run_id)
    assert status.generated_manifest_path is not None
    evidence = json.loads(app.read_item_evidence(planned.run_id, spec_id))
    assert evidence["status"] == "accepted"
    assert evidence["attempts"][0]["candidate_status"] == "accepted"
    assert [gate["gate"] for gate in evidence["attempts"][0]["gates"]] == list(
        REQUIRED_ACCEPTANCE_GATES
    )


def test_application_pages_worker_log_by_byte_offset(tmp_path):
    app = AuthoringApplication(tmp_path)
    planned = app.plan(_intent(count=1))
    log_path = tmp_path / "runs" / planned.run_id / "worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes("agent input → output\n".encode())

    first = app.read_worker_log(planned.run_id, offset=0, limit_bytes=8)
    second = app.read_worker_log(
        planned.run_id,
        offset=first.next_offset,
        limit_bytes=100,
    )

    assert first.offset == 0
    assert first.eof is False
    assert second.eof is True
    assert (first.content + second.content).startswith("agent in")
    assert second.next_offset == log_path.stat().st_size


@pytest.mark.parametrize("limit_bytes", [1, 2, 3, 5, 9])
def test_worker_log_paging_preserves_unicode_at_byte_boundaries(tmp_path, limit_bytes):
    app = AuthoringApplication(tmp_path)
    planned = app.plan(_intent(count=1))
    path = tmp_path / "runs" / planned.run_id / "worker.log"
    original = "{\"input\": \"range → ℝ, 重试\"}\n"
    path.write_text(original, encoding="utf-8")
    offset = 0
    chunks = []
    for _ in range(100):
        page = app.read_worker_log(planned.run_id, offset=offset, limit_bytes=limit_bytes)
        assert page.next_offset > offset
        assert page.next_offset - offset <= limit_bytes + 3
        chunks.append(page.content)
        offset = page.next_offset
        if page.eof:
            break
    assert "".join(chunks) == original


def test_detached_worker_launcher_requests_jsonl_agent_output(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from vbagent.authoring.application import SubprocessWorkerLauncher

    captured = {}

    def fake_popen(command, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(pid=1234)

    monkeypatch.setattr("vbagent.authoring.application.subprocess.Popen", fake_popen)
    result = SubprocessWorkerLauncher()(tmp_path, "example-run", 2, False, "token")
    assert result.pid == 1234
    assert captured["env"]["VBAGENT_AGENT_IO_FORMAT"] == "jsonl"
