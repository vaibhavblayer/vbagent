"""Tests for solution-only generation from scanned TeX projects."""

from pathlib import Path

from click.testing import CliRunner

from vbagent.cli.generation.solve import (
    _item_spans,
    _resolve_folder_output_path,
    parse_excluded_indices,
    select_item_indices,
    solve,
)


def test_parse_excluded_indices_accepts_comma_and_repeated_values():
    assert parse_excluded_indices(("5, 7", "8", "7")) == {5, 7, 8}


def test_select_item_indices_applies_range_then_exclusions():
    assert select_item_indices(10, 1, 8, {2, 5, 8}) == [1, 3, 4, 6, 7]


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
