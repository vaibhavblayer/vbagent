import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vbagent.authoring.models import AuthoringRequest
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.store import AuthoringStore, ItemStatus, RunStatus


def _plan(count=2, *, human_review=False):
    return AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=count,
            question_types={"mcq_sc": 1},
            difficulties={5: 1},
            acceptance={"human_review_required": human_review},
            seed=21,
        )
    )


def _candidate(spec, status=CandidateStatus.ACCEPTED, failed_gate=None):
    if status in {CandidateStatus.ACCEPTED, CandidateStatus.NEEDS_REVIEW}:
        gate_names = list(REQUIRED_ACCEPTANCE_GATES)
        if spec.diagram_policy.value == "required":
            gate_names.insert(2, "problem_diagram")
        gates = [GateResult(gate=gate, passed=True) for gate in gate_names]
    else:
        gates = [GateResult(gate="draft", passed=True)]
    if failed_gate and status not in {CandidateStatus.ACCEPTED, CandidateStatus.NEEDS_REVIEW}:
        gates.append(GateResult(gate=failed_gate, passed=False, summary="must retry"))
    problem = (
        r"\item A projectile is launched horizontally. Its range is"
        "\n"
        r"\begin{tasks}(2)\task $R$ \ans\task $2R$\task $R/2$\task $0$\end{tasks}"
    )
    return AuthoredCandidate(
        spec=spec,
        status=status,
        problem_latex=problem,
        draft_solution_latex=r"\begin{solution}The range is $R$.\end{solution}",
        independent_solution_latex=r"\begin{solution}The range is $R$.\end{solution}",
        final_latex=problem + "\n" + r"\begin{solution}The range is $R$.\end{solution}",
        gates=gates,
        provenance={
            "usage": {
                "totals": {
                    "requests": 2,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "duration_seconds": 1.5,
                }
            }
        },
    )


def test_create_run_is_idempotent_and_plan_bound(tmp_path):
    plan = _plan()
    output = tmp_path / "output"
    with AuthoringStore(tmp_path) as store:
        assert store.create_run(plan, output, max_attempts=2, concurrency=2) == plan.plan_id
        assert store.create_run(plan, output, max_attempts=2, concurrency=2) == plan.plan_id
        assert store.stats(plan.plan_id)["total"] == 2
        assert store.stats(plan.plan_id)["pending"] == 2
        assert (output / "runs" / plan.plan_id / "run.json").exists()
        stored_payload = store.get_run(plan.plan_id)["plan_json"]
        assert '"items"' not in stored_payload
        assert store.load_plan(plan.plan_id) == plan
        assert store.load_request(plan.plan_id) == plan.request
        assert store.plan_metadata(plan.plan_id)["plan_id"] == plan.plan_id
        assert len(store.list_item_results(plan.plan_id)) == 2
        assert "spec_json" not in store.list_item_results(plan.plan_id)[0]

        with pytest.raises(ValueError, match="different output"):
            store.create_run(plan, tmp_path / "elsewhere")


def test_legacy_full_plan_rows_remain_idempotent_and_readable(tmp_path):
    plan = _plan(count=1)
    output = tmp_path / "output"
    legacy_json = json.dumps(
        plan.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    legacy_digest = hashlib.sha256(legacy_json.encode()).hexdigest()

    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, output)
        store.conn.execute(
            """
            UPDATE authoring_runs SET plan_json = ?, plan_sha256 = ?
            WHERE run_id = ?
            """,
            (legacy_json, legacy_digest, plan.plan_id),
        )
        store.conn.commit()

        assert store.create_run(plan, output) == plan.plan_id
        assert store.load_plan(plan.plan_id) == plan
        assert store.plan_metadata(plan.plan_id)["plan_id"] == plan.plan_id


