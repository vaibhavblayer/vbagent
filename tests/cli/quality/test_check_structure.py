"""Regression tests for the split quality-check CLI workflow."""

import json

from click.testing import CliRunner

from vbagent.cli.quality import check as check_module
from vbagent.cli.quality.checker_session import (
    _detect_subject_for_file,
    run_checker_session,
)


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
