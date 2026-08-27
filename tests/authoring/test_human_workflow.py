import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from vbagent.authoring.application import AuthoringApplication
from vbagent.authoring.completion import plan_completion
from vbagent.authoring.exports import export_item, get_export
from vbagent.authoring.models import AcceptancePolicy, AuthoringRequest
from vbagent.authoring.paths import generated_output_root, generated_problem_path
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.publication import assemble_generated_run
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.store import AuthoringStore, ItemStatus


@pytest.fixture
def output(tmp_path):
    return tmp_path / "agentic" / "authoring"


@pytest.fixture
def compiler(monkeypatch):
    def compile_pdf(result, output_dir=None, verbose=False):
        target = Path(output_dir) / "main.pdf"
        target.write_bytes(b"%PDF-1.4\nfixture\n")
        return True, str(target)

    monkeypatch.setattr("vbagent.dpp.builder.DPPResult.compile", compile_pdf)


def make_plan(seed=1, *, include_solution=True, include_idea=True, human_review=False, count=1):
    return AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="mathematics",
            chapter="sets relations and functions",
            count=count,
            seed=seed,
            include_solution=include_solution,
            include_idea=include_idea,
            acceptance=AcceptancePolicy(human_review_required=human_review),
        )
    )


def record(store, plan, *, reject=False):
    claimed = store.claim_next(plan.plan_id, "test-worker")
    spec = claimed.spec
    problem = spec.parent_problem_latex or (
        rf"\item Find the range for setting {spec.random_seed % 10000}."
        "\n" + r"\begin{tasks}(2)\task A \ans\task B\task C\task D\end{tasks}"
    )
    solution = (
        r"\begin{solution}A checked solution.\end{solution}"
        if spec.include_solution
        else ""
    )
    idea = spec.parent_idea_latex or (
        r"\begin{idea}Preserve the domain.\end{idea}" if spec.include_idea else ""
    )
    if reject:
        status = CandidateStatus.REJECTED
        gates = [
            GateResult(gate="draft", passed=True),
            GateResult(
                gate="spec_alignment",
                passed=False,
                summary="requested method was not used",
            ),
        ]
    elif spec.include_solution:
        status = (
            CandidateStatus.NEEDS_REVIEW
            if spec.acceptance.human_review_required
            else CandidateStatus.ACCEPTED
        )
        gates = [
            GateResult(gate=gate, passed=True) for gate in REQUIRED_ACCEPTANCE_GATES
        ]
    else:
        status = CandidateStatus.DRAFT
        gates = [
            GateResult(gate=gate, passed=True)
            for gate in ("draft", "structure", "final_structure", "compile")
        ]
    candidate = AuthoredCandidate(
        spec=spec,
        status=status,
        problem_latex=problem,
        draft_solution_latex=solution,
        independent_solution_latex=solution,
        idea_latex=idea,
        final_latex="\n\n".join(
            part for part in (problem, solution, idea if not reject else "") if part
        ),
        gates=gates,
    )
    folder, digest = store.write_candidate_artifacts(claimed, candidate)
    store.record_candidate(
        claimed,
        candidate,
        artifact_dir=folder,
        artifact_sha256=digest,
        retry_base_seconds=0,
    )
    return claimed, candidate


def test_numbering_accumulates_and_rebuild_is_idempotent(output, tmp_path, compiler):
    with AuthoringStore(output) as store:
        first, second = make_plan(101), make_plan(102)
        for plan in (first, second):
            store.create_run(plan, output, max_attempts=1)
            record(store, plan)
            result = assemble_generated_run(store, plan.plan_id)
            assert result["compile_success"]
        assert result["problem_count"] == 2
        assert result["run_problem_count"] == 1
        repeat = assemble_generated_run(store, first.plan_id)
        assert repeat["problem_count"] == 2
    generated = generated_output_root(output)
    assert sorted(path.name for path in generated.glob("*.tex")) == [
        "problem_1.tex",
        "problem_2.tex",
    ]
    assert not (generated / "authoring").exists()
    metadata = json.loads((generated / "problem_1.json").read_text())
    assert metadata["validated"] is True
    assert metadata["specification"]["subject"] == "mathematics"
    main = (tmp_path / "main.tex").read_text()
    assert r"\foreach \i in {1, 2}" in main
    assert r"\input{agentic/generated/problem_\i.tex}" in main
    assert (tmp_path / "answer_key.tex").exists()
    assert (tmp_path / "main.pdf").exists()


