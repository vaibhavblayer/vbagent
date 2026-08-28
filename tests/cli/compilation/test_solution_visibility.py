"""Compile visibility flags affect only the generated document preamble."""

import shutil
import subprocess

import pytest
from click.testing import CliRunner

from vbagent.cli.compilation.compile_main import generate_preamble
from vbagent.cli.main import main


@pytest.mark.parametrize("solution", [False, True])
@pytest.mark.parametrize("alternate", [False, True])
def test_solution_exclusions_are_independent(solution, alternate):
    lines = generate_preamble(
        include_solution=solution, include_alternate_solution=alternate
    ).splitlines()

    for environment, visible in (
        ("solution", solution),
        ("alternatesolution", alternate),
    ):
        command = rf"\excludecomment{{{environment}}}"
        assert (command in lines) is not visible
        assert ("% " + command in lines) is visible
    for environment in ("hint", "idea", "remark", "finalanswer"):
        assert rf"\excludecomment{{{environment}}}" in lines


@pytest.mark.parametrize(
    "flags, solution, alternate",
    [
        ([], True, True),
        (["--solution", "--alternatesolution"], True, True),
        (["--no-solution", "--no-alternatesolution"], False, False),
        (["--solution", "--no-alternatesolution"], True, False),
        (["--no-solution", "--alternatesolution"], False, True),
    ],
)
def test_compile_cli_controls_visibility_without_modifying_sources(
    tmp_path, flags, solution, alternate
):
    scans = tmp_path / "scans"
    scans.mkdir()
    source = scans / "problem_1.tex"
    original = (
        b"\\item Question.\n\\begin{solution}\nPrimary solution.\n\\end{solution}\n"
        b"\\begin{alternatesolution}\nAlternate method.\n\\end{alternatesolution}\n"
    )
    source.write_bytes(original)
    output = tmp_path / "main.tex"
    title = "DPP: JEE: III: Functions"

    result = CliRunner().invoke(
        main,
        [
            "compile",
            "-d",
            str(scans),
            "-o",
            str(output),
            "--all-packages",
            "-t",
            title,
            *flags,
        ],
    )

    assert result.exit_code == 0, result.output
    document = output.read_text()
    assert rf"\title{{\textsc{{{title}}}}}" in document
    assert r"\usepackage{chemfig}" in document
    for environment, visible in (
        ("solution", solution),
        ("alternatesolution", alternate),
    ):
        prefix = "% " if visible else ""
        assert prefix + rf"\excludecomment{{{environment}}}" in document.splitlines()
    assert source.read_bytes() == original


def test_compile_help_exposes_both_visibility_switches():
    result = CliRunner().invoke(main, ["compile", "--help"])

    assert result.exit_code == 0
    for flag in (
        "--solution",
        "--no-solution",
        "--alternatesolution",
        "--no-alternatesolution",
    ):
        assert flag in result.output


@pytest.mark.parametrize("solution", [False, True])
@pytest.mark.parametrize("alternate", [False, True])
def test_visibility_in_compiled_pdf(tmp_path, solution, alternate):
    """Check rendered content, not just whether the exclusion line changed."""
    for program in ("pdflatex", "pdftotext", "kpsewhich"):
        if not shutil.which(program):
            pytest.skip(f"{program} is needed for PDF verification")
    for package in (
        "tzplot",
        "kinematikz",
        "chemmacros",
        "fourier",
        "venndiagram",
        "tkz-euclide",
    ):
        found = subprocess.run(
            ["kpsewhich", f"{package}.sty"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if found.returncode:
            pytest.skip(f"Full compilation requires {package}.sty")

    source = tmp_path / "visibility.tex"
    source.write_text(
        generate_preamble(
            title="Visibility check",
            include_all=True,
            include_solution=solution,
            include_alternate_solution=alternate,
        )
        + r"""
\begin{document}
QuestionToken789
\begin{solution}
PrimaryToken123
\end{solution}
\begin{alternatesolution}
AlternateToken456
\end{alternatesolution}
\begin{finalanswer}
HiddenAnswerToken
\end{finalanswer}
\end{document}
"""
    )
    compiled = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", source.name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stdout[-6000:]
    rendered = subprocess.run(
        ["pdftotext", str(source.with_suffix(".pdf")), "-"],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    ).stdout

    assert "QuestionToken789" in rendered
    assert ("PrimaryToken123" in rendered) is solution
    assert ("AlternateToken456" in rendered) is alternate
    assert "HiddenAnswerToken" not in rendered
