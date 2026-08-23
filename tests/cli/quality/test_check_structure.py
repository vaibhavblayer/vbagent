"""Regression tests for the split quality-check CLI workflow."""

import json
from types import SimpleNamespace

from click.testing import CliRunner

from vbagent.cli.quality import check as check_module
from vbagent.cli.quality.checker_session import (
    _detect_subject_for_file,
    run_checker_session,
)
from vbagent.models.quality import ReviewResult
from vbagent.models.version_store import ProblemCheckStatus, VersionStore


def test_check_module_delegates_to_shared_session():
    assert check_module._run_checker_session is run_checker_session


def test_grammar_command_preserves_checker_configuration(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        check_module,
        "_run_checker_session",
        lambda **kwargs: calls.append(kwargs),
    )

    result = CliRunner().invoke(
        check_module.check,
        [
            "grammar",
            "--dir",
            str(tmp_path),
            "--count",
            "3",
            "--prompt",
            "Use British English",
            "--reset",
            "--yes",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "output_dir": str(tmp_path),
            "count": 3,
            "problem_id": None,
            "checker_name": "grammar",
            "check_func_module": "vbagent.agents.quality.grammar_checker",
            "check_func_name": "check_grammar",
            "require_solution": False,
            "reset": True,
            "extra_prompt": "Use British English",
            "auto_approve": True,
        }
    ]


def test_subject_detection_moved_with_checker_session(tmp_path):
    scans_dir = tmp_path / "scans"
    classifications_dir = tmp_path / "classifications"
    scans_dir.mkdir()
    classifications_dir.mkdir()
    tex_file = scans_dir / "problem_1.tex"
    tex_file.write_text("\\item A chemistry problem")
    (classifications_dir / "problem_1.json").write_text(
        json.dumps({"subject": "chemistry"})
    )

    assert _detect_subject_for_file(tex_file) == "chemistry"


def test_check_directory_resolution_reuses_legacy_trailing_slash(tmp_path):
    scans_dir = tmp_path / "agentic" / "scans"
    scans_dir.mkdir(parents=True)
    stored_dir = f"{scans_dir}/"
    store = VersionStore(base_dir=str(tmp_path))
    try:
        store.init_problem_checks(["problem_124"], stored_dir)

        assert check_module._resolve_tracked_output_dir(store, None) == stored_dir
        assert (
            check_module._resolve_tracked_output_dir(store, str(scans_dir))
            == stored_dir
        )
    finally:
        store.close()


def test_check_init_range_filters_by_problem_number(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scans_dir = tmp_path / "agentic" / "scans"
    scans_dir.mkdir(parents=True)
    (scans_dir / "problem_2.tex").write_text(r"\item Two")
    (scans_dir / "problem_124.tex").write_text(r"\item One twenty four")

    result = CliRunner().invoke(
        check_module.check,
        ["init", "--dir", str(scans_dir), "--from", "124", "--to", "124"],
    )

    assert result.exit_code == 0, result.output
    store = VersionStore(base_dir=str(tmp_path))
    try:
        tracked_dir = store.get_problem_check_dirs()[0]
        assert store.get_pending_problems(tracked_dir) == ["problem_124"]
    finally:
        store.close()


def test_check_continue_reuses_init_dir_and_forwards_compile_error(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    scans_dir = tmp_path / "agentic" / "scans"
    classifications_dir = tmp_path / "agentic" / "classifications"
    scans_dir.mkdir(parents=True)
    classifications_dir.mkdir(parents=True)
    (scans_dir / "problem_124.tex").write_text(
        r"\item Test.\begin{solution}\addplot[only marks]\end{solution}"
    )
    (classifications_dir / "problem_124.json").write_text(
        json.dumps({"subject": "mathematics"})
    )

    init_result = CliRunner().invoke(
        check_module.check,
        ["init", "--dir", f"{scans_dir}/", "--from", "124", "--to", "124"],
    )
    assert init_result.exit_code == 0, init_result.output

    from vbagent import compile as compile_module
    from vbagent.agents.quality import reviewer

    monkeypatch.setattr(
        compile_module,
        "compile_latex",
        lambda *args, **kwargs: SimpleNamespace(
            success=False,
            error_summary="confirmed pgfplots failure",
        ),
    )
    captured = {}

    def fake_review(context):
        captured["context"] = context
        return ReviewResult(
            problem_id=context.problem_id,
            passed=True,
            suggestions=[],
            summary="No correction returned",
        )

    monkeypatch.setattr(reviewer, "review_problem_sync", fake_review)

    continue_result = CliRunner().invoke(
        check_module.check,
        ["continue", "--count", "1"],
    )

    assert continue_result.exit_code == 0, continue_result.output
    assert "forwarding the exact diagnostic" in continue_result.output
    assert captured["context"].subject == "mathematics"
    assert captured["context"].compile_error == "confirmed pgfplots failure"

    store = VersionStore(base_dir=str(tmp_path))
    try:
        tracked_dir = store.get_problem_check_dirs()[0]
        assert store.get_problems_by_status(
            tracked_dir, ProblemCheckStatus.FAILED
        ) == ["problem_124"]
    finally:
        store.close()