def test_rebuild_selects_human_numbers_across_runs_and_preserves_all_sources(output, tmp_path, compiler):
    with AuthoringStore(output) as store:
        first, second = make_plan(101, count=5), make_plan(102, count=2)
        for plan in (first, second):
            store.create_run(plan, output, max_attempts=1)
            for _ in plan.items:
                record(store, plan)
            assert assemble_generated_run(store, plan.plan_id)["compile_success"]
    generated = generated_output_root(output)
    originals = {path.name: path.read_bytes() for path in generated.glob("problem_*.*")}
    assert json.loads(originals["problem_6.json"])["ordinal"] == 1

    result = AuthoringApplication(output).start(
        second.plan_id, confirmed=True, rebuild_only=True, problem_numbers=[6, 7],
    )

    assert result.action == "rebuild"
    assert not result.dispatched
    assert result.status.publication["compile_success"]
    assert result.status.publication["problem_count"] == 2
    assert result.status.publication["problem_numbers"] == [6, 7]
    assert r"\foreach \i in {6, 7}" in (tmp_path / "main.tex").read_text()
    assert (tmp_path / "answer_key.tex").read_text().count(r"\item (a)") == 2
    assert {path.name: path.read_bytes() for path in generated.glob("problem_*.*")} == originals

    # The manual CLI and MCP-backed application share the same exact selection.
    from click.testing import CliRunner

    from vbagent.cli.authoring import author

    cli = CliRunner().invoke(author, [
        "continue", "--run-id", second.plan_id, "--output", str(output),
        "--rebuild-only", "--problem-number", "7", "--problem-number", "6",
    ])
    assert cli.exit_code == 0, cli.output
    assert r"\foreach \i in {7, 6}" in (tmp_path / "main.tex").read_text()


@pytest.mark.parametrize("selection", [[1, 999], [1, 2]])
def test_subset_does_not_silently_omit_missing_or_unapproved_items(output, tmp_path, compiler, selection):
    with AuthoringStore(output) as store:
        accepted, review = make_plan(111), make_plan(112, human_review=True)
        for plan in (accepted, review):
            store.create_run(plan, output, max_attempts=1)
            record(store, plan)
            assemble_generated_run(store, plan.plan_id)
        original = {name: (tmp_path / name).read_bytes() for name in ("main.tex", "main.pdf", "answer_key.tex")}
        result = assemble_generated_run(store, review.plan_id, problem_numbers=selection)
        assert result["status"] == "failed"
        assert "missing or not ready" in result["error"]
        assert {name: (tmp_path / name).read_bytes() for name in original} == original


@pytest.mark.parametrize("selection", [[], [0], [-1], [1, 1], [True], ["1"]])
def test_invalid_problem_selection_is_rejected_before_publication(output, selection):
    plan = make_plan(133)
    with AuthoringStore(output) as store:
        store.create_run(plan, output, max_attempts=1)
    with pytest.raises(ValueError, match="distinct positive integers"):
        AuthoringApplication(output).start(
            plan.plan_id, confirmed=True, rebuild_only=True, problem_numbers=selection,
        )
    assert not (output.parent.parent / "main.tex").exists()


def test_selection_cannot_be_used_to_accidentally_start_generation(output):
    with pytest.raises(ValueError, match="only valid with rebuild_only"):
        AuthoringApplication(output).start("irrelevant", confirmed=True, problem_numbers=[6, 7])


def test_unmanaged_number_and_root_file_are_preserved(output, tmp_path, compiler):
    generated = generated_output_root(output)
    generated.mkdir(parents=True)
    existing = generated / "problem_1.tex"
    existing.write_text("author-owned question")
    (tmp_path / "main.tex").write_text("author-owned main")
    with AuthoringStore(output) as store:
        plan = make_plan()
        store.create_run(plan, output, max_attempts=1)
        claimed, _ = record(store, plan)
        assert get_export(store, claimed.spec.spec_id)["number"] == 2
        result = assemble_generated_run(store, plan.plan_id)
    assert result["status"] == "failed"
    assert "preserved" in result["error"]
    assert existing.read_text() == "author-owned question"
    assert (tmp_path / "main.tex").read_text() == "author-owned main"


def test_manual_problem_and_metadata_edits_are_preserved(output, compiler):
    with AuthoringStore(output) as store:
        plan = make_plan()
        store.create_run(plan, output, max_attempts=1)
        claimed, _ = record(store, plan)
        path = generated_problem_path(output, 1)
        path.write_text("my edited question")
        result = assemble_generated_run(store, plan.plan_id)
        assert result["status"] == "failed"
        assert path.read_text() == "my edited question"
        with pytest.raises(ValueError, match="manual edits"):
            export_item(store, plan.plan_id, claimed.spec.spec_id)