def test_rejected_attempt_retries_with_evidence_then_accepts(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=2)
        claimed = store.claim_next(plan.plan_id, "worker")
        rejected = _candidate(claimed.spec, CandidateStatus.REJECTED, "spec_alignment")
        artifact_dir, digest = store.write_candidate_artifacts(claimed, rejected)

        status = store.record_candidate(
            claimed,
            rejected,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
            retry_base_seconds=0,
        )

        assert status is ItemStatus.PENDING
        retry = store.claim_next(plan.plan_id, "worker")
        assert retry.attempt == 2
        assert "spec_alignment" in retry.retry_reason

        accepted = _candidate(retry.spec)
        artifact_dir, digest = store.write_candidate_artifacts(retry, accepted)
        assert store.record_candidate(
            retry,
            accepted,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
            retry_base_seconds=0,
        ) is ItemStatus.ACCEPTED

        stats = store.stats(plan.plan_id)
        assert stats["status"] == RunStatus.COMPLETED.value
        assert stats["accepted"] == 1
        assert stats["attempts"] == 2
        assert store.accepted_coverage(plan.plan_id)["topic"] == {retry.spec.topic_id: 1}
        assert store.usage_summary(plan.plan_id)["requests"] == 4
        assert store.failure_reasons(plan.plan_id) == {"spec_alignment": 1}


def test_atomic_artifacts_preserve_every_attempt_and_promote_acceptance(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=1)
        claimed = store.claim_next(plan.plan_id, "worker")
        accepted = _candidate(claimed.spec)
        artifact_dir, digest = store.write_candidate_artifacts(claimed, accepted)

        assert (artifact_dir / "candidate.json").exists()
        assert (artifact_dir / "final.tex").exists()
        assert len(digest) == 64
        assert not (claimed.output_dir / "problem.tex").exists()
        store.record_candidate(
            claimed,
            accepted,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
        )
        assert (claimed.output_dir / "problem.tex").exists()
        accepted_copy = (
            claimed.output_dir.parent.parent
            / "accepted"
            / f"problem_{claimed.spec.ordinal:06d}_{claimed.spec.spec_id[:12]}.tex"
        )
        assert accepted_copy.exists()


def test_failed_ledger_commit_does_not_leave_promoted_acceptance(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=1)
        claimed = store.claim_next(plan.plan_id, "worker")
        accepted = _candidate(claimed.spec)
        artifact_dir, digest = store.write_candidate_artifacts(claimed, accepted)
        store.conn.execute(
            """
            CREATE TRIGGER reject_accepted_update
            BEFORE UPDATE OF status ON authoring_items
            WHEN NEW.status = 'accepted'
            BEGIN
                SELECT RAISE(ABORT, 'forced ledger failure');
            END
            """
        )
        store.conn.commit()

        with pytest.raises(Exception, match="forced ledger failure"):
            store.record_candidate(
                claimed,
                accepted,
                artifact_dir=artifact_dir,
                artifact_sha256=digest,
            )

        accepted_copy = (
            claimed.output_dir.parent.parent
            / "accepted"
            / f"problem_{claimed.spec.ordinal:06d}_{claimed.spec.spec_id[:12]}.tex"
        )
        assert not (claimed.output_dir / "problem.tex").exists()
        assert not accepted_copy.exists()
        attempts = store.conn.execute(
            "SELECT COUNT(*) FROM authoring_attempts WHERE spec_id = ?",
            (claimed.spec.spec_id,),
        ).fetchone()[0]
        assert attempts == 0


def test_store_rejects_passing_status_without_complete_gate_evidence(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=1)
        claimed = store.claim_next(plan.plan_id, "worker")
        accepted = _candidate(claimed.spec)
        accepted.gates.pop()
        artifact_dir, digest = store.write_candidate_artifacts(claimed, accepted)

        with pytest.raises(ValueError, match="incomplete acceptance evidence"):
            store.record_candidate(
                claimed,
                accepted,
                artifact_dir=artifact_dir,
                artifact_sha256=digest,
            )

        assert not (claimed.output_dir / "problem.tex").exists()


def test_overlap_lease_and_expired_item_lease_are_safe(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=2)
        assert store.acquire_run_lease(plan.plan_id, "owner-a")
        assert not store.acquire_run_lease(plan.plan_id, "owner-b")
        store.release_run_lease(plan.plan_id, "owner-a")
        assert store.acquire_run_lease(plan.plan_id, "owner-b")

        first = store.claim_next(plan.plan_id, "dead-worker", lease_seconds=60)
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        store.conn.execute(
            "UPDATE authoring_items SET lease_expires_at = ? WHERE spec_id = ?",
            (expired, first.spec.spec_id),
        )
        store.conn.commit()
        recovered = store.claim_next(plan.plan_id, "new-worker")
        assert recovered.spec.spec_id == first.spec.spec_id
        assert recovered.attempt == 2


