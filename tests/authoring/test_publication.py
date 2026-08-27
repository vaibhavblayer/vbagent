import json

from vbagent.authoring.models import AuthoringRequest
from vbagent.authoring.paths import (
    generated_build_path,
    generated_collection_manifest_path,
)
from vbagent.authoring.planner import AuthoringPlanner
from vbagent.authoring.publication import assemble_generated_run
from vbagent.authoring.results import (
    REQUIRED_ACCEPTANCE_GATES,
    AuthoredCandidate,
    CandidateStatus,
    GateResult,
)
from vbagent.authoring.store import AuthoringStore


def test_publication_reuses_cli_assembly_answer_extraction_and_pdf_compile(
    tmp_path,
    monkeypatch,
):
    output = tmp_path / "agentic" / "authoring"
    plan = AuthoringPlanner().plan(
        AuthoringRequest(
            exam="jee_main",
            subject="physics",
            chapter="kinematics",
            topics=["projectile motion"],
            count=2,
            question_types={"mcq_sc": 1},
            difficulties={5: 1},
            seed=87,
        )
    )

    def fake_compile(result, output_dir=None, verbose=False):
        assert result.main_tex_path.name == "main.tex"
        assert verbose is False
        pdf = output_dir / "main.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        return True, str(pdf)

    monkeypatch.setattr("vbagent.dpp.builder.DPPResult.compile", fake_compile)

    with AuthoringStore(output) as store:
        store.create_run(plan, output, max_attempts=1)
        for _ in range(2):
            claimed = store.claim_next(plan.plan_id, "publication-test")
            problem = (
                rf"\item Problem {claimed.spec.ordinal}"
                "\n"
                r"\begin{tasks}(2)\task Correct \ans\task B\task C\task D\end{tasks}"
            )
            candidate = AuthoredCandidate(
                spec=claimed.spec,
                status=CandidateStatus.ACCEPTED,
                problem_latex=problem,
                draft_solution_latex=r"\begin{solution}Solved.\end{solution}",
                independent_solution_latex=(
                    r"\begin{solution}Solved.\end{solution}"
                ),
                final_latex=(
                    problem + "\n" + r"\begin{solution}Solved.\end{solution}"
                ),
                gates=[
                    GateResult(gate=gate, passed=True)
                    for gate in REQUIRED_ACCEPTANCE_GATES
                ],
            )
            artifact_dir, digest = store.write_candidate_artifacts(
                claimed,
                candidate,
            )
            store.record_candidate(
                claimed,
                candidate,
                artifact_dir=artifact_dir,
                artifact_sha256=digest,
            )

        publication = assemble_generated_run(store, plan.plan_id)
        store.write_run_manifest(plan.plan_id)

    run_dir = tmp_path
    assert publication["status"] == "completed"
    assert publication["compile_success"] is True
    assert publication["main_tex_path"] == str(run_dir / "main.tex")
    assert publication["answer_key_path"] == str(run_dir / "answer_key.tex")
    assert publication["pdf_path"] == str(run_dir / "main.pdf")
    assert (run_dir / "main.tex").is_file()
    assert (run_dir / "answer_key.tex").is_file()
    assert (run_dir / "main.pdf").read_bytes().startswith(b"%PDF")
    assert not (run_dir / "problems").exists()

    main = (run_dir / "main.tex").read_text(encoding="utf-8")
    assert r"\foreach \i in {1, 2}" in main
    assert r"\input{agentic/generated/problem_\i.tex}" in main
    assert r"\input{answer_key.tex}" in main
    answer_key = (run_dir / "answer_key.tex").read_text(encoding="utf-8")
    assert r"\begin{multicols}{2}" in answer_key
    assert answer_key.count(r"\item (a)") == 2

    build = json.loads(
        generated_build_path(output, plan.plan_id).read_text(encoding="utf-8")
    )
    assert build == publication
    manifest = json.loads(generated_collection_manifest_path(output).read_text(encoding="utf-8"))
    assert manifest["publication"]["pdf_path"] == str(run_dir / "main.pdf")