def test_exhausted_draft_awaits_author_and_cannot_skip_checks(output, compiler):
    with AuthoringStore(output) as store:
        plan = make_plan()
        store.create_run(plan, output, max_attempts=1)
        claimed, candidate = record(store, plan, reject=True)
        assert store.stats(plan.plan_id)["needs_review"] == 1
        assert store.stats(plan.plan_id)["rejected"] == 0
        assert candidate.idea_latex in generated_problem_path(output, 1).read_text()
        with pytest.raises(ValueError, match="failed or missing checks"):
            store.review_item(
                plan.plan_id, claimed.spec.spec_id, approve=True, reason="I like it"
            )
        store.defer_or_revise_item(
            plan.plan_id, claimed.spec.spec_id, revise=False, reason="keep for later"
        )
        assert store.get_item(claimed.spec.spec_id)["status"] == "needs_review"
        store.review_item(
            plan.plan_id,
            claimed.spec.spec_id,
            approve=False,
            reason="author chooses rejection",
        )
        assert store.stats(plan.plan_id)["rejected"] == 1
        assert (
            generated_problem_path(output, 1).read_text()
            == candidate.deliverable_latex + "\n"
        )
        assert store.restore_unreviewed_rejections(plan.plan_id) == 0
        assert (
            store.item_evidence(plan.plan_id, claimed.spec.spec_id)["attempts"][0][
                "candidate_status"
            ]
            == "rejected"
        )


def test_author_revision_queues_one_more_attempt_without_losing_draft(output):
    with AuthoringStore(output) as store:
        plan = make_plan()
        store.create_run(plan, output, max_attempts=1)
        claimed, candidate = record(store, plan, reject=True)
        store.defer_or_revise_item(
            plan.plan_id, claimed.spec.spec_id, revise=True, reason="use inverse images"
        )
        item = store.get_item(claimed.spec.spec_id)
        assert item["status"] == "pending"
        assert item["max_attempts"] == 2
        assert item["attempts"] == 1
        assert (
            generated_problem_path(output, 1).read_text()
            == candidate.deliverable_latex + "\n"
        )
        retry = store.claim_next(plan.plan_id, "revision-worker")
        assert retry.retry_reason == "use inverse images"


def test_deferred_solution_completion_updates_same_file_and_keeps_evidence(
    output, tmp_path, compiler
):
    with AuthoringStore(output) as store:
        original = make_plan(include_solution=False)
        store.create_run(original, output, max_attempts=1)
        claimed, draft = record(store, original)
        assert store.stats(original.plan_id)["draft"] == 1
        before = generated_problem_path(output, 1).read_text()
        result = assemble_generated_run(store, original.plan_id)
        assert result["draft_count"] == 1
        assert "Draft collection" in (tmp_path / "main.tex").read_text()
        assert "Unverified" in (tmp_path / "answer_key.tex").read_text()

    completion = plan_completion(output, original.plan_id)
    assert completion.items[0].parent_problem_latex == draft.problem_latex
    assert completion.items[0].parent_idea_latex == draft.idea_latex
    with AuthoringStore(output) as store:
        store.create_run(completion, output, max_attempts=1)
        _, finished = record(store, completion)
        result = assemble_generated_run(store, completion.plan_id)
        assert result["compile_success"]
        assert result["problem_count"] == 1
        assert result["draft_count"] == 0
        assert get_export(store, finished.spec.spec_id)["number"] == 1
        assert (claimed.output_dir / "problem.tex").read_text() == before
        assemble_generated_run(store, original.plan_id)
        assert (
            generated_problem_path(output, 1).read_text() == finished.final_latex + "\n"
        )
    assert not generated_problem_path(output, 2).exists()
    assert "Draft collection" not in (tmp_path / "main.tex").read_text()
    with pytest.raises(ValueError, match="already contain"):
        plan_completion(output, original.plan_id)


def test_components_can_be_added_in_two_steps_from_original_run(output, compiler):
    with AuthoringStore(output) as store:
        original = make_plan(include_solution=False, include_idea=False)
        store.create_run(original, output, max_attempts=1)
        record(store, original)
    idea_plan = plan_completion(output, original.plan_id, include_solution=False)
    with AuthoringStore(output) as store:
        store.create_run(idea_plan, output, max_attempts=1)
        record(store, idea_plan)
    solution_plan = plan_completion(output, original.plan_id)
    assert solution_plan.items[0].parent_spec_id == idea_plan.items[0].spec_id
    with AuthoringStore(output) as store:
        store.create_run(solution_plan, output, max_attempts=1)
        _, finished = record(store, solution_plan)
        assemble_generated_run(store, original.plan_id)
        result = assemble_generated_run(store, idea_plan.plan_id)
        assert result["compile_success"]
        assert get_export(store, finished.spec.spec_id)["number"] == 1
        assert (
            generated_problem_path(output, 1).read_text() == finished.final_latex + "\n"
        )
    assert not generated_problem_path(output, 2).exists()
    with pytest.raises(ValueError, match="already contain"):
        plan_completion(output, idea_plan.plan_id)


