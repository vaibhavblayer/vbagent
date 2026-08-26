import hashlib

import pytest

from vbagent.authoring.api import execute_variants, plan_authoring
from vbagent.authoring.models import AuthoringRequest, SourceKind, VariantFamily
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.store import AuthoringStore


def _request(*, seed=1, count=1, topics=None):
    return AuthoringRequest(
        exam="jee_main",
        subject="physics",
        chapter="kinematics",
        topics=topics or [],
        count=count,
        question_types={"mcq_sc": 1},
        difficulties={5: 1},
        seed=seed,
    )


def _accept_plan(store, plan, output):
    store.create_run(plan, output, max_attempts=1)
    claimed = store.claim_next(plan.plan_id, "test-worker")
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
        independent_solution_latex=r"\begin{solution}The range is $R$.\end{solution}",
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
    return claimed.spec, final


def test_plan_authoring_balances_against_accepted_cross_run_coverage(tmp_path):
    output = tmp_path / "authoring"
    first = AuthoringPlanner().plan(_request(topics=["projectile motion"]))
    with AuthoringStore(output) as store:
        accepted_spec, _ = _accept_plan(store, first, output)

    next_plan = plan_authoring(_request(seed=2), output_dir=output)

    assert next_plan.request.existing_accepted_counts[accepted_spec.topic_id] == 1
    assert next_plan.items[0].topic_id != accepted_spec.topic_id


def test_variants_require_accepted_parent_and_persist_lineage(tmp_path):
    output = tmp_path / "authoring"
    parent_plan = AuthoringPlanner().plan(_request(topics=["projectile motion"]))
    with AuthoringStore(output) as store:
        parent_spec, parent_latex = _accept_plan(store, parent_plan, output)

    execution = execute_variants(
        parent_spec.spec_id,
        output,
        count=4,
        variant_families={"numerical": 1, "context": 1},
        start=False,
    )

    assert execution.stats["pending"] == 4
    assert execution.plan.distributions["variant_family"] == {
        "context": 2,
        "numerical": 2,
    }
    assert all(item.source_kind is SourceKind.VARIANT for item in execution.plan.items)
    assert {item.variant_family for item in execution.plan.items} == {
        VariantFamily.NUMERICAL,
        VariantFamily.CONTEXT,
    }
    assert all(item.parent_spec_id == parent_spec.spec_id for item in execution.plan.items)
    assert all(item.lineage_root_spec_id == parent_spec.spec_id for item in execution.plan.items)
    assert all(item.lineage_depth == 1 for item in execution.plan.items)
    assert all(
        item.parent_artifact_sha256 == hashlib.sha256(parent_latex.encode()).hexdigest()
        for item in execution.plan.items
    )


def test_variant_fanout_cap_is_transactional(tmp_path):
    output = tmp_path / "authoring"
    parent_plan = AuthoringPlanner().plan(_request(topics=["projectile motion"]))
    with AuthoringStore(output) as store:
        parent_spec, _ = _accept_plan(store, parent_plan, output)

    execute_variants(
        parent_spec.spec_id,
        output,
        count=2,
        variant_families={"numerical": 1},
        max_variants_per_parent=2,
        start=False,
    )
    with pytest.raises(ValueError, match="cap is 2"):
        execute_variants(
            parent_spec.spec_id,
            output,
            count=1,
            variant_families={"context": 1},
            max_variants_per_parent=2,
            start=False,
        )


def test_variant_request_cannot_name_unaccepted_parent(tmp_path):
    output = tmp_path / "authoring"
    plan = AuthoringPlanner().plan(_request(topics=["projectile motion"]))
    with AuthoringStore(output) as store:
        store.create_run(plan, output)

    with pytest.raises(ValueError, match="not accepted"):
        execute_variants(plan.items[0].spec_id, output, start=False)
