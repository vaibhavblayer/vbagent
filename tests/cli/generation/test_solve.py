"""Tests for solution-only generation from scanned TeX projects."""

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from vbagent.cli.generation.solve import (
    _folder_units,
    _item_spans,
    _resolve_folder_output_path,
    has_solution_environment,
    parse_excluded_indices,
    select_item_indices,
    sort_tex_files,
    solve,
)


def test_parse_excluded_indices_accepts_comma_and_repeated_values():
    assert parse_excluded_indices(("5, 7", "8", "7")) == {5, 7, 8}


def test_select_item_indices_applies_range_then_exclusions():
    assert select_item_indices(10, 1, 8, {2, 5, 8}) == [1, 3, 4, 6, 7]


def test_folder_files_are_sorted_by_numeric_problem_id(tmp_path):
    files = [
        tmp_path / "Problem_1.tex",
        tmp_path / "Problem_10.tex",
        tmp_path / "Problem_2.tex",
        tmp_path / "Problem_13.tex",
    ]

    assert [path.name for path in sort_tex_files(files)] == [
        "Problem_1.tex",
        "Problem_2.tex",
        "Problem_10.tex",
        "Problem_13.tex",
    ]


def test_folder_units_use_problem_number_suffixes(tmp_path):
    files = [
        tmp_path / "problem_1.tex",
        tmp_path / "problem_5.tex",
        tmp_path / "problem_10.tex",
    ]

    assert [number for number, _ in _folder_units(files)] == [1, 5, 10]

def test_existing_solution_environment_is_detected():
    assert has_solution_environment(
        r"\item Problem\begin{solution}Already solved\end{solution}"
    )
    assert not has_solution_environment(r"\item Problem without a solution")


def test_item_spans_preserve_project_items():
    content = """% subject: physics

\\item First problem

\\item Second problem
"""

    spans = _item_spans(content)
    assert [item for _, _, item in spans] == [
        r"\item First problem",
        r"\item Second problem",
    ]


def test_folder_output_defaults_to_a_separate_solutions_directory(tmp_path):
    source_dir = tmp_path / "scanned"
    source_dir.mkdir()

    assert _resolve_folder_output_path(source_dir, None) == (
        Path("agentic") / "solutions" / "scanned"
    )


def test_solve_help_exposes_project_controls():
    result = CliRunner().invoke(solve, ["--help"])

    assert result.exit_code == 0
    assert "--from" in result.output
    assert "--to" in result.output
    assert "--exclude" in result.output
    assert "--no-diagram" in result.output
    assert "--in-place" in result.output
    assert "agentic/scans" in result.output
    assert "integer" in result.output


def test_solve_default_workspace_uses_sidecar_and_updates_selected_problem(
    monkeypatch,
    tmp_path,
):
    scans = tmp_path / "agentic" / "scans"
    classifications = tmp_path / "agentic" / "classifications"
    images = tmp_path / "images"
    scans.mkdir(parents=True)
    classifications.mkdir(parents=True)
    images.mkdir()
    (scans / "problem_1.tex").write_text(r"\item Leave unchanged.")
    (scans / "problem_5.tex").write_text(r"\item Find the period of $f(x)$.")
    (images / "problem_5.png").touch()
    (classifications / "problem_5.json").write_text(
        json.dumps(
            {
                "subject": "mathematics",
                "question_type": "subjective",
                "has_diagram": False,
                "chapter": "Trigonometry",
                "topic": "Periodic functions",
            }
        )
    )
    calls = []

    def fake_generate_solution(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            latex=(
                kwargs["problem_latex"]
                + r"\begin{solution}Period work.\end{solution}"
            )
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "vbagent.config.get_config",
        lambda: SimpleNamespace(subject="physics"),
    )
    monkeypatch.setattr(
        "vbagent.pipeline.stages.generate_solution_orchestrated",
        fake_generate_solution,
    )

    result = CliRunner().invoke(
        solve,
        ["--item", "5", "--no-cache", "--quiet"],
    )

    assert result.exit_code == 0, result.output
    assert (scans / "problem_1.tex").read_text() == r"\item Leave unchanged."
    assert r"\begin{solution}" in (scans / "problem_5.tex").read_text()
    assert len(calls) == 1
    assert calls[0]["primary"].subject == "mathematics"
    assert calls[0]["primary"].chapter == "Trigonometry"
    assert calls[0]["image_path"] == str(images / "problem_5.png")
