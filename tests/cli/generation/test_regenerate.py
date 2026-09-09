"""Tests for role-scoped diagram regeneration."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from rich.console import Console

from vbagent.cli.generation import regenerate as regenerate_module
from vbagent.cli.generation.regenerate import (
    _is_current_scan_target,
    _regenerate_current_scan_file,
    _replace_problem_diagrams,
    _replace_solution_diagrams,
    _selected_scan_files,
    regenerate,
)

PROBLEM_DIAGRAM = r"""\begin{center}
\begin{tikzpicture}
\draw (0,0) -- (1,0);
\end{tikzpicture}
\end{center}"""

SOLUTION_DIAGRAM = r"""\begin{center}
\begin{tikzpicture}
\draw[->] (0,0) -- (0,1);
\end{tikzpicture}
\end{center}"""


def _combined_tex() -> str:
    return (
        "\\item Passage text.\n"
        + PROBLEM_DIAGRAM
        + r"""
\def\OptionA{\begin{tikzpicture}\node{A};\end{tikzpicture}}
\begin{tasks}(1)\task \OptionA\end{tasks}
\begin{solution}
Keep this solution text exactly.
"""
        + SOLUTION_DIAGRAM
        + "\n\\end{solution}\n\\begin{finalanswer}$1$\\end{finalanswer}\n"
    )


def test_problem_replacement_preserves_option_macro_diagrams():
    problem, solution = regenerate_module._split_problem_and_solution(_combined_tex())

    updated = _replace_problem_diagrams(
        problem,
        r"\begin{tikzpicture}\draw (0,0) circle (1);\end{tikzpicture}",
    )

    assert "circle (1)" in updated
    assert "\\def\\OptionA" in updated
    assert "\\node{A}" in updated
    assert "Keep this solution text exactly." in solution


def test_solution_replacement_does_not_touch_solution_prose():
    _problem, solution = regenerate_module._split_problem_and_solution(_combined_tex())

    updated, count = _replace_solution_diagrams(
        solution,
        lambda _old, _index, _total: (
            r"\begin{tikzpicture}\draw (0,0) rectangle (1,1);\end{tikzpicture}"
        ),
    )

    assert count == 1
    assert "Keep this solution text exactly." in updated
    assert "rectangle (1,1)" in updated
    assert "\\draw[->]" not in updated


def test_current_scan_file_scopes_problem_and_solution_independently(
    tmp_path, monkeypatch
):
    scans = tmp_path / "agentic" / "scans"
    scans.mkdir(parents=True)
    tex_file = scans / "problem_1.tex"
    original = _combined_tex()
    tex_file.write_text(original)

    def fake_generate(**kwargs):
        if kwargs["role"] == "problem":
            return r"\begin{tikzpicture}\node{new problem};\end{tikzpicture}"
        return r"\begin{tikzpicture}\node{new solution};\end{tikzpicture}"

    monkeypatch.setattr(regenerate_module, "_generate_scoped_diagram", fake_generate)
    console = Console(file=None, force_terminal=False)

    changed, count = _regenerate_current_scan_file(
        tex_file, "problem", None, False, console
    )
    problem_only = tex_file.read_text()
    assert changed is True
    assert count == 1
    assert "new problem" in problem_only
    assert SOLUTION_DIAGRAM in problem_only
    assert "Keep this solution text exactly." in problem_only

    tex_file.write_text(original)
    changed, count = _regenerate_current_scan_file(
        tex_file, "solution", None, False, console
    )
    solution_only = tex_file.read_text()
    assert changed is True
    assert count == 1
    assert PROBLEM_DIAGRAM in solution_only
    assert "new solution" in solution_only
    assert "Keep this solution text exactly." in solution_only


def test_compile_failure_leaves_scan_file_unchanged(tmp_path, monkeypatch):
    tex_file = tmp_path / "problem_1.tex"
    original = _combined_tex()
    tex_file.write_text(original)

    monkeypatch.setattr(
        regenerate_module,
        "_generate_scoped_diagram",
        lambda **_kwargs: (
            r"\begin{tikzpicture}\node{invalid candidate};\end{tikzpicture}"
        ),
    )
    monkeypatch.setattr(
        "vbagent.compile.compile_latex",
        lambda *_args, **_kwargs: SimpleNamespace(
            success=False,
            error_summary="invalid diagram",
        ),
    )

    with pytest.raises(RuntimeError, match="invalid diagram"):
        _regenerate_current_scan_file(
            tex_file,
            "problem",
            None,
            True,
            Console(file=None, force_terminal=False),
        )

    assert tex_file.read_text() == original


def test_scan_selection_uses_problem_numbers_and_ranges(tmp_path):
    files = [tmp_path / f"problem_{number}.tex" for number in (1, 2, 3, 10)]

    selected = _selected_scan_files(files, [], 2, 10, {3})
    assert [path.stem for path in selected] == ["problem_2", "problem_10"]

    selected = _selected_scan_files(files, ["3"], None, None, set())
    assert [path.stem for path in selected] == ["problem_3"]


def test_legacy_problem_and_concepts_directories_are_not_current_scans(tmp_path):
    problem_dir = tmp_path / "legacy-problem"
    problem_dir.mkdir()
    (problem_dir / "problem.tex").write_text("problem")
    (problem_dir / "meta.json").write_text("{}")

    concepts_dir = tmp_path / "legacy-concepts"
    concepts_dir.mkdir()
    (concepts_dir / "concepts.tex").write_text("concepts")
    (concepts_dir / "concepts.json").write_text("{}")

    assert _is_current_scan_target(problem_dir) is False
    assert _is_current_scan_target(concepts_dir) is False


def test_cli_accepts_project_folder_and_scoped_range(tmp_path, monkeypatch):
    scans = tmp_path / "agentic" / "scans"
    scans.mkdir(parents=True)
    for number in (1, 2, 3):
        (scans / f"problem_{number}.tex").write_text(_combined_tex())

    seen: list[str] = []

    def fake_regenerate(tex_file, scope, *args, **kwargs):
        seen.append(f"{tex_file.stem}:{scope}")
        return True, 1

    monkeypatch.setattr(
        regenerate_module, "_regenerate_current_scan_file", fake_regenerate
    )

    result = CliRunner().invoke(
        regenerate,
        [
            str(tmp_path),
            "--problem-diagram",
            "--from",
            "1",
            "--to",
            "3",
            "--exclude",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen == ["problem_1:problem", "problem_3:problem"]