def test_manually_edited_json_stops_completion_before_tex_is_overwritten(output):
    with AuthoringStore(output) as store:
        original = make_plan(include_solution=False)
        store.create_run(original, output, max_attempts=1)
        record(store, original)
    tex = generated_problem_path(output, 1)
    before = tex.read_bytes()
    sidecar = tex.with_suffix(".json")
    sidecar.write_text('{"author_note": "preserve my edit"}\n')
    plan = plan_completion(output, original.plan_id)
    with AuthoringStore(output) as store:
        store.create_run(plan, output, max_attempts=1)
        record(store, plan)
        with pytest.raises(ValueError, match="manual edits"):
            export_item(store, plan.plan_id, plan.items[0].spec_id)
    assert tex.read_bytes() == before
    assert json.loads(sidecar.read_text()) == {"author_note": "preserve my edit"}


def test_completion_plan_cannot_forge_accepted_parent(output):
    with AuthoringStore(output) as store:
        original = make_plan(include_solution=False)
        store.create_run(original, output, max_attempts=1)
        record(store, original)
    plan = plan_completion(output, original.plan_id)
    forged = plan.model_copy(
        update={
            "items": (plan.items[0].model_copy(update={"parent_was_accepted": True}),)
        }
    )
    with AuthoringStore(output) as store:
        with pytest.raises(ValueError, match="validation status"):
            store.create_run(forged, output)


def test_reviewing_a_completed_component_preserves_single_problem_coverage(output):
    with AuthoringStore(output) as store:
        original = make_plan(include_idea=False, human_review=True)
        store.create_run(original, output, max_attempts=1)
        claimed, _ = record(store, original)
        store.review_item(
            original.plan_id, claimed.spec.spec_id, approve=True, reason="checked"
        )
    plan = plan_completion(output, original.plan_id)
    with AuthoringStore(output) as store:
        store.create_run(plan, output, max_attempts=1)
        claimed, _ = record(store, plan)
        assert store.get_item(claimed.spec.spec_id)["status"] == "needs_review"
        store.review_item(
            plan.plan_id,
            claimed.spec.spec_id,
            approve=True,
            reason="checked the added idea",
        )
        scope = dict(
            exam=claimed.spec.exam,
            subject=claimed.spec.subject,
            catalog_source_sha256=claimed.spec.syllabus_source_sha256,
        )
        coverage = store.accepted_coverage_for_catalog(**scope)
        assert sum(coverage["topic"].values()) == 1
        assert [
            spec_id for spec_id, _ in store.accepted_documents_for_catalog(**scope)
        ] == [claimed.spec.spec_id]
        assert get_export(store, claimed.spec.spec_id)["number"] == 1


def test_failed_completion_keeps_previous_human_copy(output):
    with AuthoringStore(output) as store:
        original = make_plan(include_solution=False)
        store.create_run(original, output, max_attempts=1)
        record(store, original)
    before = generated_problem_path(output, 1).read_bytes()
    plan = plan_completion(output, original.plan_id)
    with AuthoringStore(output) as store:
        store.create_run(plan, output, max_attempts=1)
        claimed, _ = record(store, plan, reject=True)
        assert store.get_item(claimed.spec.spec_id)["status"] == "needs_review"
        assert (claimed.output_dir / "review.tex").is_file()
    assert generated_problem_path(output, 1).read_bytes() == before


def test_concurrent_runs_get_unique_numbers(output):
    plans = [make_plan(seed) for seed in range(20, 24)]
    with AuthoringStore(output) as store:
        for plan in plans:
            store.create_run(plan, output, max_attempts=1)

    def work(plan):
        with AuthoringStore(output) as store:
            claimed, _ = record(store, plan)
            return get_export(store, claimed.spec.spec_id)["number"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        numbers = list(pool.map(work, plans))
    assert sorted(numbers) == [1, 2, 3, 4]


def test_rebuild_migrates_only_machine_rejections(output, compiler):
    with AuthoringStore(output) as store:
        plan = make_plan()
        store.create_run(plan, output, max_attempts=1)
        claimed, _ = record(store, plan, reject=True)
        store.conn.execute(
            "UPDATE authoring_items SET status = 'rejected' WHERE spec_id = ?",
            (claimed.spec.spec_id,),
        )
        store.conn.commit()
    result = AuthoringApplication(output).start(
        plan.plan_id, confirmed=True, rebuild_only=True
    )
    assert result.dispatched is False
    assert result.status.stats["needs_review"] == 1
    assert result.status.stats["rejected"] == 0
    assert result.status.current_stage == "awaiting_author_review"
    assert ItemStatus.NEEDS_REVIEW.value == "needs_review"