def test_item_lease_renewal_and_infrastructure_abandon_are_owner_bound(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=2)
        claimed = store.claim_next(plan.plan_id, "worker-a", lease_seconds=60)

        assert store.renew_item_lease(
            claimed.spec.spec_id,
            "worker-a",
            claimed.attempt,
            lease_seconds=120,
        )
        assert not store.renew_item_lease(
            claimed.spec.spec_id,
            "worker-b",
            claimed.attempt,
        )
        assert not store.renew_item_lease(
            claimed.spec.spec_id,
            "worker-a",
            claimed.attempt + 1,
        )
        assert store.abandon_item(claimed, "artifact filesystem unavailable")
        item = store.get_item(claimed.spec.spec_id)
        assert item["status"] == ItemStatus.PENDING.value
        assert item["lease_owner"] is None
        assert "filesystem" in item["retry_reason"]


def test_final_attempt_abandon_is_terminal(tmp_path):
    plan = _plan(count=1)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=1)
        claimed = store.claim_next(plan.plan_id, "worker-a")

        assert store.abandon_item(claimed, "disk full")
        item = store.get_item(claimed.spec.spec_id)
        assert item["status"] == ItemStatus.FAILED.value
        assert item["completed_at"]


def test_cancel_and_resume_only_unfinished_items(tmp_path):
    plan = _plan(count=2)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=2)
        store.request_cancel(plan.plan_id, "stop")
        stats = store.stats(plan.plan_id)
        assert stats["status"] == RunStatus.CANCELLED.value
        assert stats["cancelled"] == 2

        assert store.resume_run(plan.plan_id) == 2
        assert store.stats(plan.plan_id)["pending"] == 2


def test_human_review_is_not_accepted_coverage_until_approved(tmp_path):
    plan = _plan(count=1, human_review=True)
    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=1)
        claimed = store.claim_next(plan.plan_id, "worker")
        candidate = _candidate(claimed.spec, CandidateStatus.NEEDS_REVIEW)
        artifact_dir, digest = store.write_candidate_artifacts(claimed, candidate)
        store.record_candidate(
            claimed,
            candidate,
            artifact_dir=artifact_dir,
            artifact_sha256=digest,
        )

        assert store.accepted_coverage(plan.plan_id)["topic"] == {}
        pending_path = (
            claimed.output_dir.parent.parent
            / "needs_review"
            / f"problem_{claimed.spec.ordinal:06d}_{claimed.spec.spec_id[:12]}.tex"
        )
        assert pending_path.exists()
        store.review_item(plan.plan_id, claimed.spec.spec_id, approve=True, reason="checked")
        assert store.accepted_coverage(plan.plan_id)["topic"] == {claimed.spec.topic_id: 1}
        assert not pending_path.exists()
        accepted_path = pending_path.parent.parent / "accepted" / pending_path.name
        assert accepted_path.exists()
        reviewed = store.get_item(claimed.spec.spec_id)
        assert '"status": "accepted"' in reviewed["last_candidate_json"]
        review = store.conn.execute(
            "SELECT decision, reason FROM authoring_reviews WHERE spec_id = ?",
            (claimed.spec.spec_id,),
        ).fetchone()
        assert tuple(review) == ("approved", "checked")


def test_human_approval_rechecks_novelty_against_other_approved_items(tmp_path):
    first_plan = _plan(count=1, human_review=True)
    second_plan = AuthoringPlanner().plan(
        first_plan.request.model_copy(update={"seed": 22})
    )
    with AuthoringStore(tmp_path) as store:
        for plan in (first_plan, second_plan):
            store.create_run(plan, tmp_path / "out", max_attempts=1)
            claimed = store.claim_next(plan.plan_id, "worker")
            candidate = _candidate(claimed.spec, CandidateStatus.NEEDS_REVIEW)
            artifact_dir, digest = store.write_candidate_artifacts(claimed, candidate)
            store.record_candidate(
                claimed,
                candidate,
                artifact_dir=artifact_dir,
                artifact_sha256=digest,
            )

        store.review_item(
            first_plan.plan_id,
            first_plan.items[0].spec_id,
            approve=True,
            reason="first is sound",
        )
        with pytest.raises(ValueError, match="novelty"):
            store.review_item(
                second_plan.plan_id,
                second_plan.items[0].spec_id,
                approve=True,
                reason="looks sound but duplicates first",
            )
