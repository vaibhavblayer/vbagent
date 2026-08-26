import threading

from vbagent.authoring.models import AuthoringRequest
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.service import AuthoringRunService
from vbagent.authoring.store import AuthoringStore, RunStatus


class StubPipeline:
    def __init__(self, claimed, attempts, contexts):
        self.claimed = claimed
        self.attempts = attempts
        self.contexts = contexts

    def run(self, spec, retry_context=None):
        with self.attempts["lock"]:
            self.attempts[spec.spec_id] = self.attempts.get(spec.spec_id, 0) + 1
            attempt = self.attempts[spec.spec_id]
            self.contexts.append((spec.spec_id, retry_context))
        should_retry = spec.ordinal == 2 and attempt == 1
        status = CandidateStatus.REJECTED if should_retry else CandidateStatus.ACCEPTED
        if should_retry:
            gates = [GateResult(gate="draft", passed=True)]
            gates.append(GateResult(gate="difficulty", passed=False, summary="too easy"))
        else:
            gates = [
                GateResult(gate=gate, passed=True)
                for gate in REQUIRED_ACCEPTANCE_GATES
            ]
        problem = (
            rf"\item Problem {spec.ordinal} has correct option"
            "\n"
            r"\begin{tasks}(2)\task A \ans\task B\task C\task D\end{tasks}"
        )
        return AuthoredCandidate(
            spec=spec,
            status=status,
            problem_latex=problem,
            draft_solution_latex=r"\begin{solution}Solved.\end{solution}",
            independent_solution_latex=r"\begin{solution}Solved.\end{solution}",
            final_latex=problem + "\n" + r"\begin{solution}Solved.\end{solution}",
            gates=gates,
        )


def test_service_executes_concurrently_retries_and_resumes_from_ledger(tmp_path):
    plan = AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=4,
            question_types={"mcq_sc": 1},
            difficulties={5: 1},
            seed=33,
        )
    )
    attempts = {"lock": threading.Lock()}
    contexts = []

    with AuthoringStore(tmp_path) as store:
        store.create_run(plan, tmp_path / "out", max_attempts=2, concurrency=3)

        def factory(claimed, novelty):
            return StubPipeline(claimed, attempts, contexts)

        stats = AuthoringRunService(
            store,
            pipeline_factory=factory,
            retry_base_seconds=0,
        ).execute(plan.plan_id)

        assert stats["status"] == RunStatus.COMPLETED.value
        assert stats["accepted"] == 4
        assert stats["attempts"] == 5
        second = plan.items[1]
        second_contexts = [context for spec_id, context in contexts if spec_id == second.spec_id]
        assert second_contexts[0] is None
        assert "difficulty" in second_contexts[1]
        assert len(store.accepted_documents(plan.plan_id)) == 4

        # Completed runs are idempotent and do not execute their items again.
        again = AuthoringRunService(store, pipeline_factory=factory).execute(plan.plan_id)
        assert again["attempts"] == 5
