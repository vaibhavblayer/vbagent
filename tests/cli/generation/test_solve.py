"""Tests for solution-only generation from scanned TeX projects."""

from pathlib import Path

from click.testing import CliRunner

from vbagent.cli.generation.solve import (
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
